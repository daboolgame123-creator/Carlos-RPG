"""PLAY-45: material-driven NPC professions in a finite, physical village.

These pure selectors propose intentions; existing market, workshop, movement,
production and wage reducers remain the only authorities. No remote inventory,
price, magic stock or unearned money participates in route selection.
PLAY-44's grain planner is intentionally separate and unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain import WorldState
from .economic_autonomy import _event_id, _free, _known
from .market import MONEY, MAX_AMOUNT, MAX_QUANTITY, _present, trade_receipt_allowed
from .navigation import shortest_known_route
from .professional_trade import (
    _healthy, _known_frontier, _latest_supplier_arrival,
    _latest_wage, _latest_work_arrival,
)
from .routines import routine_allows_work

# Explicit bounded experimental prices. Quotes are real, local events; their
# price never changes behind a customer's back.
MATERIAL_PRICE = {
    "wood": 1,
    "iron_ore": 1,
    "plank": 2,
    "iron_fitting": 2,
}
RAW_SUPPLIER = {
    "woodcutter": "wood",
    "miner": "iron_ore",
}


@dataclass(frozen=True)
class MaterialOffer:
    site_id: str
    offer_id: str
    resource: str
    quantity: int
    unit_price: int
    reason: str


@dataclass(frozen=True)
class MaterialPurchase:
    offer_id: str
    trade_id: str
    unit_price: int
    reason: str


@dataclass(frozen=True)
class MaterialDeposit:
    site_id: str
    resource: str
    quantity: int


@dataclass(frozen=True)
class MaterialWalk:
    route_id: str
    destination: str
    reason: str


def _unreserved_personal(state: WorldState, who: str, resource: str) -> int | None:
    """Do not spend or deposit somebody else's courier-consigned parcel."""
    amount = state.resources.get(who, {}).get(resource)
    if not _known(amount):
        return None
    circuit = state.supply_circuits.get(who)
    cargo = circuit["carry"] if circuit is not None else None
    reserved = int(cargo is not None and cargo["resource"] == resource)
    return amount - reserved if amount >= reserved else None


def _recipe(state: WorldState, who: str):
    """The buyer's own scheduled workplace contract, not a remote recipe."""
    npc = state.npcs.get(who)
    routine = state.npc_routines.get(who)
    if npc is None or routine is None:
        return None
    workplace = routine["workplace_id"]
    if workplace is None:
        return None
    return next((
        recipe for recipe in sorted(
            state.production_recipes.values(), key=lambda rec: rec["id"]
        )
        if recipe["site_id"] == workplace
        and recipe["role"] == npc["role"]
        and recipe.get("input_resource") in MATERIAL_PRICE
    ), None)


def has_material_workshop_recipe(state: WorldState, who: str) -> bool:
    return _recipe(state, who) is not None


