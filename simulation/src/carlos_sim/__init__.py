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
from .social import NPCSocialService, SocialResult
from .social_autonomy import choose_social_intent, SocialIntent, MIN_SOCIAL_COOLDOWN
from .assistance import NPCAssistanceService, AssistanceResult, ASSISTANCE_RESOURCES
from .assistance_autonomy import choose_assistance_intent, AssistanceIntent
from .consumption import NPCConsumptionService, ConsumptionResult, choose_food_consumption
from .survival import HUNGER_SECONDS_PER_POINT, FATIGUE_SECONDS_PER_POINT, CRITICAL_HUNGER

from .gathering import NPCGatheringService, GatheringResult

from .gathering import choose_gathering_intent, GatheringIntent

from .foraging import choose_local_foraging, FORAGING_MIN_HUNGER, FORAGING_MAX_FATIGUE

from .food_navigation import FoodRouteIntent, choose_food_route

from .scarcity import recent_personal_depletion, recently_refused_by

from .player_gateway import PlayerGateway, PlayerCommandResult
from .production import NPCProductionService, ProductionStart
from .market import NPCMarketService, MarketResult
from .loans import NPCLoanService, LoanResult
from .property import NPCPropertyService, TakingResult

from .property_evidence import personal_property_evidence

from .complaints import NPCComplaintService, ComplaintResult, personal_complaints

from .rights_permissions import NPCPermissionService, PermissionResult

from .registered_claims import NPCRegisteredClaimService, ClaimAssignmentResult
