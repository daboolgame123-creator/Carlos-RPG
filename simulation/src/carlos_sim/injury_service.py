"""03-A5 trusted in-process exhaustion injury service.

Internal test-world capability only; do not expose directly to players or HTTP.
"""
from __future__ import annotations

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore
from .time_engine import TimeEngine
from .injury_events import EXHAUSTION_THRESHOLD


class NPCExhaustionInjuryService:
    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        self.store = store
        self.clock = clock

    def record(self, world_id: str, *, subject_id: str, injury_id: str,
               command_id: str, expected_revision: int) -> WorldState:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if type(subject_id) is not str or subject_id not in state.npcs:
            raise ValueError("unknown NPC for exhaustion injury")
        if type(injury_id) is not str or not injury_id:
            raise ValueError("injury identifier required")
        if type(command_id) is not str or not command_id:
            raise ValueError("command identifier required")
        fatigue = state.npcs[subject_id]["needs"]["fatigue"]
        if type(fatigue) is not int or fatigue < EXHAUSTION_THRESHOLD:
            raise ValueError("NPC fatigue is below injury threshold")
        event = DomainEvent(
            "InjuryRecorded", None, "deterministic local exhaustion event",
            state.time,
            {"injury_id": injury_id, "subject_id": subject_id,
             "severity": fatigue - 70, "source": "exhaustion",
             "fatigue_at_onset": fatigue},
        )
        return self.store.append(
            world_id, command_id, expected_revision, [event],
            injury_authorized=True,
        )
