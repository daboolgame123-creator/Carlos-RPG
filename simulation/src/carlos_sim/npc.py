"""Deterministic, knowledge-limited NPC planning and event-sourced NPC state.

Only an NPC's documented beliefs may influence its plans. This module contains
no world-clock, network calls or language-model generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .domain import DomainEvent, WorldState, _json_copy
from .store import SQLiteEventStore
from .time_engine import TimeEngine

ACTIONS = ("rest", "work", "investigate", "wait")
NEEDS = ("fatigue", "hunger", "safety")
GOALS = ("earn", "explore", "survive")


def _integer(value: Any, *, minimum: int = 0, maximum: int = 100) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _validate_claim(claim: Any) -> None:
    if not isinstance(claim, dict) or set(claim) != {"text", "source", "received_at", "confidence"}:
        raise ValueError("invalid NPC claim shape")
    if not all(isinstance(claim[k], str) and claim[k] for k in ("text", "source")):
        raise ValueError("claim requires text and source")
    if not _integer(claim["received_at"], maximum=2**63 - 1) or not _integer(claim["confidence"]):
        raise ValueError("invalid claim time/confidence")


def validate_npc_state(npc: Any) -> None:
    if not isinstance(npc, dict) or set(npc) != {"role", "needs", "goals", "beliefs", "next_decision_at", "last_decision"}:
        raise ValueError("invalid NPC state")
    if not isinstance(npc["role"], str) or not npc["role"]:
        raise ValueError("invalid NPC role")
    if not isinstance(npc["needs"], dict) or set(npc["needs"]) != set(NEEDS) or not all(_integer(x) for x in npc["needs"].values()):
        raise ValueError("invalid NPC needs")
    if not isinstance(npc["goals"], dict) or set(npc["goals"]) != set(GOALS) or not all(_integer(x) for x in npc["goals"].values()):
        raise ValueError("invalid NPC goals")
    if not isinstance(npc["beliefs"], dict) or any(not isinstance(k, str) or not k for k in npc["beliefs"]):
        raise ValueError("invalid NPC knowledge")
    for claim in npc["beliefs"].values():
        _validate_claim(claim)
    if not _integer(npc["next_decision_at"], maximum=2**63 - 1):
        raise ValueError("invalid decision schedule")
    last = npc["last_decision"]
    if last is not None:
        if not isinstance(last, dict) or set(last) != {"action", "score", "reason", "at"}:
            raise ValueError("invalid decision record")
        if last["action"] not in ACTIONS or type(last["score"]) is not int or not isinstance(last["reason"], str) or not _integer(last["at"], maximum=2**63 - 1):
            raise ValueError("invalid recorded decision")


def project_npc_event(state: dict[str, Any], event: DomainEvent, *, bootstrap: bool) -> None:
    p = _json_copy(event.data)
    ident = p.get("npc_id")
    if not isinstance(ident, str) or not ident or ident not in state["entities"] or state["entities"][ident]["controller"] != "npc":
        raise ValueError("NPC events may target only existing autonomous entities")
    if event.event_type == "NPCConfigured":
        if set(p) != {"npc_id", "role", "needs", "goals"} or ident in state["npcs"]:
            raise ValueError("invalid or duplicate NPC configuration")
        if not bootstrap or state["time"] != 0 or event.actor_id is not None:
            raise ValueError("NPC setup requires trusted bootstrap")
        profile = {"role": p["role"], "needs": p["needs"], "goals": p["goals"],
                   "beliefs": {}, "next_decision_at": 0, "last_decision": None}
        validate_npc_state(profile)
        state["npcs"][ident] = _json_copy(profile)
        return
    if ident not in state["npcs"]:
        raise ValueError("NPC not configured")
    npc = state["npcs"][ident]
    if event.event_type == "NPCBeliefReceived":
        if set(p) != {"npc_id", "key", "claim"} or not isinstance(p["key"], str) or not p["key"]:
            raise ValueError("invalid knowledge delivery")
        _validate_claim(p["claim"])
        if p["claim"]["received_at"] != state["time"]:
            raise ValueError("knowledge must be delivered at current simulation time")
        if event.actor_id != ident and event.actor_id is not None:
            raise ValueError("untrusted third-party delivery actor")
        # A system event with no actor means a trusted externally resolved delivery.
        # No omniscient state is read here.
        npc["beliefs"][p["key"]] = _json_copy(p["claim"])
    elif event.event_type == "NPCNeedChanged":
        if set(p) != {"npc_id", "need", "previous", "current"} or p["need"] not in NEEDS:
            raise ValueError("invalid need change")
        if event.actor_id not in (None, ident):
            raise ValueError("unrelated actor cannot change NPC needs")
        if npc["needs"][p["need"]] != p["previous"] or not _integer(p["current"]) or p["current"] == p["previous"]:
            raise ValueError("invalid need transition")
        npc["needs"][p["need"]] = p["current"]
    elif event.event_type == "NPCDecisionRecorded":
        if set(p) != {"npc_id", "action", "score", "reason", "next_decision_at"} or event.actor_id != ident:
            raise ValueError("invalid NPC decision event")
        if event.time < npc["next_decision_at"]:
            raise ValueError("NPC decision attempted before next allowed time")
        if p["action"] not in ACTIONS or type(p["score"]) is not int or not isinstance(p["reason"], str) or not p["reason"]:
            raise ValueError("invalid decision contents")
        if not _integer(p["next_decision_at"], maximum=2**63-1) or p["next_decision_at"] <= state["time"]:
            raise ValueError("next decision must be in future")
        expected = _score_choice(npc, ident)
        if (p["action"], p["score"], p["reason"]) != (expected.action, expected.score, expected.reason):
            raise ValueError("NPC decision does not match deterministic utility policy")
        # Event records an intention, never silently changes HP, resources or position.
        npc["last_decision"] = {"action": p["action"], "score": p["score"], "reason": p["reason"], "at": event.time}
        npc["next_decision_at"] = p["next_decision_at"]
    else:
        raise ValueError("unsupported NPC event")


@dataclass(frozen=True)
class Decision:
    npc_id: str
    action: str
    score: int
    reason: str


def _score_choice(npc: Mapping[str, Any], npc_id: str) -> Decision:
    """Pure utility scoring based only on a single NPC profile."""
    needs, goals, beliefs = npc["needs"], npc["goals"], npc["beliefs"]
    danger = beliefs.get("danger")
    perceived_risk = danger["confidence"] if danger is not None else 0
    scores = {
        "rest": needs["fatigue"] * 2 + needs["safety"] // 5,
        "work": goals["earn"] + needs["hunger"] - needs["fatigue"] - perceived_risk,
        "investigate": goals["explore"] + perceived_risk // 2 - needs["fatigue"] - needs["safety"],
        "wait": 10 + needs["safety"] + perceived_risk,
    }
    # No random draw or unordered iteration. Stable tie preference makes replay deterministic.
    action = sorted(ACTIONS, key=lambda a: (-scores[a], ACTIONS.index(a)))[0]
    reason = f"utility[{action}]={scores[action]}; belief_danger={perceived_risk}; npc={npc_id}"
    return Decision(npc_id, action, scores[action], reason)


def choose_action(state: WorldState, npc_id: str) -> Decision | None:
    """Return an explainable recommendation based ONLY on one NPC's knowledge.

    Beliefs are not asserted as facts; a false report may still change a decision.
    """
    npc = state.npcs.get(npc_id)
    if npc is None or state.entities[npc_id]["controller"] != "npc":
        return None
    if state.time < npc["next_decision_at"]:
        return None
    return _score_choice(npc, npc_id)


class NPCService:
    """Explicit deterministic decision step. Does not advance the world clock.

    A TimeEngine session must be active before any decision can be recorded.
    This stage does not yet execute actions; that requires action resolvers.
    """
    def __init__(self, store: SQLiteEventStore, clock: "TimeEngine", *, decision_cooldown: int = 60):
        if type(decision_cooldown) is not int or decision_cooldown < 1:
            raise ValueError("cooldown must be a positive integer")
        self.store = store
        self.clock = clock
        if clock.store is not store:
            raise ValueError("NPC service and clock must use the same store")
        self.cooldown = decision_cooldown

    def decide(self, world_id: str, npc_id: str, *, command_id: str, expected_revision: int) -> Decision | None:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            from .store import RevisionConflict
            raise RevisionConflict("stale NPC decision request")
        candidate = choose_action(state, npc_id)
        if candidate is None:
            return None
        event = DomainEvent("NPCDecisionRecorded", npc_id, "local utility policy", state.time,
                            {"npc_id": npc_id, "action": candidate.action, "score": candidate.score,
                             "reason": candidate.reason, "next_decision_at": state.time + self.cooldown})
        self.store.append(world_id, command_id, expected_revision, [event], npc_authorized=True)
        return candidate
