"""PLAY48 optional community rations, truly drawn from market-owned unquoted bread.

A trusted time-zero market owner authorizes at most TWO physical loaves per
simulated day for co-present, penniless, hungry residents from only leftover,
UNQUOTED stock. This contract does not reserve food or alter regular prices.
The participating
keeper must be present; ordinary customer offers, cargo and prior wages remain
protected. Every transfer is recorded as an authoritative event. No money,
food, courier service or travel is invented.
"""
from __future__ import annotations

from .domain import DomainEvent, WorldState
from .food_for_work import _available_site_food, _worker_present_and_free
from .market import _present

DAY = 24 * 3600
DAILY_LIMIT = 2
HUNGER_THRESHOLD = 75


def sign_market_relief(state: dict, event: DomainEvent, *, bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"site_id", "keeper_id", "daily_limit"}
            or p["site_id"] != "market" or p["daily_limit"] != DAILY_LIMIT):
        raise ValueError("relief requires explicitly signed time-zero market terms")
    stall = state["market_stalls"].get("market")
    keeper = p["keeper_id"]
    if (stall is None or stall["keeper_id"] != keeper
            or "community_food" in stall
            or state["npcs"].get(keeper, {}).get("role") != "merchant"
            or not _present(state, keeper, "market")
            or type(state["resources"].get("market", {}).get("food")) is not int):
        raise ValueError("relief requires a present delegated market owner and known food")
    stall["community_food"] = {"daily_limit": DAILY_LIMIT, "payments": []}


def _eligible(state: dict, recipient: str, *, require_unquoted: bool = True) -> bool:
    stall = state["market_stalls"].get("market", {})
    contract = stall.get("community_food")
    npc = state["npcs"].get(recipient)
    if contract is None or npc is None:
        return False
    keeper = stall["keeper_id"]
    if not _present(state, keeper, "market"):
        return False
    if (not _worker_present_and_free(state, recipient, "market")
            or not _present(state, recipient, "market")
            or npc["needs"]["hunger"] < HUNGER_THRESHOLD):
        return False
    goods = state["resources"].get(recipient, {})
    if (type(goods.get("food")) is not int or goods["food"] != 0
            or type(goods.get("coin_copper")) is not int
            or goods["coin_copper"] != 0):
        return False
    used_today = sum(p["paid_at"] // DAY == state["time"] // DAY
                     for p in contract["payments"])
    if used_today >= DAILY_LIMIT:
        return False
    if any(p["recipient_id"] == recipient
           and state["time"] - p["paid_at"] < DAY
           for p in contract["payments"]):
        return False
    # An existing quote is a claim on real owner stock; NEVER take from it.
    return not require_unquoted or _available_site_food(state, "market") >= 1



def signed_local_relief_quote_capacity(state: WorldState, *,
                                       unit_price: int = 2) -> int:
    """Owner's still-unused daily food aid when there is no solvent local buyer.

    Checks only the market's own contract, physical NPC positions, its own
    inventory, and its on-site asking price. Does not invent supplies, debt,
    promises or remote price knowledge. Never alters a pre-existing offer.
    """
    raw = state.to_dict()
    stall = raw["market_stalls"].get("market", {})
    contract = stall.get("community_food")
    if contract is None:
        return 0
    keeper = stall["keeper_id"]
    if not _present(raw, keeper, "market"):
        return 0
    # Do not withdraw an unsold retail quote while a real paying customer
    # is physically present, including human-controlled shoppers.
    for who, entity in raw["entities"].items():
        if who == keeper or entity["location_id"] != "market":
            continue
        goods = raw["resources"].get(who, {})
        is_present = (_present(raw, who, "market") if who in raw["npcs"]
                      else entity["controller"] == "player")
        if (is_present and type(goods.get("coin_copper")) is int
                and goods["coin_copper"] >= unit_price):
            return 0
    remaining = DAILY_LIMIT - sum(
        p["paid_at"] // DAY == raw["time"] // DAY
        for p in contract["payments"]
    )
    if remaining <= 0:
        return 0
    eligible = sum(_eligible(raw, who, require_unquoted=False)
                   for who in raw["npcs"])
    return min(remaining, eligible)


