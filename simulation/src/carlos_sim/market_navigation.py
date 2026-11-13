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
# A genuinely visited but unbought market may be retried after this much
# simulation time, without any oracle about its *current* stock or price.
UNBOUGHT_STALL_REVISIT_SECONDS = 6 * 3600


@dataclass(frozen=True)
class ShoppingWalkIntent:
    npc_id: str
    route_id: str
    destination: str
    reason: str


def _latest_wage_at(state: WorldState, npc_id: str) -> int:
    return max((job["work_wage"]["paid_at"] for job in state.production_jobs.values()
                if job["npc_id"] == npc_id and "work_wage" in job), default=-1)


def wants_local_market(state: WorldState, npc_id: str, *, repeat_errands=False,
                       seek_alternative_if_unaffordable=False) -> bool:
    """Hungry solvent buyer may inspect local prices, never remote stock.

    Optional genuine-survival search allows leaving an empty/too-expensive
    local market to survey adjacent known roads, not a teleported purchase.
    """
    if type(seek_alternative_if_unaffordable) is not bool:
        raise ValueError("alternate market search is opt-in boolean")
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
        if seek_alternative_if_unaffordable:
            # On-site quotations only: the buyer never observes a distant
            # price, seller, inventory or even a remote stall from here.
            from .market import _present, reserved_trade_units, trade_receipt_allowed
            physically_affordable = any(
                offer["status"] == "open"
                and offer["site_id"] == here
                and offer["resource"] == "food"
                and offer["payment_resource"] == MONEY
                and offer["seller_id"] != npc_id
                and offer["stock_owner_id"] != npc_id
                and offer["remaining"] >= 1
                and offer["unit_price"] <= coins
                and _present(state.to_dict(), offer["seller_id"], here)
                and trade_receipt_allowed(
                    state.supply_circuits, offer["stock_owner_id"], MONEY
                )
                and type(state.resources.get(
                    offer["stock_owner_id"], {}).get("food")) is int
                and state.resources[offer["stock_owner_id"]]["food"]
                    > reserved_trade_units(
                        state.supply_circuits, offer["stock_owner_id"], "food"
                    )
                for offer in state.market_offers.values()
            )
            if physically_affordable:
                return False
        elif (not repeat_errands or any(
                offer["site_id"] == here and offer["resource"] == "food"
                for offer in state.market_offers.values())):
            return False  # Historic mode does not abandon the home market.
    return True


def choose_known_market_walk(
    state: WorldState, npc_id: str, *, repeat_errands=False,
    remember_unbought_stalls=False,
    seek_alternative_if_unaffordable=False,
) -> ShoppingWalkIntent | None:
    """One real road toward a personally unexplored reachable location.

    Only the NPC's OWN surveyed route identifiers, own visited locations,
    and public travel durations of those learned roads enter pathfinding.
    Unknown shops and distant inventory are never inspected. No teleport.
    """
    # New policy is opt-in and cannot affect historical shopping modes.
    if (type(remember_unbought_stalls) is not bool
            or (remember_unbought_stalls and not repeat_errands)):
        raise ValueError("visited stall memory requires repeat errands")
    if not wants_local_market(
            state, npc_id, repeat_errands=repeat_errands,
            seek_alternative_if_unaffordable=seek_alternative_if_unaffordable):
        return None
    nav = state.navigation.get(npc_id)
    if nav is None:
        return None  # Caller must first survey adjacent roads while on-site.
    here = state.entities[npc_id]["location_id"]
    if repeat_errands:
        wage_at = _latest_wage_at(state, npc_id)
        # Only personal purchases reveal a remote food destination. A new
        # wage permits one fresh attempt, even on a previously visited route.
        previous_sites = {
            trade["site_id"] for trade in state.market_trades.values()
            if trade["buyer_id"] == npc_id and trade["resource"] == "food"
            and trade["executed_at"] < wage_at
        }
        if remember_unbought_stalls and wage_at >= 0:
            # Completed personal road arrival BEFORE a later genuine wage
            # and a food offer already posted at the time of that arrival
            # are the only admissible evidence of a remembered stall.
            # No remote price, stock, cashier balance or unknown road is read.
            previous_sites.update(
                trip["destination"] for trip in state.travels.values()
                if trip["npc_id"] == npc_id and trip["status"] == "arrived"
                and trip["arrived_at"] < wage_at
                and trip["destination"] in state.market_stalls
                and any(
                    offer["site_id"] == trip["destination"]
                    and offer["resource"] == "food"
                    and offer["posted_at"] <= trip["arrived_at"]
                    for offer in state.market_offers.values()
                )
            )
        attempted_sites = {
            trip["destination"] for trip in state.travels.values()
            if trip["npc_id"] == npc_id and trip["status"] == "arrived"
            and trip["arrived_at"] >= wage_at
        }
        for destination in sorted(previous_sites - attempted_sites - {here}):
            path = shortest_known_route(state, npc_id, destination)
            if path:
                return ShoppingWalkIntent(
                    npc_id, path[0], destination,
                    ("funded shopper returning to a personally visited "
                     "food stall after a new authentic wage"
                     if remember_unbought_stalls else
                     "funded shopper returning to a personally used food stall"),
                )

        if remember_unbought_stalls and wage_at >= 0:
            # Crucial case missed by the first market-memory pilot: a worker
            # receives a real wage FIRST, THEN visits a food stall while it is
            # empty/unaffordable, and later still owns enough personal copper
            # to retry. No subsequent wage is required to remember a place
            # their OWN feet have already reached.
            #
            # Apply a strict clock cooldown from the LATEST physical arrival,
            # not from a remote price/stock update. This is bounded curiosity,
            # not a daily oracle that reveals whether bread has been restocked.
            first_hand_last_arrival = {}
            for trip in state.travels.values():
                if (trip["npc_id"] != npc_id or trip["status"] != "arrived"
                        or trip["destination"] not in state.market_stalls):
                    continue
                destination = trip["destination"]
                arrived = trip["arrived_at"]
                if not any(
                    offer["site_id"] == destination
                    and offer["resource"] == "food"
                    and offer["posted_at"] <= arrived
                    for offer in state.market_offers.values()
                ):
                    continue
                first_hand_last_arrival[destination] = max(
                    arrived, first_hand_last_arrival.get(destination, -1)
                )
            for destination, arrived in sorted(first_hand_last_arrival.items()):
                if (destination == here
                        or state.time - arrived < UNBOUGHT_STALL_REVISIT_SECONDS
                        or any(
                            trade["buyer_id"] == npc_id
                            and trade["resource"] == "food"
                            and trade["site_id"] == destination
                            and trade["executed_at"] >= arrived
                            for trade in state.market_trades.values()
                        )):
                    continue
                path = shortest_known_route(state, npc_id, destination)
                if path:
                    return ShoppingWalkIntent(
                        npc_id, path[0], destination,
                        "hungry solvent shopper revisiting a food stall "
                        "personally encountered at least six hours earlier",
                    )

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


