"""PLAY-42: opt-in economic shopping journeys from personally surveyed roads.

This is deliberately NOT an omniscient market finder. A hungry solvent NPC
explores a finite, previously surveyed road frontier until physically finding
a registered local stall. The planner never reads remote food, prices, stock,
or another person's coins. The existing market/meal reducers decide outcomes
only after arrival; failure to buy is a genuine possible outcome.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain import WorldState
from .economic_autonomy import BUY_HUNGER_THRESHOLD, _free
from .market import MONEY, MAX_AMOUNT
from .navigation import shortest_known_route
from .routines import choose_routine_route

MAX_SHOPPING_FATIGUE = 84
MAX_SHOPPING_DANGER = 74


@dataclass(frozen=True)
class ShoppingWalkIntent:
    npc_id: str
    route_id: str
    destination: str
    reason: str


def wants_local_market(state: WorldState, npc_id: str) -> bool:
    """Personal hunger, free time and owned wallet; no remote market oracle."""
    npc = state.npcs.get(npc_id)
    entity = state.entities.get(npc_id)
    if (npc is None or entity is None or entity["controller"] != "npc"
            or not _free(state, npc_id)
            or npc_id in state.supply_circuits):
        return False
    needs = npc["needs"]
    if (needs["hunger"] < BUY_HUNGER_THRESHOLD
            or needs["fatigue"] > MAX_SHOPPING_FATIGUE
            or needs["safety"] > MAX_SHOPPING_DANGER):
        return False
    owned = state.resources.get(npc_id, {})
    coins, food = owned.get(MONEY), owned.get("food")
    if (type(coins) is not int or not 1 <= coins <= MAX_AMOUNT
            or type(food) is not int or food != 0):
        return False
    nav = state.navigation.get(npc_id)
    if nav is not None and nav["target"] is not None:
        return False  # Explicit travel choices take precedence.
    here = entity["location_id"]
    if here in state.market_stalls:
        return False  # At an actual local stall: ordinary price/stock checks decide.
    return True


def choose_known_market_walk(state: WorldState, npc_id: str) -> ShoppingWalkIntent | None:
    """One real road toward a personally unexplored reachable location.

    Only the NPC's OWN surveyed route identifiers, own visited locations,
    and public travel durations of those learned roads enter pathfinding.
    Unknown shops and distant inventory are never inspected. No teleport.
    """
    if not wants_local_market(state, npc_id):
        return None
    nav = state.navigation.get(npc_id)
    if nav is None:
        return None  # Caller must first survey adjacent roads while on-site.
    here = state.entities[npc_id]["location_id"]
    candidates: list[tuple[int, str, tuple[str, ...]]] = []
    reachable = set()
    for rid in nav["known_routes"]:
        road = state.routes[rid]
        reachable.add(road["a"])
        reachable.add(road["b"])
    for destination in sorted(reachable - set(nav["visited"]) - {here}):
        path = shortest_known_route(state, npc_id, destination)
        if path:
            candidates.append((
                sum(state.routes[r]["seconds"] for r in path),
                destination, path,
            ))
    if not candidates:
        return None
    _, destination, path = min(candidates)
    return ShoppingWalkIntent(
        npc_id, path[0], destination,
        "hungry funded shopper exploring personally known roads; "
        f"unvisited_destination={destination}",
    )


def choose_known_market_return(state: WorldState, npc_id: str) -> ShoppingWalkIntent | None:
    """Return from a completed *actual* market meal via normal known work roads.

    Historical paid-food receipts and an actual subsequent meal at that same
    stall authorize this intent; merely reaching a stall or possessing money
    does not. The existing routine selector checks shift and personal health.
    Unreachable home/work routes are not invented.
    """
    if (npc_id not in state.npcs or not _free(state, npc_id)
            or npc_id in state.supply_circuits
            or npc_id not in state.npc_routines):
        return None
    personal_trades = [
        t for t in state.market_trades.values()
        if t["buyer_id"] == npc_id and t["resource"] == "food"
    ]
    if not personal_trades or not any(
            m["npc_id"] == npc_id and m["location_id"] == t["site_id"]
            and m["consumed_at"] >= t["executed_at"]
            for t in personal_trades for m in state.consumptions.values()):
        return None
    back = choose_routine_route(state, npc_id)
    if back is None:
        return None
    return ShoppingWalkIntent(
        npc_id, back.route_id, back.destination,
        "returning after locally paid and eaten market food; "
        f"known_routine_destination={back.destination}",
    )
