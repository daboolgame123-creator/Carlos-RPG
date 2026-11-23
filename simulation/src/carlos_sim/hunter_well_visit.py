"""P10 optional hunter's finite, voluntary visit to a public village well.

The hunter can choose to visit a known public landmark without observing
distant people or inventories. Each leg is an existing surveyed physical road.
Aid itself remains under the P9 co-present assistance and property reducer.
"""
from __future__ import annotations

from .domain import WorldState
from .navigation import shortest_known_route
from .npc import _injury_rest_decision

PREFIX = "p10-well-hunter:"
MAX_WALK_SECONDS = 1800
MAX_HUNGER = 35
MAX_FATIGUE = 69


def hunter_prepared(state: WorldState, who: str) -> bool:
    npc = state.npcs.get(who)
    if npc is None or npc["role"] != "hunter":
        return False
    need = npc["needs"]
    if (state.resources.get(who, {}).get("food", 0) < 1
            or need["hunger"] > MAX_HUNGER or need["fatigue"] > MAX_FATIGUE
            or need["safety"] >= 75
            or _injury_rest_decision(state.injuries, who) is not None
            or who not in state.navigation
            or state.navigation[who]["target"] is not None):
        return False
    if any(x["npc_id"] == who and x["status"] == "traveling"
           for x in state.travels.values()):
        return False
    if any(x["npc_id"] == who and x["status"] == "running"
           for x in state.actions.values()):
        return False
    if any(x["npc_id"] == who and x["status"] == "running"
           for x in state.production_jobs.values()):
        return False
    return not any(x["provider"] == who and x["resource"] == "food"
                   and x["status"] in ("requested", "promised")
                   for x in state.obligations.values())


def hunter_seeks_well(state: WorldState, who: str) -> bool:
    """One bounded tour: start at own worksite or continue a real begun tour."""
    if not hunter_prepared(state, who) or "well" not in state.locations:
        return False
    here = state.entities[who]["location_id"]
    if here == "well":
        return False
    departures = [
        t["start"] for key, t in state.travels.items()
        if key.startswith(PREFIX + who + ":") and t["npc_id"] == who
    ]
    if departures:
        return 0 <= state.time - min(departures) < MAX_WALK_SECONDS
    routine = state.npc_routines.get(who)
    return routine is not None and here == routine["workplace_id"]


def choose_hunter_well_leg(state: WorldState, who: str) -> str | None:
    """The next locally known leg. Unknown roads require physical survey."""
    if not hunter_seeks_well(state, who):
        return None
    route = shortest_known_route(state, who, "well")
    if route:
        return route[0]
    nav = state.navigation[who]
    here = state.entities[who]["location_id"]
    frontier = []
    for rid in nav["known_routes"]:
        edge = state.routes[rid]
        for place in (edge["a"], edge["b"]):
            if place == here or place in nav["visited"]:
                continue
            path = shortest_known_route(state, who, place)
            if path:
                frontier.append((
                    sum(state.routes[r]["seconds"] for r in path),
                    place, path
                ))
    return min(frontier)[2][0] if frontier else None


def hunter_waits_at_well(state: WorldState, who: str) -> bool:
    """Wait no longer than an hour for a *locally seen* needy neighbor to ask."""
    if (not hunter_prepared(state, who)
            or state.entities[who]["location_id"] != "well"):
        return False
    arrivals = [
        t["arrived_at"] for key, t in state.travels.items()
        if key.startswith(PREFIX + who + ":") and t["npc_id"] == who
        and t["destination"] == "well" and t["status"] == "arrived"
    ]
    if not arrivals or not 0 <= state.time - max(arrivals) < 3600:
        return False
    return any(
        peer != who and state.entities[peer]["location_id"] == "well"
        and state.npcs[peer]["role"] == "courier"
        and state.npcs[peer]["needs"]["hunger"] >= 90
        and state.resources[peer].get("food") == 0
        for peer in state.npcs
    )