def choose_market_relief_quote_retirement(state: WorldState) -> str | None:
    """Local owner may withdraw an OLD unsold quote to fulfill signed aid.

    Close via the existing seller-authorized MarketOfferClosed event, then
    market re-listing preserves the owner's still-needed physical rations.
    No promised or already sold loaf is changed, and no price is rewritten.
    """
    stall = state.market_stalls.get("market", {})
    if "community_food" not in stall:
        return None
    keeper = stall["keeper_id"]
    for ident, offer in sorted(state.market_offers.items()):
        if (offer["status"] != "open" or offer["site_id"] != "market"
                or offer["stock_owner_id"] != "market"
                or offer["seller_id"] != keeper or offer["resource"] != "food"
                or state.time - offer["posted_at"] < 6 * 3600):
            continue
        budget = signed_local_relief_quote_capacity(
            state, unit_price=offer["unit_price"])
        if (budget > _available_site_food(state, "market")
                and state.resources["market"]["food"] >= budget):
            return ident
    return None


def choose_market_ration(state: WorldState) -> str | None:
    """One locally witnessed need, highest actual hunger first; no remote oracle."""
    if "community_food" not in state.market_stalls.get("market", {}):
        return None
    raw = state.to_dict()
    for who in sorted(raw["npcs"], key=lambda w: (-raw["npcs"][w]["needs"]["hunger"], w)):
        if _eligible(raw, who):
            return who
    return None


def pay_market_ration(state: dict, event: DomainEvent, *,
                      market_authorized: bool) -> None:
    p = event.data
    if (not market_authorized or event.actor_id is not None
            or set(p) != {"site_id", "recipient_id", "amount"}
            or p["site_id"] != "market" or p["amount"] != 1
            or type(p["recipient_id"]) is not str
            or not _eligible(state, p["recipient_id"])):
        raise ValueError("community ration requires signed, local, unfunded need")
    recipient = p["recipient_id"]
    source = state["resources"]["market"]["food"]
    owned = state["resources"][recipient]["food"]
    state["resources"]["market"]["food"] = source - 1
    state["resources"][recipient]["food"] = owned + 1
    state["market_stalls"]["market"]["community_food"]["payments"].append({
        "recipient_id": recipient, "paid_at": state["time"],
        "source_before": source, "source_after": source - 1,
        "recipient_before": owned, "recipient_after": owned + 1,
    })


def validate_market_relief(state: dict, stall: dict) -> None:
    contract = stall.get("community_food")
    if contract is None:
        return
    if (type(contract) is not dict or set(contract) != {"daily_limit", "payments"}
            or type(contract["daily_limit"]) is not int
            or contract["daily_limit"] != DAILY_LIMIT
            or type(contract["payments"]) is not list):
        raise ValueError("invalid owner-signed food relief contract")
    per_day = {}
    last_by_recipient = {}
    last_paid_at = -1
    for p in contract["payments"]:
        if (type(p) is not dict or set(p) != {
                "recipient_id", "paid_at", "source_before", "source_after",
                "recipient_before", "recipient_after"}
                or p["recipient_id"] not in state["npcs"]
                or type(p["paid_at"]) is not int
                or not last_paid_at <= p["paid_at"] <= state["time"]
                or any(type(p[k]) is not int or not 0 <= p[k] <= 2**31 - 1
                       for k in ("source_before", "source_after",
                                 "recipient_before", "recipient_after"))
                or p["source_before"] - p["source_after"] != 1
                or p["recipient_after"] - p["recipient_before"] != 1):
            raise ValueError("community food receipt has no conserved actual loaf")
        if (p["recipient_id"] in last_by_recipient
                and p["paid_at"] - last_by_recipient[p["recipient_id"]] < DAY):
            raise ValueError("recipient cannot claim multiple daily rations")
        last_by_recipient[p["recipient_id"]] = p["paid_at"]
        day = p["paid_at"] // DAY
        per_day[day] = per_day.get(day, 0) + 1
        if per_day[day] > DAILY_LIMIT:
            raise ValueError("community rations exceed owner-authorized daily limit")
        last_paid_at = p["paid_at"]
