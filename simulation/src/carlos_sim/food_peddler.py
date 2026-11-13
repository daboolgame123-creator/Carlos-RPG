"""PLAY48: a genuine, self-funded NPC carries bought fish/game to market.

The existing market and movement reducers remain the only authorities:
- A real on-site quote from a true hunter/fisher keeper; customer-owned
  coin transfers to the seller on an authenticated MarketTradeExecuted.
- The trader has one personally owned food unit in their inventory while
  walking on ONLY personally surveyed roads, never remote inspection.
- At the physical market, a personal offer sells the same carried unit to
  a local buyer for real copper. No food teleports to the market's site stock.
- A quotation is withdrawn *before* a needy trader consumes their own
  unsold food. Buyers and workers retain the normal safety/needs guards.

This is opt-in. No promise of profit, buyers, long-run prey renewal, or
full village livelihood from one self-funded trader.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .domain import WorldState
from .economic_autonomy import _free
from .market import MONEY, MAX_AMOUNT, reserved_trade_units, _present
from .navigation import shortest_known_route
from .npc import _injury_rest_decision
from .routines import is_work_shift

TRADER = "repairman"
SOURCE = "hunting_woods"
DESTINATION = "market"
SOURCE_PRICE = 1
MARKET_PRICE = 2


@dataclass(frozen=True)
class Purchase:
    offer_id: str
    trade_id: str
    unit_price: int


@dataclass(frozen=True)
class Sale:
    offer_id: str
    quantity: int


@dataclass(frozen=True)
class Withdrawal:
    offer_id: str


@dataclass(frozen=True)
class Walk:
    route_id: str
    destination: str


def _id(prefix: str, ident: str, tick: int) -> str:
    raw = f"pdd-{prefix}-{ident}-{tick}"
    if len(raw) <= 64:
        return raw
    return "pdd-" + sha256(raw.encode()).hexdigest()[:52]


def _present_free(state: WorldState, who: str) -> bool:
    if (who != TRADER or who not in state.npcs
            or state.npcs[who]["role"] != "food_peddler"
            or not _free(state, who)):
        return False
    n = state.npcs[who]["needs"]
    return (
        n["hunger"] < 90 and n["fatigue"] < 70 and n["safety"] < 75
        and _injury_rest_decision(state.injuries, who) is None
        and _present(state.to_dict(), who, state.entities[who]["location_id"])
    )


def _balances(state: WorldState) -> tuple[int | None, int | None]:
    bag = state.resources.get(TRADER, {})
    food, copper = bag.get("food"), bag.get(MONEY)
    if (type(food) is not int or not 0 <= food <= MAX_AMOUNT
            or type(copper) is not int or not 0 <= copper <= MAX_AMOUNT):
        return None, None
    return food, copper


def choose_purchase(state: WorldState) -> Purchase | None:
    """Inspect ONLY a personally reached local hunting stall and real quote."""
    if not _present_free(state, TRADER):
        return None
    if state.entities[TRADER]["location_id"] != SOURCE:
        return None
    food, coins = _balances(state)
    if food != 0 or coins is None or coins < SOURCE_PRICE:
        return None
    source = state.resources.get(SOURCE, {})
    available = source.get("food")
    if type(available) is not int or available < 1:
        return None
    raw = state.to_dict()
    for offer_id, o in sorted(state.market_offers.items()):
        if (o["status"] != "open" or o["site_id"] != SOURCE
                or o["resource"] != "food"
                or o["payment_resource"] != MONEY
                or o["stock_owner_id"] != SOURCE
                or o["seller_id"] != "omar"
                or o["remaining"] < 1
                or o["unit_price"] != SOURCE_PRICE
                or coins - reserved_trade_units(
                    state.supply_circuits, TRADER, MONEY) < SOURCE_PRICE
                or not _present(raw, o["seller_id"], SOURCE)
                or available - reserved_trade_units(
                    state.supply_circuits, SOURCE, "food") < 1):
            continue
        return Purchase(offer_id, _id("buy", TRADER, state.time), SOURCE_PRICE)
    return None


def choose_offer(state: WorldState) -> Sale | None:
    """Only personally owned carried goods offered after actual arrival."""
    if not _present_free(state, TRADER):
        return None
    if state.entities[TRADER]["location_id"] != DESTINATION:
        return None
    food, _ = _balances(state)
    if (food is None or food < 1
            or state.npcs[TRADER]["needs"]["hunger"] >= 70
            or any(o["status"] == "open"
                   and o["stock_owner_id"] == TRADER
                   and o["resource"] == "food"
                   for o in state.market_offers.values())):
        return None
    committed = reserved_trade_units(state.supply_circuits, TRADER, "food")
    if food - committed < 1:
        return None
    return Sale(_id("offer", TRADER, state.time), 1)


def choose_withdrawal(state: WorldState) -> Withdrawal | None:
    """A starving private trader withdraws an unsold quote before eating."""
    if not _present(state.to_dict(), TRADER, DESTINATION):
        return None
    if TRADER not in state.npcs or state.npcs[TRADER]["role"] != "food_peddler":
        return None
    food, _ = _balances(state)
    for offer_id, o in sorted(state.market_offers.items()):
        if (o["status"] == "open" and o["seller_id"] == TRADER
                and o["stock_owner_id"] == TRADER
                and o["site_id"] == DESTINATION and o["resource"] == "food"
                and (food is None or food < o["remaining"]
                     or state.npcs[TRADER]["needs"]["hunger"] >= 70)):
            return Withdrawal(offer_id)
    return None


def choose_walk(state: WorldState) -> Walk | None:
    """At work, explore the real known woods; return carrying actual food."""
    profile = state.npc_routines.get(TRADER)
    if (not _present_free(state, TRADER) or profile is None
            or not is_work_shift(profile, state.time)):
        return None
    food, coins = _balances(state)
    if food is None or coins is None:
        return None
    here = state.entities[TRADER]["location_id"]
    if any(o["status"] == "open" and o["stock_owner_id"] == TRADER
           for o in state.market_offers.values()):
        return None
    if here == DESTINATION and food == 0 and coins >= SOURCE_PRICE:
        destination = SOURCE  # Known local road destination, NOT a stock query.
    elif here == SOURCE and food > 0:
        destination = DESTINATION
    else:
        return None
    path = shortest_known_route(state, TRADER, destination)
    if not path:
        return None
    return Walk(path[0], destination)
