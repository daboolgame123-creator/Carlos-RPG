"""03-A3: read-only eligibility checks for a hypothetical NPC recovery action.

This is NOT a scheduled recovery, treatment, or permission to change the world.
The intake record is untrusted; only a later event-sourced authorization can
create injury/recovery events. Never expose this trusted-world packet to players.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .injury_transitions import TIME_MAX, validate_injury_record
from .market import _id, _present


def assess_npc_recovery_readiness(state: Any, *, injury: Mapping[str, Any],
                                  caregiver_id: str, duration: int,
                                  improvement: int) -> dict[str, Any]:
    """Determine whether two NPCs could be physically ready to begin recovery.

    The returned assessment carries no capability and is not a reservation.
    It cannot establish that an injury exists in the persisted world.
    """
    validate_injury_record(injury)
    if injury["status"] != "active":
        raise ValueError("recovered injury cannot begin recovery again")
    if not _id(caregiver_id) or caregiver_id not in state.npcs:
        raise ValueError("caregiver must be a real NPC")
    subject_id = injury["subject_id"]
    if subject_id not in state.npcs:
        raise ValueError("this first slice supports NPC subjects only")
    if type(duration) is not int or not 1 <= duration <= TIME_MAX:
        raise ValueError("duration must be a positive bounded logical interval")
    if type(improvement) is not int or not 1 <= improvement <= 100:
        raise ValueError("invalid recovery effect")
    if (type(state.time) is not int or not 0 <= state.time < TIME_MAX
            or duration > TIME_MAX - state.time):
        raise ValueError("proposed due time exceeds logical time bounds")
    if injury["onset"] > state.time or injury["last_changed"] > state.time:
        raise ValueError("injury future-dated against this world")
    site_id = state.entities[subject_id]["location_id"]
    projected = state.to_dict()
    if not _present(projected, subject_id, site_id):
        raise ValueError("injured subject must be physically present and available")
    if not _present(projected, caregiver_id, site_id):
        raise ValueError("caregiver must be locally present and available")
    return {
        "injury_id_proposed": injury["injury_id"],
        "subject_id": subject_id,
        "caregiver_id": caregiver_id,
        "site_id": site_id,
        "started_at_proposed": state.time,
        "due_at_proposed": state.time + duration,
        "improvement_proposed": improvement,
        "physical_eligibility_checked": True,
        "injury_persisted_and_source_verified": False,
        "treatment_effectiveness_verified": False,
        "resources_reserved": False,
        "scheduled_event_created": False,
        "recovery_authorized": False,
        "status": "readiness_only_no_gameplay_authority",
        "audience": "trusted_internal_design_only",
    }