def choose_local_material_offer(state: WorldState, keeper: str) -> MaterialOffer | None:
    """Offer only locally owned and initialized input or finished stock."""
    if keeper not in state.npcs or not _free(state, keeper):
        return None
    site = state.entities[keeper]["location_id"]
    stall = state.market_stalls.get(site)
    if stall is None or stall["keeper_id"] != keeper:
        return None
    if not _present(state.to_dict(), keeper, site):
        return None
    stock = state.resources.get(site, {})
    copper = stock.get(MONEY)
    if not _known(copper):
        return None

    role = state.npcs[keeper]["role"]
    if role in RAW_SUPPLIER:
        resources = (RAW_SUPPLIER[role],)
    else:
        # At a productive workshop, sell only what this keeper physically
        # produced. Never advertise its needed input or reserved tools.
        resources = tuple(sorted({
            recipe["output_resource"]
            for recipe in state.production_recipes.values()
            if recipe["site_id"] == site and recipe["role"] == role
            and recipe["output_resource"] in MATERIAL_PRICE
        }))
    for resource in resources:
        quantity_here = stock.get(resource)
        unit_price = MATERIAL_PRICE[resource]
        if not _known(quantity_here) or quantity_here == 0:
            continue
        if any(offer["site_id"] == site and offer["resource"] == resource
               and offer["status"] == "open"
               for offer in state.market_offers.values()):
            continue
        quantity = min(quantity_here, MAX_QUANTITY,
                       (MAX_AMOUNT - copper) // unit_price)
        if quantity <= 0:
            continue
        offer_id = _event_id("multiquote", keeper, state.time)
        if offer_id in state.market_offers:
            continue
        return MaterialOffer(
            site, offer_id, resource, quantity, unit_price,
            f"local_owned={quantity_here}; item={resource}; price={unit_price}",
        )
    return None


def choose_local_material_purchase(state: WorldState, who: str) -> MaterialPurchase | None:
    """Do not know a seller's quote until physically at their stall."""
    recipe = _recipe(state, who)
    if recipe is None or not _free(state, who) or not _healthy(state, who):
        return None
    site = state.entities[who]["location_id"]
    if site == recipe["site_id"] or site not in state.market_stalls:
        return None
    if not _present(state.to_dict(), who, site):
        return None
    item = recipe["input_resource"]
    owned = state.resources.get(who, {})
    bag = _unreserved_personal(state, who, item)
    coins = _unreserved_personal(state, who, MONEY)
    if not _known(bag) or bag > 0 or not _known(coins):
        return None

    choices = []
    for offer_id, offer in sorted(state.market_offers.items()):
        if (offer["status"] != "open" or offer["site_id"] != site
                or offer["resource"] != item or offer["payment_resource"] != MONEY
                or offer["seller_id"] == who or offer["stock_owner_id"] == who
                or not trade_receipt_allowed(state.supply_circuits, who, item)
                or not trade_receipt_allowed(state.supply_circuits, offer["stock_owner_id"], MONEY)
                or offer["remaining"] < 1):
            continue
        price = offer["unit_price"]
        stock = state.resources.get(offer["stock_owner_id"], {})
        if (not _known(price) or price < 1 or coins < price
                or not _known(stock.get(item)) or stock[item] < 1
                or not _known(stock.get(MONEY))
                or stock[MONEY] + price > MAX_AMOUNT
                or not _present(state.to_dict(), offer["seller_id"], site)):
            continue
        choices.append((price, offer_id))
    if not choices:
        return None
    price, offer_id = min(choices)
    trade_id = _event_id("multipurchase", who, state.time)
    if trade_id in state.market_trades:
        return None
    return MaterialPurchase(
        offer_id, trade_id, price,
        f"observed_local={offer_id}; own_copper={coins}; material={item}",
    )


def choose_workshop_material_deposit(state: WorldState, who: str) -> MaterialDeposit | None:
    recipe = _recipe(state, who)
    if recipe is None or not _free(state, who):
        return None
    site = recipe["site_id"]
    if state.entities[who]["location_id"] != site:
        return None
    item = recipe["input_resource"]
    bag = _unreserved_personal(state, who, item)
    work_stock = state.resources.get(site, {}).get(item)
    if (not _known(bag) or not _known(work_stock) or bag < 1
            or work_stock >= recipe["input_amount"]):
        return None
    quantity = min(bag, recipe["input_amount"] - work_stock,
                   MAX_QUANTITY - work_stock)
    return MaterialDeposit(site, item, quantity) if quantity >= 1 else None


def choose_material_known_road(state: WorldState, who: str) -> MaterialWalk | None:
    """Explore only the person's own visited/surveyed route graph.

    The decision to leave is based solely on a *local* workshop shortage and
    the worker's personal wallet. No hidden market or remote stock is read.
    """
    recipe = _recipe(state, who)
    if recipe is None or not _free(state, who) or not _healthy(state, who):
        return None
    nav = state.navigation.get(who)
    if nav is None or nav["target"] is not None:
        return None
    site = recipe["site_id"]
    here = state.entities[who]["location_id"]
    item = recipe["input_resource"]
    own = state.resources.get(who, {})
    bag = _unreserved_personal(state, who, item)
    coins = _unreserved_personal(state, who, MONEY)
    if bag is None or coins is None:
        return None
    last_supplier = _latest_supplier_arrival(state, who, site)
    last_work = _latest_work_arrival(state, who, site)

    if here != site:
        if bag > 0 or last_supplier > last_work:
            path = shortest_known_route(state, who, site)
            if path:
                return MaterialWalk(
                    path[0], site, "physical-return-after-supplier-visit"
                )
            return None
        frontier = _known_frontier(state, who)
        if frontier is not None:
            return MaterialWalk(frontier[2], frontier[1],
                                "personally-surveyed-frontier")
        path = shortest_known_route(state, who, site)
        if path:
            return MaterialWalk(path[0], site, "surveyed-dead-end-return")
        return None

    local = state.resources.get(site, {})
    needed = local.get(item)
    output = local.get(recipe["output_resource"])
    tool = local.get(recipe["tool_resource"])
    if (not all(_known(v) for v in (needed, output, tool))
            or needed >= recipe["input_amount"] or output > 0 or tool < 1
            or bag > 0 or coins < 1
            or not routine_allows_work(state, who)):
        return None

    # A failed trip should not oscillate through the same market for ever.
    # Only actually earned wages can justify a repeated procurement attempt.
    if last_supplier >= 0 and _latest_wage(state, who) <= last_supplier:
        # A failed visit must not produce a loop, but a genuinely unvisited
        # directly surveyed road is still a bounded exploration opportunity.
        other = _known_frontier(state, who)
        if other is None:
            return None
        return MaterialWalk(other[2], other[1],
                            'unvisited-road-after-unsuccessful-supplier')
    history = sorted(
        ((t["executed_at"], t["site_id"])
         for t in state.market_trades.values()
         if t["buyer_id"] == who and t["resource"] == item
         and t["site_id"] != site),
        reverse=True,
    )
    for _, prior_site in history:
        path = shortest_known_route(state, who, prior_site)
        if path:
            return MaterialWalk(path[0], prior_site,
                                "self-receipt-supplier-repeat")
    frontier = _known_frontier(state, who)
    if frontier is None:
        return None
    return MaterialWalk(frontier[2], frontier[1],
                        "unknown-supplier-known-road")
