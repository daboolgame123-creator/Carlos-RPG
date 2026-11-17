"""PLAY49-J: opt-in real cost-backed cooked-food quotes from local receipts.

Pure selector, not a story generator or artificial buyer. A recipe-completed
plate is quoted only if the site has actual purchase receipts for EACH consumed
input since the preceding cooked-food batch. Existing reducers remain trusted.
"""
from __future__ import annotations

from .domain import WorldState
from .economic_autonomy import OfferIntent, _event_id
from .market import MAX_PRICE, MAX_QUANTITY, MONEY, _present
from .production import recipe_inputs


def has_prepared_food_recipe(state: WorldState, site_id: str) -> bool:
    """Distinguish actual compound kitchens from ordinary generic food stalls."""
    return any(
        r["site_id"] == site_id and r["output_resource"] == "food"
        and "inputs" in r and r["output_amount"] == 1
        and type(r.get("wage_coin")) is int and r["wage_coin"] >= 1
        for r in state.production_recipes.values()
    )


def choose_local_costed_plate_offer(
    state: WorldState, keeper_id: str
) -> OfferIntent | None:
    """Price ONE actual on-site prepared plate from recorded cash outlays + wage.

    No received stock / completed job / authentic on-site ingredient receipts
    means NO quote, rather than silently selling it as generic 2-copper food.
    The posted price is not itself a sale and does not promise a buyer.
    """
    if keeper_id not in state.npcs:
        return None
    site = state.entities[keeper_id]["location_id"]
    stall = state.market_stalls.get(site)
    if (stall is None or stall["keeper_id"] != keeper_id
            or state.npcs[keeper_id]["role"] != "merchant"
            or not _present(state.to_dict(), keeper_id, site)
            or not has_prepared_food_recipe(state, site)):
        return None
    cash = state.resources.get(site, {}).get(MONEY)
    food = state.resources.get(site, {}).get("food")
    if (type(cash) is not int or cash < 0
            or type(food) is not int or food != 1):
        return None
    if any(
        o["status"] == "open" and o["stock_owner_id"] == site
        and o["resource"] == "food"
        for o in state.market_offers.values()
    ):
        return None
    kitchen_recipes = [
        (name, rec) for name, rec in state.production_recipes.items()
        if rec["site_id"] == site and rec["output_resource"] == "food"
        and "inputs" in rec and rec["output_amount"] == 1
        and type(rec.get("wage_coin")) is int and rec["wage_coin"] >= 1
    ]
    # Ambiguous recipes may not reuse each other's historical receipt costs.
    if len(kitchen_recipes) != 1:
        return None
    recipe_id, rec = kitchen_recipes[0]
    jobs = sorted(
        (j for j in state.production_jobs.values()
         if j["recipe_id"] == recipe_id and j["status"] == "completed"),
        key=lambda j: (j["started_at"], j["finished_at"]),
    )
    if not jobs:
        return None
    current_job = jobs[-1]
    preceding_start = jobs[-2]["started_at"] if len(jobs) > 1 else -1
    started = current_job["started_at"]
    if (current_job["finished_at"] is None
            or current_job["finished_at"] > state.time
            or current_job["output_after"] != 1
            or rec["output_amount"] != 1):
        return None
    invoice_total = 0
    for item, required in recipe_inputs(rec):
        matches = [
            t for t in state.market_trades.values()
            if t.get("business_keeper_id") == keeper_id
            and t["buyer_id"] == site
            and t["site_id"] == site
            and t["resource"] == item
            and t["payment_resource"] == MONEY
            and t["quantity"] == required
            and preceding_start < t["executed_at"] <= started
        ]
        # Exactly one paid site receipt must back each consumed input.
        # This intentionally rejects bulk purchases and ambiguous ledgers.
        if len(matches) != 1:
            return None
        t = matches[0]
        price = t["total_paid"]
        if (type(price) is not int or price < 1
                or price != required * t["unit_price"]):
            return None
        invoice_total += price
    wage = rec["wage_coin"]
    final_price = invoice_total + wage
    if not 1 <= final_price <= MAX_PRICE:
        return None
    offer_id = _event_id("menu", site, state.time)
    if offer_id in state.market_offers:
        return None
    return OfferIntent(
        keeper_id, site, offer_id, 1,
        f"prepared_recipe={recipe_id}; paid_ingredient_copper={invoice_total}; "
        f"signed_cook_wage={wage}; revenue_only_on_real_sale=1",
        final_price,
    )
