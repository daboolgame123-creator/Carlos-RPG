"""PLAY48: real local merchant food wage funded from unquoted owner stock.

A real market keeper signs at genesis: two completed on-site sales of
owner-held FOOD earn exactly one loaf *after* the shop physically has an
unpromised surplus. The shop never diverts quoted customer goods, courier
cargo, physical coin or the protected operating food unit. No salary until
both the service and the physical local employer stock really exist.
"""
from __future__ import annotations
from bisect import bisect_right
from typing import Any
from .domain import DomainEvent, WorldState
from .market import _id, _present, MAX_AMOUNT
from .food_for_work import _available_site_food

PAYMENT_SALES = 2
WAGE_FOOD = 1
# Require one genuinely unquoted shop loaf to remain after the paid wage.
UNPROMISED_OPERATING_FOOD = 1


def sign_steward_food_contract(state: dict[str, Any], event: DomainEvent, *,
                                bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"site_id", "keeper_id", "sales_per_wage"}
            or type(p["sales_per_wage"]) is not int
            or p["sales_per_wage"] != PAYMENT_SALES):
        raise ValueError("two actual sales per food wage require trusted genesis agreement")
    site, who = p["site_id"], p["keeper_id"]
    stall = state["market_stalls"].get(site)
    if (not _id(site) or not _id(who) or stall is None
            or set(stall) != {"keeper_id"} or stall["keeper_id"] != who
            or state["npcs"].get(who, {}).get("role") != "merchant"
            or not _present(state, who, site)
            or type(state["resources"].get(site, {}).get("food")) is not int
            or type(state["resources"].get(who, {}).get("food")) is not int):
        raise ValueError("contract needs an actual local registered steward and food ledgers")
    stall["food_wage_sales_required"] = PAYMENT_SALES


def _earned_sales(state: WorldState | dict[str, Any], site: str):
    stalls = state.market_stalls if isinstance(state, WorldState) else state["market_stalls"]
    trades = state.market_trades if isinstance(state, WorldState) else state["market_trades"]
    stall = stalls.get(site)
    if stall is None or stall.get("food_wage_sales_required") != PAYMENT_SALES:
        return [], []
    who = stall["keeper_id"]
    eligible = sorted(
        ((ident, t) for ident, t in trades.items()
         if t["site_id"] == site and t["stock_owner_id"] == site
         and t["seller_id"] == who and t["resource"] == "food"
         and t["payment_resource"] == "coin_copper" and t["total_paid"] >= 1),
        key=lambda p: (p[1]["executed_at"], p[0]),
    )
    paid = [(ident, t) for ident, t in eligible if "steward_food_wage" in t]
    return eligible, paid


def choose_steward_food_wage(state: WorldState, site: str) -> str | None:
    stall = state.market_stalls.get(site)
    if stall is None or stall.get("food_wage_sales_required") != PAYMENT_SALES:
        return None
    who = stall["keeper_id"]
    if (state.npcs[who]["role"] != "merchant"
            or not _present(state.to_dict(), who, site)):
        return None
    eligible, paid = _earned_sales(state, site)
    if len(eligible) < PAYMENT_SALES * (len(paid) + 1):
        return None
    if _available_site_food(state, site) < WAGE_FOOD + UNPROMISED_OPERATING_FOOD:
        return None
    worker_food = state.resources.get(who, {}).get("food")
    if type(worker_food) is not int or worker_food >= MAX_AMOUNT:
        return None
    return next((ident for ident, trade in reversed(eligible)
                 if "steward_food_wage" not in trade), None)


def pay_steward_food_wage(state: dict[str, Any], event: DomainEvent, *,
                          market_authorized: bool) -> None:
    p = event.data
    if (not market_authorized or event.actor_id is not None
            or set(p) != {"site_id", "trade_id", "amount"}
            or not _id(p["site_id"]) or not _id(p["trade_id"])
            or type(p["amount"]) is not int or p["amount"] != WAGE_FOOD):
        raise ValueError("steward wage requires authenticated single physical loaf")
    site = p["site_id"]
    stall = state["market_stalls"].get(site)
    if stall is None or stall.get("food_wage_sales_required") != PAYMENT_SALES:
        raise ValueError("shop worker has no signed food wage contract")
    who = stall["keeper_id"]
    if state["npcs"].get(who, {}).get("role") != "merchant" or not _present(state, who, site):
        raise ValueError("steward must be physically available where food is owned")
    eligible, paid = _earned_sales(state, site)
    if (len(eligible) < PAYMENT_SALES * (len(paid) + 1)
            or not any(ident == p["trade_id"] and "steward_food_wage" not in trade
                       for ident, trade in eligible)
            or _available_site_food(state, site) < WAGE_FOOD + UNPROMISED_OPERATING_FOOD):
        raise ValueError("unearned sale wage or customer/courier reserve is protected")
    employer = state["resources"].get(site, {})
    worker = state["resources"].get(who, {})
    source, destination = employer.get("food"), worker.get("food")
    if (type(source) is not int or source < 2 or type(destination) is not int
            or destination < 0 or destination >= MAX_AMOUNT):
        raise ValueError("merchant payroll requires source stock and bounded worker inventory")
    employer["food"], worker["food"] = source - 1, destination + 1
    state["market_trades"][p["trade_id"]]["steward_food_wage"] = {
        "site_id": site, "worker_id": who, "amount": 1,
        "paid_at": state["time"],
        "site_before": source, "site_after": source - 1,
        "worker_before": destination, "worker_after": destination + 1,
    }


