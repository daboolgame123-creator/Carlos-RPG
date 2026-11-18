"""Market owner's explicitly signed physical food relief, PLAY48 P0."""
import pytest

from carlos_sim import DomainEvent
from carlos_sim.community_food import (
    sign_market_relief, choose_market_ration, pay_market_ration,
    validate_market_relief, DAY,
)
from carlos_sim.domain import WorldState
from carlos_sim.market import post_offer


def market(*, food=4, hunger=90, cash=0, at_market=True):
    return WorldState(
        "pilot", time=0,
        locations={"market": {"name": "market"}, "farm": {"name": "farm"}},
        entities={
            "salma": {"controller": "npc", "location_id": "market"},
            "nora": {"controller": "npc", "location_id": "market" if at_market else "farm"},
        },
        npcs={"salma": {"role": "merchant", "needs": {"hunger": 30}},
              "nora": {"role": "farmer", "needs": {"hunger": hunger}}},
        resources={"market": {"food": food, "coin_copper": 0},
                   "nora": {"food": 0, "coin_copper": cash}},
        market_stalls={"market": {"keeper_id": "salma"}},
    ).to_dict()


def configured(*, food=4, hunger=90, cash=0, at_market=True):
    state = market(food=food, hunger=hunger, cash=cash, at_market=at_market)
    signed = DomainEvent(
        "MarketCommunityRationsSigned", None, "market owner opts in", 0,
        {"site_id": "market", "keeper_id": "salma", "daily_limit": 2},
    )
    sign_market_relief(state, signed, bootstrap=True)
    validate_market_relief(state, state["market_stalls"]["market"])
    return state


def ration(state, *, recipient="nora", authorized=True):
    return pay_market_ration(
        state, DomainEvent("MarketCommunityRationIssued", None,
                           "witnessed need, market owner contract", state["time"],
                           {"site_id": "market", "recipient_id": recipient, "amount": 1}),
        market_authorized=authorized,
    )


def test_owner_consent_is_required_and_only_signed_at_genesis():
    s = market()
    assert choose_market_ration(WorldState(**s)) is None
    with pytest.raises(ValueError):
        ration(s)
    signed = DomainEvent("MarketCommunityRationsSigned", None, "attempt late", DAY,
                         {"site_id": "market", "keeper_id": "salma", "daily_limit": 2})
    s["time"] = DAY
    with pytest.raises(ValueError):
        sign_market_relief(s, signed, bootstrap=True)
    s["time"] = 0
    sign_market_relief(s, signed, bootstrap=True)
    with pytest.raises(ValueError):
        sign_market_relief(s, signed, bootstrap=True)


def test_original_market_merchant_wage_and_owner_ration_contracts_can_coexist():
    from carlos_sim.steward_food_payroll import sign_steward_food_contract
    from carlos_sim.market import validate_market
    s = market()
    s["resources"]["salma"] = {"food": 0, "coin_copper": 0}
    sign_steward_food_contract(s, DomainEvent(
        "MarketStewardFoodContractSigned", None, "original merchant job", 0,
        {"site_id": "market", "keeper_id": "salma", "sales_per_wage": 2},
    ), bootstrap=True)
    sign_market_relief(s, DomainEvent(
        "MarketCommunityRationsSigned", None, "later consent", 0,
        {"site_id": "market", "keeper_id": "salma", "daily_limit": 2},
    ), bootstrap=True)
    assert s["market_stalls"]["market"]["food_wage_sales_required"] == 2
    validate_market(s)


def test_actual_penniless_present_and_hungry_recipient_gets_conserved_food():
    s = configured()
    assert choose_market_ration(WorldState(**s)) == "nora"
    with pytest.raises(ValueError):
        ration(s, authorized=False)
    ration(s)
    assert (s["resources"]["market"]["food"], s["resources"]["nora"]["food"]) == (3, 1)
    rec = s["market_stalls"]["market"]["community_food"]["payments"][0]
    assert rec["source_before"] - rec["source_after"] == 1
    assert rec["recipient_after"] - rec["recipient_before"] == 1
    validate_market_relief(s, s["market_stalls"]["market"])
    with pytest.raises(ValueError):
        ration(s)


@pytest.mark.parametrize("options", [
    {"hunger": 74}, {"cash": 1}, {"at_market": False}, {"food": 0},
])
def test_no_gift_without_on_site_need_or_real_stock(options):
    s = configured(**options)
    assert choose_market_ration(WorldState(**s)) is None
    with pytest.raises(ValueError):
        ration(s)


def test_customer_offers_are_protected_and_one_unit_is_left_unquoted():
    s = configured(food=4)
    def quote(q):
        return DomainEvent("MarketOfferPosted", "salma", "seller at market", 0,
                           {"id": "offer", "seller_id": "salma",
                            "stock_owner_id": "market", "site_id": "market",
                            "resource": "food", "payment_resource": "coin_copper",
                            "quantity": q, "unit_price": 2})
    with pytest.raises(ValueError):
        post_offer(s, quote(4), market_authorized=True)
    post_offer(s, quote(3), market_authorized=True)
    # A second direct listing must not double-count already quoted units.
    second = DomainEvent("MarketOfferPosted", "salma", "new listing", 0,
                         {**quote(1).data, "id": "other"})
    with pytest.raises(ValueError):
        post_offer(s, second, market_authorized=True)
    assert choose_market_ration(WorldState(**s)) == "nora"
    ration(s)
    assert s["resources"]["market"]["food"] == 3
    assert s["market_offers"]["offer"]["remaining"] == 3
    with pytest.raises(ValueError):
        ration(s)


def test_repeat_and_day_limit_are_enforced_even_when_food_is_present():
    s = configured(food=10)
    s["time"] = DAY
    ration(s)
    s["resources"]["nora"]["food"] = 0  # fixture: meal consumed outside this reducer
    s["time"] += 1
    with pytest.raises(ValueError):
        ration(s)
    s["time"] += DAY
    ration(s)
    s["resources"]["nora"]["food"] = 0
    s["time"] += DAY
    ration(s)
    with pytest.raises(ValueError):
        ration(s)
    validate_market_relief(s, s["market_stalls"]["market"])


def test_corrupt_receipt_and_limit_are_rejected():
    s = configured()
    ration(s)
    rec = s["market_stalls"]["market"]["community_food"]["payments"][0]
    rec["source_after"] += 1
    with pytest.raises(ValueError):
        validate_market_relief(s, s["market_stalls"]["market"])
