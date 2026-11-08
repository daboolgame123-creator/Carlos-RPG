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
    """Walk back after an actual visit, whether the purchase succeeded or not.

    This is a return from a personally reached LOCAL market, never a query to
    remote shops. A completed, real wage must precede the market arrival.
    A valid affordable local quote keeps the shopper at the stall; an
    unaffordable or unavailable offer does not imprison a hungry worker.
    A genuine paid meal also permits return to the established routine.
    """
    if (npc_id not in state.npcs or not _free(state, npc_id)
            or npc_id in state.supply_circuits
            or npc_id not in state.npc_routines):
        return None
    entity = state.entities.get(npc_id)
    if entity is None or entity["controller"] != "npc":
        return None
    nav = state.navigation.get(npc_id)
    if nav is None or nav["target"] is not None:
        return None
    here = entity["location_id"]
    if here not in state.market_stalls:
        return None
    # The NPC must have *arrived*, not merely be at an opening market.
    arrivals = sorted(
        (t["arrived_at"] for t in state.travels.values()
         if t["npc_id"] == npc_id and t["destination"] == here
         and t["status"] == "arrived"),
    )
    if not arrivals:
        return None
    arrival = arrivals[-1]
    if not any(
            job["npc_id"] == npc_id and "work_wage" in job
            and job["work_wage"]["paid_at"] <= arrival
            for job in state.production_jobs.values()):
        return None

    # A purchased and subsequently eaten loaf is evidence of a completed
    # errand. Only transactions after this physical arrival count.
    own_meals = [
        meal for meal in state.consumptions.values()
        if meal["npc_id"] == npc_id and meal["location_id"] == here
        and meal["consumed_at"] >= arrival
    ]
    fed = any(
        trade["buyer_id"] == npc_id and trade["site_id"] == here
        and trade["resource"] == "food" and trade["executed_at"] >= arrival
        and trade["executed_at"] <= meal["consumed_at"]
        for trade in state.market_trades.values() for meal in own_meals
    )
    if not fed:
        wallet = state.resources.get(npc_id, {})
        coins, food = wallet.get(MONEY), wallet.get("food")
        if type(food) is not int or food > 0 or type(coins) is not int:
            return None
        # Check only ACTUALLY LOCAL, publicly posted offers, not distant stock
        # or future deliveries. Do not leave merely because a decision cooldown
        # temporarily prevents an otherwise affordable purchase.
        raw = state.to_dict()
        from .market import _present
        affordable = any(
            offer["status"] == "open" and offer["site_id"] == here
            and offer["resource"] == "food"
            and offer["payment_resource"] == MONEY
            and offer["remaining"] >= 1
            and offer["unit_price"] <= coins
            and offer["seller_id"] != npc_id
            and offer["stock_owner_id"] != npc_id
            and _present(raw, offer["seller_id"], here)
            and state.resources.get(offer["stock_owner_id"], {}).get("food", 0) >= 1
            for offer in state.market_offers.values()
        )
        if affordable:
            return None

    npc = state.npcs[npc_id]
    if npc["needs"]["fatigue"] >= 70 or npc["needs"]["safety"] >= 75:
        return None
    from .npc import _injury_rest_decision
    if _injury_rest_decision(state.injuries, npc_id) is not None:
        return None
    from .routines import DAY_SECONDS
    profile = state.npc_routines[npc_id]
    now = state.time % DAY_SECONDS
    start, end = profile["work_start"], profile["work_end"]
    at_work = start <= now < end if start < end else now >= start or now < end
    destination = (
        profile["workplace_id"] if at_work and profile["workplace_id"] is not None
        else profile["home_id"]
    )
    if destination == here:
        return None
    known_path = shortest_known_route(state, npc_id, destination)
    if not known_path:
        return None
    return ShoppingWalkIntent(
        npc_id, known_path[0], destination,
        "returning from physically visited market after "
        + ("paid meal" if fed else "unavailable/unaffordable local food")
        + f"; known_routine_destination={destination}",
    )