def choose_known_market_return(
    state: WorldState, npc_id: str, *, repeat_errands=False,
) -> ShoppingWalkIntent | None:
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
    # A personally completed trip is sufficient evidence of a visited stall.
    # Do not require the villager to still be on that market tile when their
    # next physical homeward road leg is due.
    wage_at = _latest_wage_at(state, npc_id) if repeat_errands else -1
    arrivals = sorted(
        ((t["arrived_at"], t["destination"]) for t in state.travels.values()
         if t["npc_id"] == npc_id and t["status"] == "arrived"
         and t["arrived_at"] >= wage_at
         and t["destination"] in state.market_stalls
         and (not repeat_errands or any(
             offer["site_id"] == t["destination"] and offer["resource"] == "food"
             and offer["posted_at"] <= t["arrived_at"]
             for offer in state.market_offers.values()
         ))),
    )
    if not arrivals:
        return None
    arrival, market_site = arrivals[-1]
    departed = any(
        t["npc_id"] == npc_id and t["origin"] == market_site
        and t["start"] >= arrival and t["status"] == "arrived"
        for t in state.travels.values()
    )
    if here != market_site and not departed:
        return None
    if not any(
            job["npc_id"] == npc_id and "work_wage" in job
            and job["work_wage"]["paid_at"] <= arrival
            for job in state.production_jobs.values()):
        return None

    # A purchased and subsequently eaten loaf is evidence of a completed
    # errand. Only transactions after this physical arrival count.
    own_meals = [
        meal for meal in state.consumptions.values()
        if meal["npc_id"] == npc_id and meal["location_id"] == market_site
        and meal["consumed_at"] >= arrival
    ]
    fed = any(
        trade["buyer_id"] == npc_id and trade["site_id"] == market_site
        and trade["resource"] == "food" and trade["executed_at"] >= arrival
        and trade["executed_at"] <= meal["consumed_at"]
        for trade in state.market_trades.values() for meal in own_meals
    )
    if not fed and here == market_site:
        wallet = state.resources.get(npc_id, {})
        coins, food = wallet.get(MONEY), wallet.get("food")
        if type(food) is not int or food > 0 or type(coins) is not int:
            return None
        # Check only ACTUALLY LOCAL, publicly posted offers, not distant stock
        # or future deliveries. Do not leave merely because a decision cooldown
        # temporarily prevents an otherwise affordable purchase.
        raw = state.to_dict()
        from .market import _present, reserved_trade_units, trade_receipt_allowed
        affordable = any(
            offer["status"] == "open" and offer["site_id"] == here
            and offer["resource"] == "food"
            and offer["payment_resource"] == MONEY
            and offer["remaining"] >= 1
            and offer["unit_price"] <= coins
            and offer["seller_id"] != npc_id
            and offer["stock_owner_id"] != npc_id
            and trade_receipt_allowed(state.supply_circuits, offer["stock_owner_id"], MONEY)
            and _present(raw, offer["seller_id"], here)
            and state.resources.get(offer["stock_owner_id"], {}).get("food", 0)
                > reserved_trade_units(state.supply_circuits, offer["stock_owner_id"], "food")
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
