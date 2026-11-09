"""PLAY-44: optional NPC professional grain sales, procurement and real road trips.

Everything here is a PURE local-intent selector. The existing trusted market,
workshop and movement reducers remain final authorities, with real receipts.
Unknown remote stock and posted prices are never inputs to destination planning.
A professional remembers a supplier only through their OWN completed trade.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain import WorldState
from .economic_autonomy import _free, _known, _event_id
from .market import MONEY, MAX_AMOUNT, MAX_QUANTITY, _present, trade_receipt_allowed
from .navigation import shortest_known_route
from .npc import _injury_rest_decision
from .routines import routine_allows_work

GRAIN_PRICE_COPPER = 2


@dataclass(frozen=True)
class GrainOffer:
    site_id: str
    offer_id: str
    quantity: int
    unit_price: int
    reason: str


@dataclass(frozen=True)
class GrainPurchase:
    offer_id: str
    trade_id: str
    unit_price: int
    reason: str


@dataclass(frozen=True)
class GrainDeposit:
    site_id: str
    resource: str
    quantity: int


@dataclass(frozen=True)
class ProfessionalWalk:
    route_id: str
    destination: str
    reason: str


def _recipe(state: WorldState, who: str):
    if who not in state.npcs:
        return None
    routine = state.npc_routines.get(who)
    if routine is None or routine["workplace_id"] is None:
        return None
    site = routine["workplace_id"]
    for rec in sorted(state.production_recipes.values(),
                      key=lambda r: r["id"]):
        if (rec["site_id"] == site and rec["role"] == state.npcs[who]["role"]
                and rec["input_resource"] == "grain"):
            return rec
    return None


def has_workshop_recipe(state: WorldState, who: str) -> bool:
    """A configured, real grain-using workshop worker, not every villager."""
    return _recipe(state, who) is not None


def _healthy(state: WorldState, who: str) -> bool:
    needs = state.npcs[who]["needs"]
    return (needs["hunger"] < 90 and needs["fatigue"] < 70
            and needs["safety"] < 75
            and _injury_rest_decision(state.injuries, who) is None)


def choose_local_grain_offer(state: WorldState, keeper: str) -> GrainOffer | None:
    """A farmer sees only their own current site stock and registered counter."""
    if (keeper not in state.npcs or state.npcs[keeper]["role"] != "farmer"
            or not _free(state, keeper)):
        return None
    here = state.entities[keeper]["location_id"]
    stall = state.market_stalls.get(here)
    if stall is None or stall["keeper_id"] != keeper:
        return None
    if not _present(state.to_dict(), keeper, here):
        return None
    stock = state.resources.get(here, {})
    grain, copper = stock.get("grain"), stock.get(MONEY)
    if not _known(grain) or not _known(copper) or grain < 1:
        return None
    if any(o["status"] == "open" and o["site_id"] == here
           and o["resource"] == "grain" for o in state.market_offers.values()):
        return None
    quantity = min(grain, MAX_QUANTITY, (MAX_AMOUNT - copper) // GRAIN_PRICE_COPPER)
    if quantity < 1:
        return None
    ident = _event_id("local-grain", keeper, state.time)
    if ident in state.market_offers:
        return None
    return GrainOffer(
        here, ident, quantity, GRAIN_PRICE_COPPER,
        f"farmer_stock={grain}; opening_price={GRAIN_PRICE_COPPER}; owned_site={here}",
    )


def choose_local_grain_purchase(state: WorldState, who: str) -> GrainPurchase | None:
    """Only current-site visible quotes; no lookup at the remote bakery."""
    rec = _recipe(state, who)
    if rec is None or not _free(state, who) or not _healthy(state, who):
        return None
    here = state.entities[who]["location_id"]
    if here == rec["site_id"] or here not in state.market_stalls:
        return None
    if not _present(state.to_dict(), who, here):
        return None
    personal = state.resources.get(who, {})
    bag, copper = personal.get("grain"), personal.get(MONEY)
    if not _known(bag) or bag > 0 or not _known(copper):
        return None
    available = []
    raw = state.to_dict()
    for offer_id, offer in sorted(state.market_offers.items()):
        if (offer["site_id"] != here or offer["status"] != "open"
                or offer["resource"] != "grain" or
                offer["payment_resource"] != MONEY
                or offer["seller_id"] == who or offer["stock_owner_id"] == who
                or not trade_receipt_allowed(state.supply_circuits, who, "grain")
                or not trade_receipt_allowed(state.supply_circuits, offer["stock_owner_id"], MONEY)
                or offer["remaining"] < 1):
            continue
        price = offer["unit_price"]
        seller = offer["seller_id"]
        seller_stock = state.resources.get(offer["stock_owner_id"], {})
        grain, till = seller_stock.get("grain"), seller_stock.get(MONEY)
        if (not _known(price) or price < 1 or copper < price
                or not _known(grain) or grain < 1
                or not _known(till) or till + price > MAX_AMOUNT
                or not _present(raw, seller, here)):
            continue
        available.append((price, offer_id))
    if not available:
        return None
    price, offer_id = min(available)
    tid = _event_id("professional-grain", who, state.time)
    if tid in state.market_trades:
        return None
    return GrainPurchase(
        offer_id, tid, price,
        f"observed_local_grain_quote={offer_id}; own_wallet={copper}",
    )


def choose_workshop_input_deposit(state: WorldState, who: str) -> GrainDeposit | None:
    """At their workplace, deliver their own purchased bag goods into stock."""
    rec = _recipe(state, who)
    if rec is None or not _free(state, who):
        return None
    site = rec["site_id"]
    if state.entities[who]["location_id"] != site:
        return None
    owned = state.resources.get(who, {}).get("grain")
    stock = state.resources.get(site, {}).get("grain")
    if (not _known(owned) or not _known(stock) or owned <= 0
            or stock >= rec["input_amount"]):
        return None
    # The event reducer checks physical presence, role, overflow and custody.
    quantity = min(owned, rec["input_amount"] - stock, MAX_QUANTITY - stock)
    return GrainDeposit(site, "grain", quantity) if quantity >= 1 else None


def _latest_work_arrival(state: WorldState, who: str, site: str) -> int:
    return max((t["arrived_at"] for t in state.travels.values()
                if t["npc_id"] == who and t["status"] == "arrived"
                and t["destination"] == site), default=-1)


def _latest_supplier_arrival(state: WorldState, who: str, work: str) -> int:
    return max((t["arrived_at"] for t in state.travels.values()
                if t["npc_id"] == who and t["status"] == "arrived"
                and t["destination"] in state.market_stalls
                and t["destination"] != work), default=-1)


def _latest_wage(state: WorldState, who: str) -> int:
    return max((j["work_wage"]["paid_at"] for j in state.production_jobs.values()
                if j["npc_id"] == who and "work_wage" in j), default=-1)


def _known_frontier(state: WorldState, who: str):
    """Choose only a physically surveyed reachable UNVISITED road endpoint."""
    nav = state.navigation.get(who)
    if nav is None:
        return None
    here = state.entities[who]["location_id"]
    visited = set(nav["visited"])
    options = []
    for rid in nav["known_routes"]:
        road = state.routes[rid]
        if here not in (road["a"], road["b"]):
            continue
        other = road["b"] if road["a"] == here else road["a"]
        if other in visited:
            continue
        options.append((road["seconds"], other, rid))
    return min(options) if options else None


def choose_professional_known_road(state: WorldState, who: str) -> ProfessionalWalk | None:
    """Walk by actual road knowledge, not globally visible offers or goods."""
    rec = _recipe(state, who)
    if rec is None or not _free(state, who) or not _healthy(state, who):
        return None
    nav = state.navigation.get(who)
    if nav is None or nav["target"] is not None:
        return None
    work = rec["site_id"]
    here = state.entities[who]["location_id"]
    own = state.resources.get(who, {})
    if not _known(own.get("grain")) or not _known(own.get(MONEY)):
        return None
    personal_grain = own["grain"]
    latest_market = _latest_supplier_arrival(state, who, work)
    last_work = _latest_work_arrival(state, who, work)

    if here != work:
        # Returning is proven by past PERSONAL physical arrival, or by a
        # personal purchased bag. No remote stock/quote is inspected.
        if personal_grain > 0 or latest_market > last_work:
            path = shortest_known_route(state, who, work)
            if path:
                return ProfessionalWalk(
                    path[0], work, "known-workplace-return-after-actual-visit",
                )
            return None
        frontier = _known_frontier(state, who)
        if frontier is not None:
            return ProfessionalWalk(frontier[2], frontier[1],
                                    "explore-personally-surveyed-frontier")
        path = shortest_known_route(state, who, work)
        if path:
            return ProfessionalWalk(path[0], work,
                                    "surveyed-dead-end-return")
        return None

    # These *local workplace* resources define the economic need.
    # They are never consulted when choosing to BUY at a distant stall.
    local = state.resources.get(work, {})
    grain = local.get("grain")
    output = local.get(rec["output_resource"])
    tool = local.get(rec["tool_resource"])
    if (not all(_known(v) for v in (grain, output, tool))
            or grain >= rec["input_amount"] or output > 0 or tool < 1
            or personal_grain > 0 or own[MONEY] < 1
            or not routine_allows_work(state, who)):
        return None

    # A prior visit cannot be repeated just because the worker remains
    # hungry or the village remains short. New *recorded earned wages* are
    # sufficient grounds for a new trip; neither stock nor remote price
    # are queried here.
    if latest_market >= 0 and _latest_wage(state, who) <= latest_market:
        return None
    past = sorted(
        ((t["executed_at"], t["site_id"]) for t in state.market_trades.values()
         if t["buyer_id"] == who and t["resource"] == "grain"
         and t["site_id"] != work), reverse=True,
    )
    for _, site in past:
        path = shortest_known_route(state, who, site)
        if path:
            return ProfessionalWalk(
                path[0], site, "return-to-personally-purchased-supplier-after-new-wage",
            )
    frontier = _known_frontier(state, who)
    if frontier is None:
        return None
    return ProfessionalWalk(frontier[2], frontier[1],
                            "unknown-supplier-exploration-on-known-road")
