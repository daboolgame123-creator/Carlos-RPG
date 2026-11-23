"""P7: previously earned on-site food wage can consume unsold OLD owner quote.

Synthetic micro-ledger exercises the pure selector and pre-existing signed
payroll/market reducers. Authentic 228-hour A/B runs separately on saved worlds.
"""
import pytest

from carlos_sim.domain import DomainEvent, WorldState
from carlos_sim.market import close_offer
from carlos_sim.steward_food_payroll import (
    choose_steward_earned_wage_quote_retirement,
    choose_steward_food_wage, pay_steward_food_wage,
    validate_steward_food_wage_receipt,
)
from test_play48_real_watch_income_24h import seed


def sample(tmp_path):
    d = seed(tmp_path / "p7-synthetic.sqlite").to_dict()
    assert d["entities"]["salma"]["location_id"] == "market"
    d["time"] = 10 * 3600
    d["market_stalls"]["market"]["food_wage_sales_required"] = 2
    d["market_stalls"]["market"].pop("community_food", None)
    d["resources"]["market"]["food"] = 8
    d["resources"]["salma"]["food"] = 0
    d["market_offers"]["old"] = {
        "seller_id": "salma", "stock_owner_id": "market",
        "site_id": "market", "resource": "food", "quantity": 8,
        "remaining": 8, "payment_resource": "coin_copper",
        "unit_price": 2, "posted_at": 100, "status": "open",
        "closed_at": None,
    }
    for i in range(2):
        d["market_trades"][f"sale-{i}"] = {
            "site_id": "market", "stock_owner_id": "market",
            "seller_id": "salma", "resource": "food",
            "payment_resource": "coin_copper", "total_paid": 2,
            "executed_at": 1000 + i,
        }
    return d


def test_signed_wage_releases_only_a_real_unsold_local_quote(tmp_path):
    d = sample(tmp_path)
    s = WorldState(**d)
    before = s.to_dict()
    assert choose_steward_food_wage(s, "market") is None
    assert choose_steward_earned_wage_quote_retirement(s) == "old"
    assert s.to_dict() == before
    close_offer(d, DomainEvent("MarketOfferClosed", "salma",
                               "owner honors real wage", d["time"],
                               {"id": "old"}), market_authorized=True)
    earned = choose_steward_food_wage(WorldState(**d), "market")
    assert earned in ("sale-0", "sale-1")
    pay_steward_food_wage(d, DomainEvent(
        "MarketStewardFoodWagePaid", None, "earned local food",
        d["time"], {"site_id": "market", "trade_id": earned,
                     "amount": 1}), market_authorized=True)
    assert d["resources"]["market"]["food"] == 7
    assert d["resources"]["salma"]["food"] == 1
    assert d["resources"]["market"]["food"] + d["resources"]["salma"]["food"] == 8
    assert sum("steward_food_wage" in t for t in d["market_trades"].values()) == 1
    validate_steward_food_wage_receipt(d, d["market_trades"][earned])
    assert choose_steward_earned_wage_quote_retirement(WorldState(**d)) is None


@pytest.mark.parametrize("alter", [
    lambda d: d["market_stalls"]["market"].pop("food_wage_sales_required"),
    lambda d: d["market_trades"].pop("sale-1"),
    lambda d: d["market_trades"]["sale-0"].update(steward_food_wage={
        "paid_at": 1000,
    }),
    lambda d: d["market_offers"]["old"].update(posted_at=10 * 3600 - 10),
    lambda d: d["market_offers"]["old"].update(status="closed"),
    lambda d: d["market_offers"]["old"].update(stock_owner_id="salma"),
    lambda d: d["market_offers"]["old"].update(seller_id="adel"),
    lambda d: d["market_offers"]["old"].update(resource="grain"),
    lambda d: d["market_offers"]["old"].update(remaining=0),
    lambda d: d["resources"]["market"].update(food=1),
    lambda d: d["entities"]["salma"].update(location_id="farm"),
    lambda d: d["resources"]["adel"].update(coin_copper=2),
])
def test_no_unearned_customer_funds_or_absent_owner_quote_withdrawal(tmp_path, alter):
    d = sample(tmp_path)
    alter(d)
    assert choose_steward_earned_wage_quote_retirement(WorldState(**d)) is None


def test_contractual_relief_comes_before_merchant_wage(tmp_path):
    d = sample(tmp_path)
    d["market_stalls"]["market"]["community_food"] = {
        "daily_limit": 2, "payments": [],
    }
    d["npcs"]["adel"]["needs"]["hunger"] = 100
    d["resources"]["adel"]["food"] = 0
    d["resources"]["adel"]["coin_copper"] = 0
    assert choose_steward_earned_wage_quote_retirement(WorldState(**d)) is None
