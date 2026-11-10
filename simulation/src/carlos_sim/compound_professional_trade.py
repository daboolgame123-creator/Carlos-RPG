"""PLAY-46 opt-in compound NPC material procurement, with local knowledge only.

A worker knows their OWN recipe and the first-hand receipts of their trade
journeys. Their workplace's stock is read only when they are physically there.
At a seller, only that seller's *current local* quote can be evaluated.
An unresolved material can trigger exploration on personally surveyed roads.
No remote prices, global supplier list, fabricated coins or teleports.
"""
from __future__ import annotations

from .domain import WorldState
from .production import recipe_inputs
from .economic_autonomy import _free, _known, _event_id
from .market import MONEY, MAX_AMOUNT, MAX_QUANTITY, _present, trade_receipt_allowed
from .navigation import shortest_known_route
from .professional_trade import (
    _healthy, _known_frontier, _latest_supplier_arrival,
    _latest_work_arrival,
)
from .multi_professional_trade import (
    MaterialDeposit, MaterialOffer, MaterialPurchase, MaterialWalk,
    _unreserved_personal,
)
from .routines import routine_allows_work


def _compound_recipe(state: WorldState, who: str):
    if who not in state.npcs:
        return None
    profile = state.npc_routines.get(who)
    if profile is None or profile["workplace_id"] is None:
        return None
    work = profile["workplace_id"]
    return next((
        rec for rec in sorted(state.production_recipes.values(),
                              key=lambda r: r["id"])
        if rec["site_id"] == work and rec["role"] == state.npcs[who]["role"]
        and "inputs" in rec
    ), None)


def has_compound_recipe(state: WorldState, who: str) -> bool:
    return _compound_recipe(state, who) is not None


def _cycle_start(state: WorldState, who: str, recipe: dict) -> int:
    """Production, rather than time wallclock, resets known input receipts."""
    return max((job["started_at"] for job in state.production_jobs.values()
                if job["npc_id"] == who and job["recipe_id"] == recipe["id"]),
               default=-1)


def _purchased_since(state: WorldState, who: str, item: str, after: int) -> int:
    return sum(t["quantity"] for t in state.market_trades.values()
               if t["buyer_id"] == who and t["resource"] == item
               and t["executed_at"] > after)


def _last_visit(state: WorldState, who: str, site: str) -> int:
    return max((t["arrived_at"] for t in state.travels.values()
                if t["npc_id"] == who and t["status"] == "arrived"
                and t["destination"] == site), default=-1)


def choose_charcoal_offer(state: WorldState, keeper: str) -> MaterialOffer | None:
    """Only a present registered charcoal burner may quote finite local fuel."""
    if (keeper not in state.npcs
            or state.npcs[keeper]["role"] != "charcoal_burner"
            or not _free(state, keeper)):
        return None
    site = state.entities[keeper]["location_id"]
    stall = state.market_stalls.get(site)
    if stall is None or stall["keeper_id"] != keeper:
        return None
    if not _present(state.to_dict(), keeper, site):
        return None
    local = state.resources.get(site, {})
    qty, copper = local.get("charcoal"), local.get(MONEY)
    if not _known(qty) or qty == 0 or not _known(copper):
        return None
    if any(o["site_id"] == site and o["resource"] == "charcoal"
           and o["status"] == "open" for o in state.market_offers.values()):
        return None
    quantity = min(qty, MAX_QUANTITY, MAX_AMOUNT - copper)
    if quantity < 1:
        return None
    ident = _event_id("charcoal-offer", keeper, state.time)
    if ident in state.market_offers:
        return None
    return MaterialOffer(site, ident, "charcoal", quantity, 1,
                         f"physically_owned_fuel={qty}")


def choose_compound_deposit(state: WorldState, who: str) -> MaterialDeposit | None:
    rec = _compound_recipe(state, who)
    if rec is None or not _free(state, who):
        return None
    site = rec["site_id"]
    if state.entities[who]["location_id"] != site:
        return None
    work_stock = state.resources.get(site, {})
    for item, needed in recipe_inputs(rec):
        owned = _unreserved_personal(state, who, item)
        local = work_stock.get(item)
        if (not _known(owned) or not _known(local)
                or owned < 1 or local >= needed):
            continue
        quantity = min(owned, needed-local, MAX_QUANTITY-local)
        if quantity:
            return MaterialDeposit(site, item, quantity)
    return None