def _validate_steward_food_wage_receipt_shape(
        state: dict[str, Any], trade: dict[str, Any]) -> tuple[str, int]:
    site, who = trade["site_id"], trade["seller_id"]
    stall = state["market_stalls"].get(site)
    wage = trade["steward_food_wage"]
    if (type(wage) is not dict
            or set(wage) != {"site_id", "worker_id", "amount", "paid_at",
                            "site_before", "site_after", "worker_before", "worker_after"}
            or stall is None or stall.get("keeper_id") != who
            or stall.get("food_wage_sales_required") != PAYMENT_SALES
            or state["npcs"][who]["role"] != "merchant"
            or trade["stock_owner_id"] != site
            or trade["resource"] != "food" or trade["payment_resource"] != "coin_copper"
            or type(wage["paid_at"]) is not int
            or not trade["executed_at"] <= wage["paid_at"] <= state["time"]
            or wage["site_id"] != site or wage["worker_id"] != who
            or type(wage["amount"]) is not int or wage["amount"] != 1
            or any(type(wage[k]) is not int or wage[k] < 0 or wage[k] > MAX_AMOUNT
                   for k in ("site_before", "site_after", "worker_before", "worker_after"))
            or wage["site_before"] - wage["site_after"] != 1
            or wage["worker_after"] - wage["worker_before"] != 1):
        raise ValueError("steward wage must be a contracted, conserved local food receipt")

    return site, wage["paid_at"]


def validate_steward_food_wage_receipt(state: dict[str, Any],
                                        trade: dict[str, Any]) -> None:
    site, at = _validate_steward_food_wage_receipt_shape(state, trade)
    eligible, paid = _earned_sales(state, site)
    # Every persisted payment must be backed by two separately completed
    # authentic owner-food sales not later than that receipt's payment time.
    # A paid receipt can never backfill with future sales.
    paid_through = sum(1 for _, t in paid
                       if t["steward_food_wage"]["paid_at"] <= at)
    sold_through = sum(1 for _, t in eligible if t["executed_at"] <= at)
    if sold_through < PAYMENT_SALES * paid_through:
        raise ValueError("steward payroll exceeds completed sale service")


def validate_steward_food_wages(
        state: dict[str, Any], eligible_sales_by_site: dict[str, list[int]]) -> None:
    """Validate all receipts using one timestamp index per contracted site.

    ``eligible_sales_by_site`` is collected while ``validate_market`` already
    walks its fully checked trade records. This preserves every per-receipt
    funding check while avoiding a full market-history scan for each receipt.
    """
    trades = state.market_trades if isinstance(state, WorldState) else state["market_trades"]
    paid_by_site: dict[str, list[int]] = {}
    for trade in trades.values():
        if "steward_food_wage" not in trade:
            continue
        site, at = _validate_steward_food_wage_receipt_shape(state, trade)
        paid_by_site.setdefault(site, []).append(at)

    for site, paid_times in paid_by_site.items():
        sale_times = sorted(eligible_sales_by_site.get(site, ()))
        paid_times.sort()
        for at in paid_times:
            sold_through = bisect_right(sale_times, at)
            paid_through = bisect_right(paid_times, at)
            if sold_through < PAYMENT_SALES * paid_through:
                raise ValueError("steward payroll exceeds completed sale service")


def choose_steward_earned_wage_quote_retirement(
        state: WorldState, site: str = "market") -> str | None:
    """Owner may withdraw an aged, UNSOLD quote to honour already earned wages.

    A quote is not a completed sale. Close it by the existing on-site seller
    event, then the standard signed food-payroll reducer transfers the real
    loaf. Refuse active solvent buyers, unrelated owners/cargo and all
    unsupported sites. Protect the owner's signed relief budget first.
    """
    stall = state.market_stalls.get(site)
    if (site != "market" or stall is None
            or stall.get("food_wage_sales_required") != PAYMENT_SALES):
        return None
    keeper = stall["keeper_id"]
    raw = state.to_dict()
    if (state.npcs.get(keeper, {}).get("role") != "merchant"
            or not _present(raw, keeper, site)):
        return None
    earned, paid = _earned_sales(state, site)
    if len(earned) < PAYMENT_SALES * (len(paid) + 1):
        return None
    if type(state.resources.get(keeper, {}).get("food")) is not int:
        return None
    if state.resources[keeper]["food"] >= MAX_AMOUNT:
        return None

    for ident, offer in sorted(state.market_offers.items()):
        if (offer["status"] != "open" or offer["site_id"] != site
                or offer["stock_owner_id"] != site or offer["seller_id"] != keeper
                or offer["resource"] != "food"
                or offer["payment_resource"] != "coin_copper"
                or type(offer["remaining"]) is not int or offer["remaining"] < 1
                or state.time - offer["posted_at"] < 6 * 3600):
            continue
        # Never retire a listed customer loaf when a real solvent NPC or
        # human buyer is standing here; do not rely on a remote wallet oracle.
        from .market import _buyer_present
        if any(
            who != keeper and entity["location_id"] == site
            and _buyer_present(raw, who, site)
            and type(raw["resources"].get(who, {}).get("coin_copper")) is int
            and raw["resources"][who]["coin_copper"] >= offer["unit_price"]
            for who, entity in raw["entities"].items()
        ):
            continue
        # Owner-signed hunger relief retains first call on its remaining
        # daily allocation. Wage withdrawal cannot cancel that promise.
        from .community_food import signed_local_relief_quote_capacity
        if signed_local_relief_quote_capacity(
                state, unit_price=offer["unit_price"]) > 0:
            continue
        # Check physical unpromised inventory AS IF this specific open
        # quote were retired, without changing state or stealing cargo.
        if (_available_site_food(state, site) + offer["remaining"]
                < WAGE_FOOD + UNPROMISED_OPERATING_FOOD):
            continue
        return ident
    return None
