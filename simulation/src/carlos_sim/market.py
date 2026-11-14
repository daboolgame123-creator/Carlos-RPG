"""02-C: local quoted prices and atomic physical transfers, never free money.

Site goods remain site-owned, even when its registered NPC steward sells.
Personal goods remain NPC-owned. Currency is an *initialized* resource named
coin_copper; a different payment resource is a barter offer. No market AI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

MAX_AMOUNT = 2**31 - 1
MAX_QUANTITY = 1000
MAX_PRICE = 1000
MAX_ID = 64
MONEY = "coin_copper"
FORBIDDEN = {"labor_units", "investigation_attempts", "regrowth_reserve",
             "wild_food"}
OFFER_KEYS = {"seller_id", "stock_owner_id", "site_id", "resource",
              "quantity", "remaining", "payment_resource", "unit_price",
              "posted_at", "status", "closed_at"}
# Optional sale-backed real labor commission: only for time-zero explicitly
# signed on-site shop service. The trade receipt itself is the proof of work,
# never a fictional periodic job, debt or transfer from a courier's bag.
_KEEPER_COMMISSION_RECEIPT_KEYS = {"keeper_commission_coin", "keeper_coin_before",
                                   "keeper_coin_after", "site_coin_after_commission"}
TRADE_KEYS = {"offer_id", "buyer_id", "seller_id", "stock_owner_id", "site_id",
              "resource", "payment_resource", "unit_price", "quantity",
              "total_paid", "executed_at", "goods_source_before",
              "goods_source_after", "goods_target_before", "goods_target_after",
              "pay_source_before", "pay_source_after", "pay_target_before",
              "pay_target_after"}


def _id(x: Any) -> bool:
    return (isinstance(x, str) and 0 < len(x) <= MAX_ID and x.isascii()
            and all(c.isalnum() or c in "_-." for c in x))


def _balance(x: Any) -> bool:
    return type(x) is int and 0 <= x <= MAX_AMOUNT


def _positive(x: Any, limit: int) -> bool:
    return type(x) is int and 1 <= x <= limit


def _present(state: dict[str, Any], npc_id: str, site: str) -> bool:
    if (npc_id not in state["npcs"] or
            state["entities"][npc_id]["location_id"] != site):
        return False
    from .movement import _in_transit
    if _in_transit(state, npc_id):
        return False
    # Producing or executing a physical task means the NPC cannot haggle.
    from .production import is_producing
    return (not is_producing(state, npc_id) and
            not any(a["npc_id"] == npc_id and a["status"] == "running"
                    for a in state["actions"].values()))


def _buyer_present(state: dict[str, Any], buyer: str, site: str) -> bool:
    """Physical, available buyer; NPC behavior and human commands stay separate.

    A player has no NPC profile or implicit market authority. This helper
    validates only event-layer co-presence; PlayerGateway separately binds
    the real human identity to the trusted command.
    """
    if buyer in state["npcs"]:
        return _present(state, buyer, site)
    person = state["entities"].get(buyer)
    if person is None or person["controller"] != "player":
        return False
    from .movement import _in_transit
    return person["location_id"] == site and not _in_transit(state, buyer)


def _owner_controls(state: dict[str, Any], seller: str, owner: str,
                    site: str) -> bool:
    if owner == seller:
        return True
    stall = state["market_stalls"].get(site)
    return owner == site and stall is not None and stall["keeper_id"] == seller


def configure_market_stall(state: dict[str, Any], event: DomainEvent, *,
                           bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) not in ({"site_id", "keeper_id"},
                              {"site_id", "keeper_id", "keeper_commission_coin"})
            or ("keeper_commission_coin" in p
                and (type(p["keeper_commission_coin"]) is not int
                     or p["keeper_commission_coin"] != 1))):
        raise ValueError("market steward requires trusted time-zero bootstrap")
    site, keeper = p["site_id"], p["keeper_id"]
    if (not _id(site) or site not in state["locations"] or site in state["market_stalls"]
            or not _id(keeper) or not _present(state, keeper, site)):
        raise ValueError("market stall must have a real local NPC steward")
    if "keeper_commission_coin" in p:
        # A worker must have a real personal receiving account at signing,
        # and the employer must have a known treasury; unknown is not zero.
        if (not _balance(state["resources"].get(keeper, {}).get(MONEY))
                or not _balance(state["resources"].get(site, {}).get(MONEY))):
            raise ValueError("signed sale commission requires known employer/worker copper")
    state["market_stalls"][site] = dict(p)
    state["market_stalls"][site].pop("site_id")


def post_offer(state: dict[str, Any], event: DomainEvent, *,
               market_authorized: bool) -> None:
    p = event.data
    if (not market_authorized or set(p) != {"id", "seller_id", "stock_owner_id",
            "site_id", "resource", "quantity", "payment_resource", "unit_price"}
            or not _id(p["id"]) or p["id"] in state["market_offers"]):
        raise ValueError("new market offer requires trusted market capability")
    seller, owner, site = p["seller_id"], p["stock_owner_id"], p["site_id"]
    item, pay = p["resource"], p["payment_resource"]
    if (not _id(seller) or not _id(owner) or not _id(site)
            or site not in state["locations"] or event.actor_id != seller
            or not _present(state, seller, site)
            or not _owner_controls(state, seller, owner, site)
            or not _id(item) or not _id(pay) or item == pay
            or item == MONEY or item in FORBIDDEN or pay in FORBIDDEN
            or not _positive(p["quantity"], MAX_QUANTITY)
            or not _positive(p["unit_price"], MAX_PRICE)
            or p["quantity"] * p["unit_price"] > MAX_AMOUNT):
        raise ValueError("invalid physical seller, owner, commodity or local price")
    # Workshop tools cannot be sold by a steward while connected production
    # rules use them; workers' personal tools are not made by this phase.
    if owner == site and any(rec["site_id"] == site and
                              rec["tool_resource"] == item
                              for rec in state["production_recipes"].values()):
        raise ValueError("workshop equipment is not an offered commodity")
    stock = state["resources"].get(owner, {}).get(item)
    if not _balance(stock) or stock < p["quantity"]:
        raise ValueError("seller has no known sufficient inventory")
    state["market_offers"][p["id"]] = {
        "seller_id": seller, "stock_owner_id": owner, "site_id": site,
        "resource": item, "quantity": p["quantity"],
        "remaining": p["quantity"], "payment_resource": pay,
        "unit_price": p["unit_price"], "posted_at": state["time"],
        "status": "open", "closed_at": None,
    }


def _ledger(state: dict[str, Any], owner: str, resource: str) -> int:
    result = state["resources"].get(owner, {}).get(resource)
    if not _balance(result):
        raise ValueError("market trade requires known, bounded owned balances")
    return result


def reserved_trade_units(circuits: Any, owner: str, resource: str) -> int:
    """Return the units held in custody rather than available for trade."""
    circuit = circuits.get(owner)
    cargo = circuit["carry"] if circuit is not None else None
    return int(cargo is not None and cargo["resource"] == resource)


def trade_receipt_allowed(circuits: Any, owner: str, resource: str) -> bool:
    """Courier water/grain/cash slots accept only supply consignments.

    Owned food may coexist with a food parcel. A market receipt must not
    create a personal balance in an exact-custody slot, even between loads.
    """
    return owner not in circuits or resource not in ("water", "grain", MONEY)


def execute_trade(state: dict[str, Any], event: DomainEvent, *,
                  market_authorized: bool) -> None:
    p = event.data
    if (not market_authorized or set(p) != {"id", "offer_id", "buyer_id",
                                           "quantity", "expected_unit_price"}
            or not _id(p["id"]) or p["id"] in state["market_trades"]
            or not _id(p["offer_id"])):
        raise ValueError("market exchange requires trusted capability and unique trade ID")
    offer = state["market_offers"].get(p["offer_id"])
    buyer = p["buyer_id"]
    if (offer is None or offer["status"] != "open"
            or not _id(buyer) or event.actor_id != buyer
            or buyer == offer["seller_id"] or buyer == offer["stock_owner_id"]
            or not _buyer_present(state, buyer, offer["site_id"])
            or not _present(state, offer["seller_id"], offer["site_id"])
            or not _positive(p["quantity"], MAX_QUANTITY)
            or p["quantity"] > offer["remaining"]
            or type(p["expected_unit_price"]) is not int
            or p["expected_unit_price"] != offer["unit_price"]):
        raise ValueError("market sale requires both present, an open quote and exact terms")
    owner = offer["stock_owner_id"]
    item, pay = offer["resource"], offer["payment_resource"]
    quantity, total = p["quantity"], p["quantity"] * offer["unit_price"]
    gb = _ledger(state, owner, item)
    gt = _ledger(state, buyer, item)
    pb = _ledger(state, buyer, pay)
    pt = _ledger(state, owner, pay)
    circuits = state["supply_circuits"]
    if (not trade_receipt_allowed(circuits, buyer, item)
            or not trade_receipt_allowed(circuits, owner, pay)):
        raise ValueError("market receipt conflicts with courier custody")
    # Retail labor is completed ONLY by a real paid, co-present sale of
    # institution-owned goods. A signed steward earns one existing copper
    # from actual sales proceeds; the employer retains any residual.
    # Barter, personal consignment and a one-copper sale are NOT an
    # authorization to drain a shop till or mint a commission.
    stall = state["market_stalls"].get(offer["site_id"], {})
    keeper = offer["seller_id"]
    commission = (1 if pay == MONEY and owner == offer["site_id"]
                  and stall.get("keeper_id") == keeper
                  and stall.get("keeper_commission_coin") == 1
                  and total >= 2 else 0)
    keeper_before = (_ledger(state, keeper, MONEY) if commission else None)
    if (gb - reserved_trade_units(circuits, owner, item) < quantity
            or pb - reserved_trade_units(circuits, buyer, pay) < total
            or gt + quantity > MAX_AMOUNT or pt + total > MAX_AMOUNT
            or (commission and (
                keeper_before + commission > MAX_AMOUNT
                or pt + total - reserved_trade_units(circuits, owner, MONEY)
                    < commission))):
        raise ValueError("insufficient market goods/coins or destination overflow")
    state["resources"][owner][item] = gb - quantity
    state["resources"][buyer][item] = gt + quantity
    state["resources"][buyer][pay] = pb - total
    state["resources"][owner][pay] = pt + total - commission
    if commission:
        state["resources"][keeper][MONEY] = keeper_before + commission
    offer["remaining"] -= quantity
    if offer["remaining"] == 0:
        offer["status"] = "filled"
        offer["closed_at"] = state["time"]
    state["market_trades"][p["id"]] = {
        "offer_id": p["offer_id"], "buyer_id": buyer,
        "seller_id": offer["seller_id"], "stock_owner_id": owner,
        "site_id": offer["site_id"], "resource": item,
        "payment_resource": pay, "unit_price": offer["unit_price"],
        "quantity": quantity, "total_paid": total,
        "executed_at": state["time"],
        "goods_source_before": gb, "goods_source_after": gb - quantity,
        "goods_target_before": gt, "goods_target_after": gt + quantity,
        "pay_source_before": pb, "pay_source_after": pb - total,
        "pay_target_before": pt, "pay_target_after": pt + total,
    }
    if commission:
        state["market_trades"][p["id"]].update({
            "keeper_commission_coin": commission,
            "keeper_coin_before": keeper_before,
            "keeper_coin_after": keeper_before + commission,
            "site_coin_after_commission": pt + total - commission,
        })


def close_offer(state: dict[str, Any], event: DomainEvent, *,
                market_authorized: bool) -> None:
    p = event.data
    if not market_authorized or set(p) != {"id"} or not _id(p["id"]):
        raise ValueError("market offer closure requires trusted seller")
    offer = state["market_offers"].get(p["id"])
    if (offer is None or offer["status"] != "open"
            or event.actor_id != offer["seller_id"]
            or not _present(state, offer["seller_id"], offer["site_id"])):
        raise ValueError("only the on-site seller can close an open listing")
    offer["status"] = "closed"
    offer["closed_at"] = state["time"]


def validate_market(state: dict[str, Any]) -> None:
    stalls, offers, trades = (state[k] for k in
                             ("market_stalls", "market_offers", "market_trades"))
    if not all(isinstance(x, dict) for x in (stalls, offers, trades)):
        raise ValueError("market ledgers must be mappings")
    for site, stall in stalls.items():
        if (not _id(site) or site not in state["locations"]
                or not isinstance(stall, dict)
                or set(stall) not in ({"keeper_id"},
                                     {"keeper_id", "keeper_commission_coin"})
                or not _id(stall["keeper_id"]) or stall["keeper_id"] not in state["npcs"]
                or ("keeper_commission_coin" in stall and
                    stall["keeper_commission_coin"] != 1)):
            raise ValueError("invalid registered market stall")
    for ident, o in offers.items():
        if (not _id(ident) or not isinstance(o, dict) or set(o) != OFFER_KEYS
                or not _id(o["site_id"]) or o["site_id"] not in state["locations"]
                or not _id(o["seller_id"]) or o["seller_id"] not in state["npcs"]
                or not _id(o["stock_owner_id"]) or not _owner_controls(
                    state, o["seller_id"], o["stock_owner_id"], o["site_id"])
                or not _id(o["resource"]) or not _id(o["payment_resource"])
                or o["resource"] == o["payment_resource"] or o["resource"] == MONEY
                or o["resource"] in FORBIDDEN or o["payment_resource"] in FORBIDDEN
                or not _positive(o["quantity"], MAX_QUANTITY)
                or type(o["remaining"]) is not int
                or not 0 <= o["remaining"] <= o["quantity"]
                or not _positive(o["unit_price"], MAX_PRICE)
                or not _balance(o["quantity"] * o["unit_price"])
                or type(o["posted_at"]) is not int or not 0 <= o["posted_at"] <= state["time"]
                or o["status"] not in {"open", "closed", "filled"}):
            raise ValueError("invalid market offer record")
        if (o["status"] == "open" and
                (o["remaining"] == 0 or o["closed_at"] is not None)):
            raise ValueError("open offer has no remaining stock")
        if o["status"] == "filled" and o["remaining"] != 0:
            raise ValueError("filled offer has outstanding stock")
        if o["status"] != "open" and (type(o["closed_at"]) is not int
                or not o["posted_at"] <= o["closed_at"] <= state["time"]):
            raise ValueError("market closure has no valid timestamp")
    sold: dict[str, int] = {}
    for ident, t in trades.items():
        if (not _id(ident) or not isinstance(t, dict)
                or set(t) not in (TRADE_KEYS,
                                  TRADE_KEYS | _KEEPER_COMMISSION_RECEIPT_KEYS)
                or t["offer_id"] not in offers):
            raise ValueError("invalid market trade record")
        o = offers[t["offer_id"]]
        if (t["buyer_id"] not in state["npcs"]
                and (t["buyer_id"] not in state["entities"]
                     or state["entities"][t["buyer_id"]]["controller"] != "player")
                or t["buyer_id"] == o["seller_id"] or t["buyer_id"] == o["stock_owner_id"]
                or any(t[k] != o[k] for k in (
                    "seller_id", "stock_owner_id", "site_id", "resource",
                    "payment_resource", "unit_price"))
                or not _positive(t["quantity"], MAX_QUANTITY)
                or t["total_paid"] != t["quantity"] * o["unit_price"]
                or type(t["executed_at"]) is not int
                or not o["posted_at"] <= t["executed_at"] <= state["time"]):
            raise ValueError("invalid market trade identity, price or provenance")
        numbers = [t[k] for k in TRADE_KEYS if k.endswith("_before") or k.endswith("_after")]
        if not all(_balance(n) for n in numbers):
            raise ValueError("market trade balances must be known and bounded")
        if (t["goods_source_before"] - t["goods_source_after"] != t["quantity"]
                or t["goods_target_after"] - t["goods_target_before"] != t["quantity"]
                or t["pay_source_before"] - t["pay_source_after"] != t["total_paid"]
                or t["pay_target_after"] - t["pay_target_before"] != t["total_paid"]):
            raise ValueError("trade must conserve goods and currency without invention")
        has_commission = "keeper_commission_coin" in t
        if has_commission:
            stall = stalls.get(t["site_id"], {})
            wage = t["keeper_commission_coin"]
            if (type(wage) is not int or wage != 1
                    or stall.get("keeper_commission_coin") != wage
                    or stall.get("keeper_id") != t["seller_id"]
                    or t["stock_owner_id"] != t["site_id"]
                    or t["payment_resource"] != MONEY or t["total_paid"] < 2
                    or not all(_balance(t[k]) for k in
                               _KEEPER_COMMISSION_RECEIPT_KEYS)
                    or t["keeper_coin_after"] - t["keeper_coin_before"] != wage
                    or t["site_coin_after_commission"] !=
                        t["pay_target_after"] - wage):
                raise ValueError("signed sale commission must be actual funded work")
        sold[t["offer_id"]] = sold.get(t["offer_id"], 0) + t["quantity"]
    for ident, o in offers.items():
        if o["quantity"] - o["remaining"] != sold.get(ident, 0):
            raise ValueError("offer remaining is inconsistent with its actual sales")


@dataclass(frozen=True)
class MarketResult:
    event_id: str
    state: WorldState


class NPCMarketService:
    """Trusted-local explicit seller/buyer API. Not a network authorization layer."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("market and clock must use the same store")
        self.store, self.clock = store, clock

    def _append(self, world_id: str, event_id: str, expected_revision: int,
                kind: str, actor: str, data: dict[str, Any]) -> MarketResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if type(expected_revision) is not int or state.revision != expected_revision:
            raise RevisionConflict("stale market command")
        event = DomainEvent(kind, actor, "explicit local market agreement",
                            state.time, data)
        result = self.store.append(
            world_id, "market:" + event_id, expected_revision, [event],
            market_authorized=True)
        return MarketResult(event_id, result)

    def post(self, world_id: str, seller_id: str, owner_id: str, site_id: str,
             offer_id: str, resource: str, quantity: int,
             payment_resource: str, unit_price: int, *,
             expected_revision: int) -> MarketResult:
        return self._append(world_id, "offer:" + offer_id, expected_revision,
                            "MarketOfferPosted", seller_id,
                            {"id": offer_id, "seller_id": seller_id,
                             "stock_owner_id": owner_id, "site_id": site_id,
                             "resource": resource, "quantity": quantity,
                             "payment_resource": payment_resource,
                             "unit_price": unit_price})

    def buy(self, world_id: str, buyer_id: str, trade_id: str, offer_id: str,
            quantity: int, expected_unit_price: int, *,
            expected_revision: int) -> MarketResult:
        # Preserve the legacy NPC-only command boundary. Human purchases
        # must come through the player-bound PlayerGateway, never by passing
        # an arbitrary human ID to the NPC market service.
        self.clock._require_session(world_id)
        if buyer_id not in self.store.load(world_id).npcs:
            raise PermissionError("NPCMarketService.buy requires a real NPC buyer")
        return self._append(world_id, "sale:" + trade_id, expected_revision,
                            "MarketTradeExecuted", buyer_id,
                            {"id": trade_id, "buyer_id": buyer_id,
                             "offer_id": offer_id, "quantity": quantity,
                             "expected_unit_price": expected_unit_price})

    def close(self, world_id: str, seller_id: str, offer_id: str, *,
              expected_revision: int) -> MarketResult:
        return self._append(world_id, "close:" + offer_id, expected_revision,
                            "MarketOfferClosed", seller_id, {"id": offer_id})

    def local_quotes(self, world_id: str, npc_id: str) -> tuple[dict[str, Any], ...]:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if npc_id not in state.npcs:
            raise PermissionError("local NPC identity required")
        site = state.entities[npc_id]["location_id"]
        raw = state.to_dict()
        if not _present(raw, npc_id, site):
            raise PermissionError("travelling or occupied NPC cannot inspect local quotes")
        result = []
        for ident, o in sorted(raw["market_offers"].items()):
            if o["site_id"] != site or o["status"] != "open":
                continue
            stock = raw["resources"].get(o["stock_owner_id"], {}).get(o["resource"])
            quantity = min(o["remaining"], stock) if _balance(stock) else 0
            if quantity > 0:
                result.append({"offer_id": ident, "resource": o["resource"],
                               "available": quantity, "payment_resource": o["payment_resource"],
                               "unit_price": o["unit_price"],
                               "site_id": site})
        return tuple(result)
