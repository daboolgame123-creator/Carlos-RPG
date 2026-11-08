"""PLAY-24: deterministic, opt-in economic intentions for real local NPCs.

These are pure selectors. Every proposed action is still verified by the
existing production/market reducers and committed through the trusted clock.
No credit, remote stock queries, resource creation or scripted NPC choices.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .domain import WorldState
from .market import MONEY, MAX_AMOUNT, MAX_QUANTITY as MARKET_MAX, _present
from .npc import _injury_rest_decision
from .production import MAX_QUANTITY as PRODUCTION_MAX
from .routines import DAY_SECONDS, routine_allows_work

BUY_HUNGER_THRESHOLD = 70
MAX_WORK_HUNGER = 89
MAX_WORK_FATIGUE = 69
TEST_FOOD_PRICE_COPPER = 2


@dataclass(frozen=True)
class ProductionIntent:
    npc_id: str
    recipe_id: str
    job_id: str
    reason: str


@dataclass(frozen=True)
class OfferIntent:
    keeper_id: str
    site_id: str
    offer_id: str
    quantity: int
    reason: str
    unit_price: int = TEST_FOOD_PRICE_COPPER


@dataclass(frozen=True)
class RetirementIntent:
    keeper_id: str
    offer_id: str
    reason: str


@dataclass(frozen=True)
class PurchaseIntent:
    buyer_id: str
    offer_id: str
    trade_id: str
    price: int
    reason: str


def _event_id(prefix: str, ident: str, tick: int) -> str:
    """An ASCII, reducer-compatible deterministic ID, including long site IDs."""
    raw = f"eco-{prefix}-{ident}-{tick}"
    if len(raw) <= 64 and all(c.isascii() and (c.isalnum() or c in "._-")
                               for c in raw):
        return raw
    return f"eco-{prefix}-" + sha256(raw.encode("utf-8")).hexdigest()[:48]


def _free(state: WorldState, who: str) -> bool:
    if who not in state.npcs:
        return False
    return (not any(a["npc_id"] == who and a["status"] == "running"
                    for a in state.actions.values())
            and not any(t["npc_id"] == who and t["status"] == "traveling"
                        for t in state.travels.values())
            and not any(j["npc_id"] == who and j["status"] == "running"
                        for j in state.production_jobs.values()))


def _known(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_AMOUNT


def choose_local_production(state: WorldState, npc_id: str, *,
                            agriculture_enabled: bool = False) -> ProductionIntent | None:
    """Worker starts one real batch as soon as local inputs and shift allow.

    The unrelated general NPC deliberation cooldown does not suppress a
    short-shift worker's physically available production opportunity. Same-tick
    duplicate choices remain blocked by last_decision and job/resource guards.
    """
    if not _free(state, npc_id):
        return None
    npc = state.npcs[npc_id]
    needs = npc["needs"]
    if (needs["hunger"] > MAX_WORK_HUNGER
            or needs["fatigue"] > MAX_WORK_FATIGUE
            or needs["safety"] >= 75
            or _injury_rest_decision(state.injuries, npc_id) is not None):
        return None
    last = npc["last_decision"]
    if last is not None and last["at"] == state.time:
        return None
    profile = state.npc_routines.get(npc_id)
    if profile is None or not routine_allows_work(state, npc_id):
        # No inferred shift, wages or economic mandate for unconfigured NPCs.
        return None
    here = state.entities[npc_id]["location_id"]
    if here != profile["workplace_id"]:
        return None
    for recipe_id, recipe in sorted(state.production_recipes.items()):
        if recipe["site_id"] != here or recipe["role"] != npc["role"]:
            continue
        remaining_shift = (profile["work_end"] - state.time % DAY_SECONDS) % DAY_SECONDS
        if recipe["duration_seconds"] > remaining_shift:
            continue
        if recipe["input_resource"] == "seed":
            field = state.farm_plots.get(here)
            resources = state.resources.get(here, {})
            if (not agriculture_enabled or field is None or field["status"] != "idle"
                    or resources.get("crop_ready") != 0
                    or resources.get("water", 0) < 1):
                continue
        stock = state.resources.get(here, {})
        input_amount = stock.get(recipe["input_resource"])
        output_amount = stock.get(recipe["output_resource"])
        tool_amount = stock.get(recipe["tool_resource"])
        if not all(_known(n) for n in (input_amount, output_amount, tool_amount)):
            continue
        if (input_amount < recipe["input_amount"] or tool_amount < 1
                or output_amount != 0
                or output_amount + recipe["output_amount"] > PRODUCTION_MAX):
            continue
        reservations = sum(
            1 for job in state.production_jobs.values()
            if job["status"] == "running" and job["site_id"] == here
            and state.production_recipes[job["recipe_id"]]["tool_resource"]
            == recipe["tool_resource"])
        if reservations >= tool_amount:
            continue
        ident = _event_id("job", npc_id, state.time)
        if ident in state.production_jobs or "production:" + ident in state.scheduled:
            continue
        return ProductionIntent(npc_id, recipe_id, ident,
                                f"on_shift; local_input={input_amount}; "
                                f"local_output={output_amount}; tool_free=1")
    return None


def choose_local_food_offer(state: WorldState, keeper_id: str, *,
                            adaptive: bool = False) -> OfferIntent | None:
    """Local seller prices only their physically owned stock; no omniscient demand.

    Adaptive prices are experimental and opt-in. Previously posted quotes never
    change behind a buyer's back; a new price needs a new physical offer.
    """
    if type(adaptive) is not bool:
        raise ValueError("adaptive market mode must be boolean")
    if not _free(state, keeper_id):
        return None
    here = state.entities[keeper_id]["location_id"]
    stall = state.market_stalls.get(here)
    if stall is None or stall["keeper_id"] != keeper_id:
        return None
    if not _present(state.to_dict(), keeper_id, here):
        return None
    food = state.resources.get(here, {}).get("food")
    coin = state.resources.get(here, {}).get(MONEY)
    if not _known(food) or not _known(coin) or food < 1:
        return None
    if any(o["status"] == "open" and o["stock_owner_id"] == here
           and o["resource"] == "food" for o in state.market_offers.values()):
        return None
    unit_price = (3 if food == 1 else 2 if food <= 3 else 1) if adaptive else TEST_FOOD_PRICE_COPPER
    amount = min(food, MARKET_MAX, (MAX_AMOUNT - coin) // unit_price)
    if amount < 1:
        return None
    ident = _event_id("offer", here, state.time)
    if ident in state.market_offers:
        return None
    return OfferIntent(keeper_id, here, ident, amount,
                       f"registered_steward; physically_stocked={food}; "
                       f"local_quote={unit_price}; adaptive={adaptive}",
                       unit_price)


def choose_local_offer_retirement(state: WorldState, keeper_id: str) -> RetirementIntent | None:
    """Withdraw an unfulfillable listing after a real on-site stock change.

    Listing retirement never refunds, reprices, transfers, or invents anything.
    The established MarketOfferClosed reducer still authorizes the seller.
    """
    if not _free(state, keeper_id):
        return None
    here = state.entities[keeper_id]["location_id"]
    stall = state.market_stalls.get(here)
    if stall is None or stall["keeper_id"] != keeper_id:
        return None
    if not _present(state.to_dict(), keeper_id, here):
        return None
    stock = state.resources.get(here, {}).get("food")
    if not _known(stock):
        return None
    for offer_id, offer in sorted(state.market_offers.items()):
        if (offer["status"] == "open" and offer["site_id"] == here
                and offer["stock_owner_id"] == here and offer["seller_id"] == keeper_id
                and offer["resource"] == "food" and offer["remaining"] > stock):
            return RetirementIntent(keeper_id, offer_id,
                                    f"on_site_stock={stock}; unfilled_quote={offer['remaining']}")
    return None


def choose_local_food_purchase(state: WorldState, buyer_id: str, *,
                               adaptive: bool = False) -> PurchaseIntent | None:
    """Buyer uses their *own* hunger and wallet plus physically visible quotes."""
    if type(adaptive) is not bool:
        raise ValueError("adaptive market mode must be boolean")
    if not _free(state, buyer_id):
        return None
    npc = state.npcs[buyer_id]
    last = npc["last_decision"]
    if (npc["needs"]["hunger"] < BUY_HUNGER_THRESHOLD
            or (last is not None and last["at"] == state.time)
            or state.time < npc["next_decision_at"]):
        return None
    here = state.entities[buyer_id]["location_id"]
    raw = state.to_dict()
    if not _present(raw, buyer_id, here):
        return None
    own_food = state.resources.get(buyer_id, {}).get("food")
    coins = state.resources.get(buyer_id, {}).get(MONEY)
    if not _known(own_food) or own_food != 0 or not _known(coins):
        return None
    candidates: list[tuple[int, str, PurchaseIntent]] = []
    # At extreme hunger an NPC accepts a higher posted price, never credit.
    max_price = 4 if npc["needs"]["hunger"] >= 95 else (
        3 if npc["needs"]["hunger"] >= 80 else 2)
    for offer_id, offer in sorted(state.market_offers.items()):
        if (offer["status"] != "open" or offer["site_id"] != here
                or offer["resource"] != "food"
                or offer["payment_resource"] != MONEY
                or offer["seller_id"] == buyer_id
                or offer["stock_owner_id"] == buyer_id
                or offer["remaining"] < 1
                or not _present(raw, offer["seller_id"], here)):
            continue
        price = offer["unit_price"]
        source = state.resources.get(offer["stock_owner_id"], {})
        stock = source.get("food")
        seller_coins = source.get(MONEY)
        if (not _known(stock) or stock < 1 or not _known(seller_coins)
                or not _known(price) or price < 1 or coins < price
                or seller_coins + price > MAX_AMOUNT
                or (adaptive and price > max_price)):
            continue
        ident = _event_id("trade", buyer_id, state.time)
        if ident in state.market_trades:
            return None
        choice = PurchaseIntent(buyer_id, offer_id, ident, price,
                                f"observed_local_quote={offer_id}; hunger="
                                f"{npc['needs']['hunger']}; own_copper={coins}; "
                                f"adaptive={adaptive}")
        if not adaptive:
            return choice
        candidates.append((price, offer_id, choice))
    return min(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None
