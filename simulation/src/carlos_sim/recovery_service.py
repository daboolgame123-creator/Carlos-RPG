"""03-A6 trusted local start of funded, scheduled NPC supportive care.

Not a player API. The authoritative reducer validates resources, physical
presence, active injury, time and efficacy before any SQLite commit.
"""
from __future__ import annotations

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore
from .time_engine import TimeEngine
from .recovery_events import DURATION, IMPROVEMENT, FOOD_COST, RESOURCE
from .injury_transitions import _ident, TIME_MAX


class NPCRecoveryService:
    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        self.store = store
        self.clock = clock

    def start(self, world_id: str, *, treatment_id: str, injury_id: str,
              caregiver_id: str, command_id: str, expected_revision: int
              ) -> WorldState:
        self.clock._require_session(world_id)
        if not _ident(treatment_id) or len(treatment_id) > 70:
            raise ValueError("invalid treatment identifier")
        if not _ident(injury_id) or not _ident(caregiver_id):
            raise ValueError("invalid treatment identities")
        if type(command_id) is not str or not command_id:
            raise ValueError("treatment command id required")
        state = self.store.load(world_id)
        if injury_id not in state.injuries:
            raise ValueError("unknown injured subject")
        subject_id = state.injuries[injury_id]["subject_id"]
        if caregiver_id not in state.npcs:
            raise ValueError("caregiver must be an NPC")
        if type(state.time) is not int or state.time + DURATION > TIME_MAX:
            raise ValueError("recovery appointment overflows logical time")
        site = state.entities[subject_id]["location_id"]
        schedule_id = "heal." + treatment_id
        due = state.time + DURATION
        treatment = DomainEvent(
            "RecoveryStarted", caregiver_id, "trusted paid supportive care", state.time,
            {"id": treatment_id, "injury_id": injury_id,
             "subject_id": subject_id, "caregiver_id": caregiver_id,
             "site_id": site, "schedule_id": schedule_id,
             "started_at": state.time, "due_at": due,
             "resource": RESOURCE, "quantity": FOOD_COST,
             "improvement": IMPROVEMENT},
        )
        scheduled = DomainEvent(
            "ScheduledEventCreated", None, "trusted recovery schedule", state.time,
            {"id": schedule_id, "due": due, "order": state.next_schedule_order,
             "kind": "signal", "payload": {"__npc_recovery": treatment_id},
             "interrupt": False},
        )
        return self.store.append(
            world_id, command_id, expected_revision, [treatment, scheduled],
            recovery_authorized=True,
        )
