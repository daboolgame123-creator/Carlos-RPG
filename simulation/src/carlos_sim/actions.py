"""Deterministic NPC action execution in a test world.

Action started -> durable scheduled signal -> firing deterministically changes
needs or records bounded, explicitly named test resources. No external API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

# Fixed prototype durations in *simulated seconds*. Not Carlos story canon.
DURATIONS = {"rest": 120, "work": 180, "investigate": 90, "wait": 60}
LABOR_RESOURCE = "labor_units"  # Non-money test metric; not transferable goods.
INVESTIGATION_RESOURCE = "investigation_attempts"  # Attempts, not discoveries.


def validate_actions(state: dict[str, Any]) -> None:
    busy: set[str] = set()
    for action_id, info in state["actions"].items():
        if not isinstance(action_id, str) or not action_id or not isinstance(info, dict):
            raise ValueError("invalid action ID or record")
        keys = {"npc_id", "action", "start", "due", "schedule_id", "status", "result", "completed_at"}
        if set(info) != keys:
            raise ValueError("invalid action fields")
        who, act, status = info["npc_id"], info["action"], info["status"]
        if who not in state["npcs"] or act not in DURATIONS or status not in ("running", "completed"):
            raise ValueError("invalid action actor/type/status")
        if type(info["start"]) is not int or type(info["due"]) is not int or info["start"] < 0:
            raise ValueError("invalid action timestamp")
        if info["due"] - info["start"] != DURATIONS[act]:
            raise ValueError("action duration mismatch")
        if not isinstance(info["schedule_id"], str) or info["schedule_id"] != "npc-action:" + action_id:
            raise ValueError("invalid action schedule ID")
        if status == "running":
            if who in busy:
                raise ValueError("NPC cannot run two actions concurrently")
            busy.add(who)
            if info["result"] is not None or info["completed_at"] is not None:
                raise ValueError("running action has a result")
            scheduled = state["scheduled"].get(info["schedule_id"])
            if scheduled is None or scheduled["due"] != info["due"] or scheduled["payload"] != {"__npc_action_id": action_id}:
                raise ValueError("running action must have matching durable schedule")
            if state["time"] > info["due"]:
                raise ValueError("running action overdue")
        else:
            if info["completed_at"] != info["due"] or type(info["completed_at"]) is not int or info["completed_at"] > state["time"]:
                raise ValueError("completed action timestamp mismatch")
            if info["schedule_id"] in state["scheduled"]:
                raise ValueError("completed action still scheduled")
            if not isinstance(info["result"], dict) or set(info["result"]) != {"needs", "counters"}:
                raise ValueError("completed action missing effects")
            for old_new in info["result"]["needs"].values():
                if not isinstance(old_new, list) or len(old_new) != 2 or any(type(x) is not int or not 0 <= x <= 100 for x in old_new):
                    raise ValueError("invalid need effect")
            for old_new in info["result"]["counters"].values():
                if not isinstance(old_new, list) or len(old_new) != 2 or any(type(x) is not int or x < 0 for x in old_new):
                    raise ValueError("invalid counter effect")


def start_action(state: dict[str, Any], event: DomainEvent, *, action_authorized: bool) -> None:
    data = event.data
    if not action_authorized or set(data) != {"action_id", "npc_id", "action", "schedule_id", "due"}:
        raise ValueError("unauthorized or malformed action start")
    action_id, npc_id, action = data["action_id"], data["npc_id"], data["action"]
    if not isinstance(action_id, str) or not action_id or action_id in state["actions"]:
        raise ValueError("invalid or duplicate action ID")
    if not isinstance(npc_id, str) or npc_id not in state["npcs"] or event.actor_id != npc_id:
        raise ValueError("action must belong to an NPC actor")
    if action not in DURATIONS or type(data["due"]) is not int or data["due"] != state["time"] + DURATIONS[action]:
        raise ValueError("invalid action duration")
    if data["schedule_id"] != "npc-action:" + action_id:
        raise ValueError("invalid action scheduled ID")
    scheduled = state["scheduled"].get(data["schedule_id"])
    if scheduled is None or scheduled["due"] != data["due"] or scheduled["payload"] != {"__npc_action_id": action_id} or scheduled["interrupt"]:
        raise ValueError("action must reference its noninterrupting scheduled signal")
    last = state["npcs"][npc_id]["last_decision"]
    if last is None or last["action"] != action or last["at"] != state["time"]:
        raise ValueError("action start requires a decision made this tick")
    if any(a["npc_id"] == npc_id and a["status"] == "running" for a in state["actions"].values()):
        raise ValueError("NPC is already busy")
    if any(a["npc_id"] == npc_id and a["start"] == state["time"] for a in state["actions"].values()):
        raise ValueError("NPC decision cannot start multiple actions")
    required_counter = {"work": LABOR_RESOURCE, "investigate": INVESTIGATION_RESOURCE}.get(action)
    if required_counter is not None:
        value = state["resources"].get(npc_id, {}).get(required_counter)
        if type(value) is not int or value < 0:
            raise ValueError("required action counter must be initialized explicitly")
    state["actions"][action_id] = {"npc_id": npc_id, "action": action, "start": state["time"],
        "due": data["due"], "schedule_id": data["schedule_id"], "status": "running",
        "result": None, "completed_at": None}


def resolve_action(state: dict[str, Any], action_id: str, schedule_id: str, time: int) -> None:
    action = state["actions"].get(action_id)
    if not isinstance(action_id, str) or action is None or action["status"] != "running" or action["schedule_id"] != schedule_id or action["due"] != time:
        raise ValueError("no matching active NPC action at due time")
    npc_id, verb = action["npc_id"], action["action"]
    npc = state["npcs"][npc_id]
    # Strict, fixed prototype effects. No random reward or claim of new knowledge.
    deltas = {
        "rest": {"fatigue": -20, "hunger": 5},
        "work": {"fatigue": 15, "hunger": 10},
        "investigate": {"fatigue": 10, "hunger": 5},
        "wait": {"hunger": 5},
    }[verb]
    result: dict[str, Any] = {"needs": {}, "counters": {}}
    for need, delta in deltas.items():
        old = npc["needs"][need]
        new = min(100, max(0, old + delta))
        npc["needs"][need] = new
        if new != old:
            result["needs"][need] = [old, new]
    resource = {"work": LABOR_RESOURCE, "investigate": INVESTIGATION_RESOURCE}.get(verb)
    if resource is not None:
        ledger = state["resources"].setdefault(npc_id, {})
        before = ledger.get(resource)
        if before is not None and (type(before) is not int or before < 0):
            raise ValueError("invalid existing action counter")
        if before is None:
            raise ValueError("action counter must be initialized explicitly")
        previous = before
        ledger[resource] = previous + 1
        result["counters"][resource] = [previous, previous + 1]
    action["status"] = "completed"
    action["completed_at"] = time
    action["result"] = result


@dataclass(frozen=True)
class ActionStart:
    action_id: str
    npc_id: str
    action: str
    due: int
    state: WorldState


class NPCActionService:
    """Starts already-decided NPC intentions; TimeEngine fires their effects.

    Underlying event-store capabilities are trusted LOCAL conventions, not auth.
    """
    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("store and clock must match")
        self.store = store
        self.clock = clock

    def start(self, world_id: str, npc_id: str, action_id: str, *, expected_revision: int) -> ActionStart:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict("stale action start request")
        if not isinstance(action_id, str) or not action_id:
            raise ValueError("action ID required")
        profile = state.npcs.get(npc_id)
        if profile is None or profile["last_decision"] is None:
            raise ValueError("NPC must choose an intention first")
        chosen = profile["last_decision"]
        if chosen["at"] != state.time:
            raise ValueError("cannot start stale NPC intention")
        verb = chosen["action"]
        due = state.time + DURATIONS[verb]
        schedule_id = "npc-action:" + action_id
        events = [
            DomainEvent("ScheduledEventCreated", None, "NPC action completion appointment", state.time,
                {"id": schedule_id, "due": due, "order": state.next_schedule_order, "kind": "signal",
                 "payload": {"__npc_action_id": action_id}, "interrupt": False}),
            DomainEvent("NPCActionStarted", npc_id, "NPC chose and started an action", state.time,
                {"action_id": action_id, "npc_id": npc_id, "action": verb,
                 "schedule_id": schedule_id, "due": due}),
        ]
        result = self.store.append(world_id, "action-start:" + action_id, expected_revision, events,
                                   action_authorized=True)
        return ActionStart(action_id, npc_id, verb, due, result)
