"""PLAY48 optional signed steward wages: real sales, real local copper.

A registered merchant's employer explicitly signs one coin per successfully
completed on-site site-owned FOOD sale of at least two copper. No wage without
same-tick authenticated trade, customer inventory debit, or employer coins.
This is an experimental persisted Rules64 transition, not a free allowance.
"""
from __future__ import annotations
from typing import Any
from .domain import DomainEvent, WorldState
from .market import _balance, _id, _present, MONEY, MAX_AMOUNT


def configure_steward_wage(state: dict[str, Any], event: DomainEvent, *,
                            bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"site_id", "keeper_id", "wage_coin"}
            or type(p["wage_coin"]) is not int or p["wage_coin"] != 1):
        raise ValueError("merchant wage is a signed trusted time-zero contract")
    site, who = p["site_id"], p["keeper_id"]
    stall = state["market_stalls"].get(site)
    if (not isinstance(stall, dict) or set(stall) != {"keeper_id"}
            or stall["keeper_id"] != who
            or state["npcs"].get(who, {}).get("role") != "merchant"
            or not _present(state, who, site)
            or not _balance(state["resources"].get(site, {}).get(MONEY))
            or not _balance(state["resources"].get(who, {}).get(MONEY))):
        raise ValueError("merchant wage requires real employed steward and known cash ledgers")
    stall["wage_coin"] = 1


def _authentic_sale(state: WorldState | dict[str, Any], trade_id: str):
    items = state.market_trades if isinstance(state, WorldState) else state["market_trades"]
    trade = items.get(trade_id)
    now = state.time if isinstance(state, WorldState) else state["time"]
    if (trade is None or "sale_wage" in trade
            or trade["executed_at"] != now
            or trade["resource"] != "food" or trade["payment_resource"] != MONEY
            or trade["total_paid"] < 2
            or trade["stock_owner_id"] != trade["site_id"]):
        return None
    site, who = trade["site_id"], trade["seller_id"]
    stalls = state.market_stalls if isinstance(state, WorldState) else state["market_stalls"]
    profiles = state.npcs if isinstance(state, WorldState) else state["npcs"]
    stall = stalls.get(site)
    if (stall is None or stall.get("keeper_id") != who
            or stall.get("wage_coin") != 1
            or profiles[who]["role"] != "merchant"):
        return None
    return trade


def choose_steward_wage(state: WorldState, trade_id: str) -> int | None:
    trade = _authentic_sale(state, trade_id)
    if trade is None:
        return None
    site, who = trade["site_id"], trade["seller_id"]
    if not _present(state.to_dict(), who, site):
        return None
    site_cash = state.resources.get(site, {}).get(MONEY)
    worker_cash = state.resources.get(who, {}).get(MONEY)
    if not _balance(site_cash) or site_cash < 1 or not _balance(worker_cash) or worker_cash == MAX_AMOUNT:
        return None
    return 1


def pay_steward_wage(state: dict[str, Any], event: DomainEvent, *,
                     market_authorized: bool) -> None:
    p = event.data
    if (not market_authorized or event.actor_id is not None
            or set(p) != {"trade_id", "amount"}
            or not _id(p["trade_id"])
            or type(p["amount"]) is not int or p["amount"] != 1):
        raise ValueError("steward wages require trusted one-coin local sale payment")
    trade = _authentic_sale(state, p["trade_id"])
    if trade is None:
        raise ValueError("a unique same-tick contracted sale is required")
    site, who = trade["site_id"], trade["seller_id"]
    if not _present(state, who, site):
        raise ValueError("worker must be physically free at shop to receive wage")
    site_stock, worker_stock = state["resources"].get(site, {}), state["resources"].get(who, {})
    before_site, before_worker = site_stock.get(MONEY), worker_stock.get(MONEY)
    if (not _balance(before_site) or before_site < 1
            or not _balance(before_worker) or before_worker == MAX_AMOUNT):
        raise ValueError("employer has no funded unreserved coin")
    site_stock[MONEY], worker_stock[MONEY] = before_site - 1, before_worker + 1
    trade["sale_wage"] = {
        "worker_id": who, "site_id": site, "amount": 1,
        "paid_at": state["time"], "site_before": before_site,
        "site_after": before_site - 1, "worker_before": before_worker,
        "worker_after": before_worker + 1,
    }


def validate_steward_wage_receipt(state: dict[str, Any], trade: dict[str, Any]) -> None:
    wage = trade["sale_wage"]
    site, who = trade["site_id"], trade["seller_id"]
    stall = state["market_stalls"].get(site)
    if (not isinstance(wage, dict) or set(wage) != {
            "worker_id", "site_id", "amount", "paid_at",
            "site_before", "site_after", "worker_before", "worker_after"}
            or trade["stock_owner_id"] != site
            or trade["resource"] != "food"
            or trade["payment_resource"] != MONEY or trade["total_paid"] < 2
            or stall is None or stall.get("keeper_id") != who
            or stall.get("wage_coin") != 1
            or state["npcs"][who]["role"] != "merchant"
            or wage["worker_id"] != who or wage["site_id"] != site
            or type(wage["amount"]) is not int or wage["amount"] != 1
            or type(wage["paid_at"]) is not int
            or wage["paid_at"] != trade["executed_at"]
            or any(not _balance(wage[k]) for k in (
                "site_before", "site_after", "worker_before", "worker_after"))
            or wage["site_before"] - wage["site_after"] != 1
            or wage["worker_after"] - wage["worker_before"] != 1):
        raise ValueError("steward receipt must preserve exact trade, contract and coin conservation")
