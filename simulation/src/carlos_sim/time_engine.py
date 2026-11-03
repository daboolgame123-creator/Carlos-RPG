"""Explicit-play logical clock and deterministic, durable scheduled signal execution.

This phase intentionally supports signals only. A signal is a recorded occurrence,
not arbitrary code execution, NPC decisions, a resource mutation or an RPG outcome.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState, apply_event, _json_copy
from .store import SQLiteEventStore, InvalidEvent, DuplicateCommand


class SessionClosed(PermissionError):
    """A logical clock operation was attempted outside an active play session."""


class AdvanceLimitExceeded(ValueError):
    """A command exceeded the configured per-command event processing limit."""


@dataclass(frozen=True)
class AdvanceResult:
    state: WorldState
    requested_seconds: int
    elapsed_seconds: int
    remaining_seconds: int
    fired_ids: tuple[str, ...]
    interrupted: bool


class TimeEngine:
    """Local trusted application layer; NOT a network authentication boundary.

    Sessions exist in process memory only. Restarting the application freezes the
    world until an explicit new session is opened; downtime never advances time.
    """

    def __init__(self, store: SQLiteEventStore, *, max_events_per_advance: int = 1000):
        if type(max_events_per_advance) is not int or max_events_per_advance < 1:
            raise ValueError("max_events_per_advance must be a positive integer")
        self.store = store
        self.max_events_per_advance = max_events_per_advance
        self._active_worlds = store._active_worlds

    def open_session(self, world_id: str) -> None:
        self.store.load(world_id)  # fail if world is missing or corrupt
        self._active_worlds.add(world_id)

    def close_session(self, world_id: str) -> None:
        self._active_worlds.discard(world_id)

    def _require_session(self, world_id: str) -> None:
        if world_id not in self._active_worlds:
            raise SessionClosed("simulation is paused until a play session is opened")

    def schedule_signal(self, world_id: str, schedule_id: str, *, due: int,
                        payload: dict[str, Any] | None = None,
                        interrupt: bool = False, expected_revision: int) -> WorldState:
        self._require_session(world_id)
        if not isinstance(schedule_id, str) or not schedule_id or type(due) is not int or type(interrupt) is not bool:
            raise ValueError("invalid schedule parameters")
        state = self.store.load(world_id)
        if payload is None:
            payload = {}
        if type(payload) is not dict:
            raise ValueError("payload must be a JSON object")
        event = DomainEvent("ScheduledEventCreated", None, "explicit schedule request", state.time,
                            {"id": schedule_id, "due": due, "order": state.next_schedule_order,
                             "kind": "signal", "payload": _json_copy(payload), "interrupt": interrupt})
        return self.store.append(world_id, "schedule:" + schedule_id, expected_revision, [event])

    def cancel(self, world_id: str, schedule_id: str, *, command_id: str,
               expected_revision: int) -> WorldState:
        self._require_session(world_id)
        if not isinstance(schedule_id, str) or not schedule_id:
            raise ValueError("invalid schedule ID")
        state = self.store.load(world_id)
        event = DomainEvent("ScheduledEventCancelled", None, "explicit schedule cancellation",
                            state.time, {"id": schedule_id})
        return self.store.append(world_id, command_id, expected_revision, [event])

    def advance(self, world_id: str, *, seconds: int, command_id: str,
                expected_revision: int) -> AdvanceResult:
        self._require_session(world_id)
        if type(seconds) is not int or seconds <= 0:
            raise ValueError("advance seconds must be a positive integer")
        if not isinstance(command_id, str) or not command_id:
            raise ValueError("command ID is required")
        # Explicitly reject replayed high-level requests rather than silently
        # returning an inconsistent elapsed/remaining result after further commits.
        if self.store.db.execute("SELECT 1 FROM commands WHERE world_id=? AND command_id=?",
                                 (world_id, command_id)).fetchone():
            raise DuplicateCommand("clock command already executed; consult event history")
        state = self.store.load(world_id)
        target = state.time + seconds
        events: list[DomainEvent] = []
        fired: list[str] = []
        interrupted = False
        current = state
        while current.time < target or any(x["due"] == current.time for x in current.scheduled.values()):
            pending = sorted(current.scheduled.items(), key=lambda x: (x[1]["due"], x[1]["order"], x[0]))
            if pending and pending[0][1]["due"] == current.time:
                ident, detail = pending[0]
                event = DomainEvent("ScheduledEventFired", None, "scheduled signal became due",
                                    current.time, {"id": ident})
                events.append(event)
                current = apply_event(current, event)
                fired.append(ident)
                if len(events) > self.max_events_per_advance:
                    raise AdvanceLimitExceeded("too many clock events in one command")
                if detail["interrupt"]:
                    interrupted = True
                    break
            else:
                next_tick = min(target, pending[0][1]["due"] if pending else target)
                if next_tick <= current.time:
                    break
                event = DomainEvent("TimeAdvanced", None, "authorized play time",
                                    next_tick, {"from": current.time, "to": next_tick})
                events.append(event)
                current = apply_event(current, event)
            if len(events) > self.max_events_per_advance:
                raise AdvanceLimitExceeded("too many clock events in one command")
        if not events:
            raise InvalidEvent("no clock events were produced")
        committed = self.store.append(world_id, command_id, expected_revision, events,
                                      clock_authorized=True)
        elapsed = committed.time - state.time
        return AdvanceResult(committed, seconds, elapsed, seconds - elapsed,
                             tuple(fired), interrupted)
