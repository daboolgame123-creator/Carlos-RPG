"""01-U: opt-in route choice to a *believed* food location using learned roads.

This planner never reads remote food balances or another character's beliefs.
Rumors are subjective; actual food is checked only when the character arrives
and attempts ordinary local forage. The chosen route consumes simulation time.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain import WorldState
from .foraging import (
    FORAGING_MIN_HUNGER, FORAGING_MAX_FATIGUE,
    FORAGING_MAX_SAFETY_NEED, FORAGING_DANGER_BELIEF_CUTOFF, OWNED_FOOD,
)
from .knowledge import effective_confidence, known_food_sites, parse_food_claim
from .navigation import shortest_known_route


@dataclass(frozen=True)
class FoodRouteIntent:
    npc_id: str
    destination: str
    route_id: str
    total_seconds: int
    confidence: int
    source: str
    observed_at: int


def choose_food_route(state: WorldState, npc_id: str) -> FoodRouteIntent | None:
    """Find cheapest *known* journey to a site this NPC believes has food.

    The planner may read this NPC's owned-food balance but never any remote
    resource, peer inventory, peer belief, or route outside known_routes.
    An explicit navigation target always takes precedence over this impulse.
    """
    npc = state.npcs.get(npc_id)
    entity = state.entities.get(npc_id)
    if npc is None or entity is None or entity["controller"] != "npc":
        return None
    if any(t["npc_id"] == npc_id and t["status"] == "traveling"
           for t in state.travels.values()):
        return None
    if any(a["npc_id"] == npc_id and a["status"] == "running"
           for a in state.actions.values()):
        return None
    nav = state.navigation.get(npc_id)
    if nav is None or nav["target"] is not None:
        return None

    needs = npc["needs"]
    warning = npc["beliefs"].get("danger")
    perceived_risk = warning["confidence"] if warning is not None else 0
    owned = state.resources.get(npc_id, {}).get(OWNED_FOOD)
    if (needs["hunger"] < FORAGING_MIN_HUNGER
            or needs["fatigue"] > FORAGING_MAX_FATIGUE
            or needs["safety"] > FORAGING_MAX_SAFETY_NEED
            or perceived_risk >= FORAGING_DANGER_BELIEF_CUTOFF
            or type(owned) is not int or owned != 0):
        return None

    here = entity["location_id"]
    candidates: list[tuple[tuple[int, int, str, tuple[str, ...]], FoodRouteIntent]] = []
    for site in known_food_sites(state, npc_id):
        if site == here or site not in state.locations:
            continue
        belief = npc["beliefs"]["food:" + site]
        parsed = parse_food_claim(belief["text"])
        if parsed is None:
            continue
        confidence = effective_confidence(belief, state.time)
        if confidence <= 0:
            continue
        path = shortest_known_route(state, npc_id, site)
        if not path:
            continue
        # The route IDs in path came only from this NPC's known_routes.
        total_seconds = sum(state.routes[rid]["seconds"] for rid in path)
        if total_seconds <= 0:
            continue
        intent = FoodRouteIntent(
            npc_id, site, path[0], total_seconds,
            confidence, belief["source"], parsed[1]
        )
        candidates.append(((total_seconds, -confidence, site, path), intent))
    return min(candidates, key=lambda entry: entry[0])[1] if candidates else None
