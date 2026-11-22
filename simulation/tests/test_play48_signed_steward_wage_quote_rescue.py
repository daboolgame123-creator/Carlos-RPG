"""P7: market seller may honor an *already-earned, signed* wage from real owner food.

Only an aged unfilled customer listing is withdrawn; the existing wage reducer
moves the actual loaf, preserving the customer's old trade receipts and money.
"""
from __future__ import annotations

from carlos_sim import DomainEvent
from carlos_sim.domain import WorldState
from carlos_sim.market import post_offer, execute_trade, close_offer, validate_market
from carlos_sim.steward_food_payroll import (
    sign_steward_food_contract, choose_steward_food_wage,
    choose_signed_steward_wage_quote_retirement, pay_steward_food_wage,
)
from test_play48_community_rations import market


def _post(s, ident: str, quantity: int):
    post_offer(s, DomainEvent(
        "MarketOfferPosted", "salma", "on-site seller's real bread",
        s["time"], {
            "id": ident, "seller_id": "salma", "stock_owner_id": "market",
            "site_id": "market", "resource": "food",
            "payment_resource": "coin_copper", "unit_price": 2,
            "quantity": quantity,
        }), market_authorized=True)


def _world():
    s = market(food=8, hunger=90, cash=2)
    s["resources"]["salma"] = {"food": 0, "coin_copper": 0}
    s["npcs"]["salma"]["needs"]["hunger"] = 100
    s["entities"]["adel"] = {"controller": "npc", "location_id": "market"}
    s["npcs"]["adel"] = {"role": "guard", "needs": {"hunger": 90}}
    s["resources"]["adel"] = {"food": 0, "coin_copper": 2}
    sign_steward_food_contract(s, DomainEvent(
        "MarketStewardFoodContractSigned", None,
        "trusted owner signs two sales for one real loaf", 0,
        {"site_id": "market", "keeper_id": "salma", "sales_per_wage": 2},
    ), bootstrap=True)
    _post(s, "old-sold", 2)
    for ident, buyer in (("sale-a", "nora"), ("sale-b", "adel")):
        execute_trade(s, DomainEvent("MarketTradeExecuted", buyer,
            "actual local cash and food swap", 0, {
                "id": ident, "offer_id": "old-sold", "buyer_id": buyer,
                "quantity": 1, "expected_unit_price": 2,
            }), market_authorized=True)
    assert s["market_offers"]["old-sold"]["status"] == "filled"
    assert s["resources"]["market"]["food"] == 6
    assert s["resources"]["market"]["coin_copper"] == 4
    _post(s, "old-unsold", 6)
    s["time"] = 7 * 3600
    return s


def test_earned_wage_releases_only_aged_unsold_owner_quote_then_pays_real_loaf():
    s = _world()
    before = WorldState(**s).to_dict()
    assert choose_steward_food_wage(WorldState(**s), "market") is None
    assert choose_signed_steward_wage_quote_retirement(WorldState(**s), "market") == "old-unsold"
    assert WorldState(**s).to_dict() == before  # pure proposal; never debits inventory
    close_offer(s, DomainEvent("MarketOfferClosed", "salma",
        "owner withdraws aged price quote", s["time"],
        {"id": "old-unsold"}), market_authorized=True)
    trade = choose_steward_food_wage(WorldState(**s), "market")
    assert trade in ("sale-a", "sale-b")
    pay_steward_food_wage(s, DomainEvent("MarketStewardFoodWagePaid",
        None, "earned signed salary", s["time"],
        {"site_id": "market", "trade_id": trade, "amount": 1}),
        market_authorized=True)
    assert s["resources"]["market"]["food"] == 5
    assert s["resources"]["salma"]["food"] == 1
    assert s["resources"]["market"]["coin_copper"] == 4
    assert s["market_offers"]["old-sold"]["status"] == "filled"
    assert s["market_offers"]["old-unsold"]["status"] == "closed"
    assert sum("steward_food_wage" in t for t in s["market_trades"].values()) == 1
    assert choose_signed_steward_wage_quote_retirement(WorldState(**s), "market") is None
    validate_market(s)


def test_unpaid_duty_does_not_override_physically_solvent_customer():
    s = _world()
    # Reassign an existing shop coin, not a new coin, to a buyer at this counter.
    s["resources"]["market"]["coin_copper"] -= 2
    s["resources"]["nora"]["coin_copper"] += 2
    assert choose_signed_steward_wage_quote_retirement(WorldState(**s), "market") is None


def test_no_salary_retirement_without_signed_contract_or_two_sales():
    s = _world()
    s["market_stalls"]["market"].pop("food_wage_sales_required")
    assert choose_signed_steward_wage_quote_retirement(WorldState(**s), "market") is None
    s = _world()
    s["market_trades"].pop("sale-b")
    assert choose_signed_steward_wage_quote_retirement(WorldState(**s), "market") is None


def test_recent_offer_never_withdrawn_and_unquoted_wage_needs_no_withdrawal():
    s = _world()
    s["time"] = 5 * 3600
    assert choose_signed_steward_wage_quote_retirement(WorldState(**s), "market") is None
    s = _world()
    s["resources"]["market"]["food"] += 2
    assert choose_steward_food_wage(WorldState(**s), "market") is not None
    assert choose_signed_steward_wage_quote_retirement(WorldState(**s), "market") is None
