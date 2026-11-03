"""Carlos Simulation Engine: Phase 01-A state and persistence core."""
from .domain import WorldState, DomainEvent, apply_event, canonical_hash
from .store import SQLiteEventStore, RevisionConflict, InvalidEvent, IntegrityError, UnsupportedVersion, DuplicateCommand

__all__ = ["WorldState", "DomainEvent", "apply_event", "canonical_hash", "SQLiteEventStore", "RevisionConflict", "InvalidEvent", "IntegrityError", "UnsupportedVersion", "DuplicateCommand"]

from .time_engine import TimeEngine, AdvanceResult, SessionClosed, AdvanceLimitExceeded
from .npc import NPCService, Decision, choose_action
from .actions import NPCActionService, ActionStart, DURATIONS
from .living_world import LivingWorldEngine, LivingAdvanceResult
from .movement import NPCMovementService, TravelStart, perceive_local
from .navigation import NPCNavigationService, shortest_known_route, next_route
