"""PLAY49-I: opt-in local business input procurement, with full-batch solvency.

A pure selector; market/production reducers still enforce every physical
transfer, quote, role and wage. No automatic grants or cross-site shopping.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain import WorldState
from .economic_autonomy import _event_id
from .market import MONEY, MAX_AMOUNT, _present, reserved_trade_units, trade_receipt_allowed
from .production import recipe_inputs


@dataclass(frozen=True)
class SiteInputIntent:
    keeper_id: str
    site_id: str
    offer_id: str
    trade_id: str
    unit_price: int
    reason: str


def choose_local_site_input_purchase(state: WorldState, site_id: str) -> SiteInputIntent | None:
    """Buy one ingredient only if a *whole* local recipe batch is fundable.

    The on-site merchant sees only actually posted local seller quotes.
    All missing ingredients must be physically present and affordable BEFORE
    spending the first site coin. A partially stocked recipe can continue on
    a later tick without spending from any employee's private wallet.
    """
    stall = state.market_stalls.get(site_id)
    if stall is None:
        return None
    keeper = stall["keeper_id"]
    if (keeper not in state.npcs
            or state.npcs[keeper]["role"] != "merchant"
            or not _present(state.to_dict(), keeper, site_id)):
        return None
    balances = state.resources.get(site_id, {})
    copper = balances.get(MONEY)
    if type(copper) is not int or not 0 <= copper <= MAX_AMOUNT:
        return None
    if not trade_receipt_allowed(state.supply_circuits, site_id, MONEY):
        return None
    # Existing completed signed wages belong to workers, not ingredient stock.
    due = sum(
        state.production_recipes[job["recipe_id"]]["wage_coin"]
        for job in state.production_jobs.values()
        if job["site_id"] == site_id and job["status"] == "completed"
        and "work_wage" not in job
        and "wage_coin" in state.production_recipes[job["recipe_id"]]
    )
    available = copper - reserved_trade_units(state.supply_circuits, site_id, MONEY) - due
    if available <= 0:
        return None
    raw = state.to_dict()
    for recipe_id, recipe in sorted(state.production_recipes.items()):
        if recipe["site_id"] != site_id:
            continue
        if any(job["status"] == "running" and job["site_id"] == site_id
               and job["recipe_id"] == recipe_id
               for job in state.production_jobs.values()):
            continue
        output = balances.get(recipe["output_resource"])
        tool = balances.get(recipe["tool_resource"])
        if (type(output) is not int or output != 0
                or type(tool) is not int or tool < 1):
            continue
        wanted = []
        estimated_total = 0
        possible = True
        for item, amount in recipe_inputs(recipe):
            stock = balances.get(item)
            if type(stock) is not int or stock < 0:
                possible = False
                break
            missing = max(0, amount - stock)
            if missing == 0:
                continue
            # One observed, available, genuine seller must satisfy each
            # missing kind. Do not speculate about unknown remote inventory.
            choices = []
            for offer_id, offer in sorted(state.market_offers.items()):
                if (offer["status"] != "open" or offer["site_id"] != site_id
                        or offer["resource"] != item
                        or offer["payment_resource"] != MONEY
                        or offer["remaining"] < missing
                        or offer["seller_id"] == keeper
                        or offer["stock_owner_id"] in (site_id, keeper)
                        or offer["seller_id"] == site_id
                        or not _present(raw, offer["seller_id"], site_id)
                        or not trade_receipt_allowed(
                            state.supply_circuits, offer["stock_owner_id"], MONEY)):
                    continue
                seller_stock = state.resources.get(offer["stock_owner_id"], {})
                goods = seller_stock.get(item)
                seller_coins = seller_stock.get(MONEY)
                price = offer["unit_price"]
                if (type(goods) is not int or type(seller_coins) is not int
                        or type(price) is not int or not 1 <= price <= 1000
                        or goods - reserved_trade_units(
                            state.supply_circuits, offer["stock_owner_id"], item) < missing
                        or seller_coins + missing * price > MAX_AMOUNT
                        or stock + missing > MAX_AMOUNT):
                    continue
                choices.append((price, offer_id))
            if not choices:
                possible = False
                break
            price, offer_id = min(choices)
            estimated_total += price * missing
            wanted.append((item, offer_id, price))
        if not possible or not wanted or estimated_total > available:
            continue
        item, offer_id, price = wanted[0]
        trade_id = _event_id("sitebuy", site_id, state.time)
        if trade_id in state.market_trades:
            return None
        return SiteInputIntent(
            keeper, site_id, offer_id, trade_id, price,
            f"local_recipe={recipe_id}; ingredient={item}; "
            f"complete_batch_cost={estimated_total}; "
            f"available_site_coins={available}"
        )
    return None
