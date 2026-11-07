"""PLAY-11: physically local, source-conserving player wild-food pickup.

This is a simplified immediate pickup of visible food, NOT a timed hunt.
"""
from __future__ import annotations

from typing import Any
from .domain import DomainEvent, WorldState
from .movement import _in_transit

WILD_FOOD_RESOURCE = "wild_food"
OWNED_FOOD_RESOURCE = "food"


def local_food_view(state: WorldState, player_id: str) -> dict[str, Any]:
    """Present-only qualitative observation; unknown never means zero."""
    if _in_transit(state.to_dict(), player_id):
        return {"status": "traveling"}
    site = state.entities[player_id]["location_id"]
    stock = state.resources.get(site, {}).get(WILD_FOOD_RESOURCE)
    status = ("present" if stock > 0 else "empty") if type(stock) is int else "unknown"
    return {"location_id": site, "status": status}


def project_player_food_collected(state: dict[str, Any], event: DomainEvent, *,
                                  action_authorized: bool, bootstrap: bool) -> None:
    """Move one known unit from the site to the human's known food balance."""
    if bootstrap or not action_authorized or set(event.data) != {"site_id", "quantity"}:
        raise ValueError("player food collection requires a trusted runtime action")
    who = event.actor_id
    if (not isinstance(who, str) or who not in state["entities"]
            or state["entities"][who]["controller"] != "player"
            or type(event.data["quantity"]) is not int
            or event.data["quantity"] != 1):
        raise ValueError("pickup requires a real player and exactly one unit")
    if _in_transit(state, who):
        raise ValueError("cannot collect food while traveling")
    site = state["entities"][who]["location_id"]
    if event.data["site_id"] != site:
        raise ValueError("food must come from the player's physical location")
    source = state["resources"].get(site, {}).get(WILD_FOOD_RESOURCE)
    owned = state["resources"].get(who, {}).get(OWNED_FOOD_RESOURCE)
    if (type(source) is not int or source < 1
            or type(owned) is not int or owned < 0):
        raise ValueError("pickup requires sufficient finite stock and initialized player food")
    state["resources"][site][WILD_FOOD_RESOURCE] = source - 1
    state["resources"][who][OWNED_FOOD_RESOURCE] = owned + 1