def choose_compound_purchase(state: WorldState, who: str) -> MaterialPurchase | None:
    """Use actual co-present offers, not remote shop status or workshop stock."""
    rec = _compound_recipe(state, who)
    if rec is None or not _free(state, who) or not _healthy(state, who):
        return None
    site = state.entities[who]["location_id"]
    if site == rec["site_id"] or site not in state.market_stalls:
        return None
    if not _present(state.to_dict(), who, site):
        return None
    copper = _unreserved_personal(state, who, MONEY)
    if copper is None or copper < 1:
        return None
    started = _cycle_start(state, who, rec)
    candidates = []
    present = state.to_dict()
    for item, needed in recipe_inputs(rec):
        bag = _unreserved_personal(state, who, item)
        if bag is None or bag > 0:
            continue
        # The worker knows only its contract and its OWN receipts since the
        # last job. It never reads the distant workshop's actual stock here.
        if _purchased_since(state, who, item, started) >= needed:
            continue
        for offer_id, offer in sorted(state.market_offers.items()):
            if (offer["site_id"] != site or offer["status"] != "open"
                    or offer["resource"] != item or offer["payment_resource"] != MONEY
                    or offer["remaining"] < 1 or offer["seller_id"] == who
                    or offer["stock_owner_id"] == who
                    or not trade_receipt_allowed(state.supply_circuits, who, item)
                    or not trade_receipt_allowed(state.supply_circuits, offer["stock_owner_id"], MONEY)):
                continue
            owner_stock = state.resources.get(offer["stock_owner_id"], {})
            price = offer["unit_price"]
            if (not _known(price) or price < 1 or price > copper
                    or not _known(owner_stock.get(item))
                    or owner_stock[item] < 1
                    or not _known(owner_stock.get(MONEY))
                    or owner_stock[MONEY] + price > MAX_AMOUNT
                    or not _present(present, offer["seller_id"], site)):
                continue
            candidates.append((price, item, offer_id))
    if not candidates:
        return None
    price, item, offer_id = min(candidates)
    ident = _event_id("compound-purchase", who, state.time)
    if ident in state.market_trades:
        return None
    return MaterialPurchase(
        offer_id, ident, price,
        f"firsthand_quote={offer_id}; contract_input={item}; own_copper={copper}"
    )


def choose_compound_known_road(
    state: WorldState, who: str, *, retry_after_seconds: int | None = None
) -> MaterialWalk | None:
    """Contract-driven real travel without remote stock inspection."""
    if (retry_after_seconds is not None
            and (type(retry_after_seconds) is not int
                 or not 600 <= retry_after_seconds <= 86400)):
        raise ValueError("known supplier revisit needs bounded positive interval")
    rec = _compound_recipe(state, who)
    if rec is None or not _free(state, who) or not _healthy(state, who):
        return None
    nav = state.navigation.get(who)
    if nav is None or nav["target"] is not None:
        return None
    work = rec["site_id"]
    here = state.entities[who]["location_id"]
    personal_coins = _unreserved_personal(state, who, MONEY)
    if personal_coins is None:
        return None
    needs = recipe_inputs(rec)
    bag = {item: _unreserved_personal(state, who, item)
           for item, _ in needs}
    if any(qty is None for qty in bag.values()):
        return None

    if here != work:
        visited_market = _latest_supplier_arrival(state, who, work)
        last_work = _latest_work_arrival(state, who, work)
        if any(amount > 0 for amount in bag.values()) or visited_market > last_work:
            path = shortest_known_route(state, who, work)
            if path:
                return MaterialWalk(path[0], work, "return-with-owned-input-or-after-stall")
            return None
        next_unknown = _known_frontier(state, who)
        if next_unknown is not None:
            return MaterialWalk(next_unknown[2], next_unknown[1],
                                "personally-surveyed-unvisited-road")
        path = shortest_known_route(state, who, work)
        return MaterialWalk(path[0], work, "return-after-survey") if path else None

    local = state.resources.get(work, {})
    output = local.get(rec["output_resource"])
    tool = local.get(rec["tool_resource"])
    if (not _known(output) or output > 0 or not _known(tool) or tool < 1
            or personal_coins < 1 or not routine_allows_work(state, who)):
        return None
    missing = [
        item for item, amount in needs
        if _known(local.get(item)) and local[item] < amount
    ]
    if not missing or any(not _known(local.get(item)) for item, _ in needs):
        return None
    if any(bag[item] > 0 for item in missing):
        return None

    # The known, personally successful supplier can be revisited for the
    # same input only if its last FIRSTHAND visit ended in a real purchase.
    for item in missing:
        visits = sorted(
            ((t["executed_at"], t["site_id"]) for t in state.market_trades.values()
             if t["buyer_id"] == who and t["resource"] == item
             and t["site_id"] != work), reverse=True)
        for traded_at, place in visits:
            if traded_at < _last_visit(state, who, place):
                continue  # last visit failed; do not oscillate indefinitely
            path = shortest_known_route(state, who, place)
            if path:
                return MaterialWalk(path[0], place,
                                    f"firsthand_supplier_of={item}")
    # PLAY48-N opt-in: ONE HOUR after an actual first-hand unsuccessful
    # shop visit, a solvent worker may walk there again. This is not a
    # remotely read stock/quote. A real medieval shop may replenish while
    # its customer is away. Require a personally VISITED and still reachable
    # supplier with a publicly observed occupational trade; no absent
    # shop can be found solely through omniscient global market listings.
    if retry_after_seconds is not None:
        source_role = {
            "charcoal": "charcoal_burner",
            "iron_ore": "miner",
            "wood": "woodcutter",
        }
        options = []
        visited = set(nav["visited"])
        for item in missing:
            required_role = source_role.get(item)
            if required_role is None:
                continue
            for place in visited:
                if place == work or place not in state.market_stalls:
                    continue
                keeper = state.market_stalls[place]["keeper_id"]
                if state.npcs[keeper]["role"] != required_role:
                    continue
                arrival = _last_visit(state, who, place)
                if arrival < 0 or state.time-arrival < retry_after_seconds:
                    continue
                path = shortest_known_route(state, who, place)
                if path:
                    options.append((path[0], place, item))
        if options:
            route_id, place, item = min(options)
            return MaterialWalk(route_id, place,
                                f"bounded_firsthand_shop_retry_for={item}")
    unknown = _known_frontier(state, who)
    if unknown is None:
        return None
    return MaterialWalk(unknown[2], unknown[1],
                        f"explore_for_local_shortage={missing[0]}")
