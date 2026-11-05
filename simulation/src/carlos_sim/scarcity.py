"""Phase 01-V: personal, finite-memory scarcity consequences.

Only a named NPC's own failed collection history and its own prior help
requests enter these choices. No external truth, peer inventory, or fabricated
resources are consulted. Both retry windows are in logical simulation seconds.
"""
from __future__ import annotations

from typing import Mapping, Any

from .domain import WorldState
from .knowledge import is_observation_source, parse_food_claim


FAILED_SITE_RETRY_SECONDS = 3600
REFUSED_PROVIDER_RETRY_SECONDS = 3600


def recent_personal_depletion(
    state: WorldState, npc_id: str, site_id: str,
    current_belief: Mapping[str, Any],
) -> bool:
    """True if *this NPC* personally depleted the candidate site recently.

    A subsequently verified direct observation of present food overrides
    an earlier failure. A new rumor, even with a newer claimed fact time,
    is not stronger than the actor's own recent physical failure.
    """
    parsed = parse_food_claim(current_belief["text"])
    if parsed is None:
        return False
    _, observed_at = parsed
    latest_failure = max((
        attempt["at"] for attempt in state.foraging_attempts.values()
        if attempt["npc_id"] == npc_id
        and attempt["site_id"] == site_id
        and attempt["outcome"] == "depleted"
        and 0 <= state.time - attempt["at"] < FAILED_SITE_RETRY_SECONDS
    ), default=None)
    if latest_failure is None:
        return False
    return not (
        is_observation_source(current_belief["source"])
        and current_belief["source"] == "observation:" + site_id
        and observed_at > latest_failure
    )


def recently_refused_by(
    state: WorldState, requester_id: str, provider_id: str,
) -> bool:
    """Recall only this requester's recorded refusal/withdrawn promise."""
    return any(
        o["requester"] == requester_id
        and o["provider"] == provider_id
        and o["resource"] == "food"
        and (
            o["status"] == "declined"
            or (o["status"] == "cancelled"
                and o["reason"] == "promise_withdrawn")
        )
        and type(o["resolved_at"]) is int
        and 0 <= state.time - o["resolved_at"] < REFUSED_PROVIDER_RETRY_SECONDS
        for o in state.obligations.values()
    )
