"""Bounded optional owner-signed withdrawal of stale unsold quotes for real aid."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent
from carlos_sim.domain import WorldState
from carlos_sim.market import post_offer, close_offer, validate_market
from carlos_sim.community_food import (
    signed_local_relief_quote_capacity, choose_market_relief_quote_retirement,
    choose_market_ration, pay_market_ration,
)
from carlos_sim.economic_autonomy import choose_local_food_offer
from test_play48_community_rations import configured


def _world(*, additional_needy=True, paying_customer=False, stock=4):
    s = configured(food=stock, hunger=100)
    if additional_needy:
        s["entities"]["adel"] = {"controller": "npc", "location_id": "market"}
        s["npcs"]["adel"] = {"role": "guard", "needs": {"hunger": 100}}
        s["resources"]["adel"] = {"food": 0, "coin_copper": 0}
    if paying_customer:
        s["entities"]["layla"] = {"controller": "npc", "location_id": "market"}
        s["npcs"]["layla"] = {"role": "fisher", "needs": {"hunger": 90}}
        s["resources"]["layla"] = {"food": 0, "coin_copper": 2}
    return s


def _post(s, *, offer_id, amount):
    post_offer(s, DomainEvent("MarketOfferPosted", "salma", "real local quote",
                              s["time"], {"id": offer_id, "seller_id": "salma",
                              "stock_owner_id": "market", "site_id": "market",
                              "resource": "food", "payment_resource": "coin_copper",
                              "quantity": amount, "unit_price": 2}),
               market_authorized=True)


def test_disabled_default_does_not_shrink_normal_food_quote():
    s = _world()
    regular = choose_local_food_offer(WorldState(**s), "salma")
    assert regular is not None and regular.quantity == 4
    protected = choose_local_food_offer(
        WorldState(**s), "salma", reserve_signed_relief=True)
    assert protected is not None and protected.quantity == 2
    assert signed_local_relief_quote_capacity(WorldState(**s)) == 2


def test_old_fully_quoted_owner_food_requires_actual_market_closure_before_grant():
    s = _world()
    _post(s, offer_id="old", amount=4)
    assert choose_market_relief_quote_retirement(WorldState(**s)) is None
    assert choose_market_ration(WorldState(**s)) is None
    s["time"] = 7 * 3600
    assert choose_market_relief_quote_retirement(WorldState(**s)) == "old"
    # A policy proposal cannot itself deallocate or give a single loaf.
    assert s["market_offers"]["old"]["status"] == "open"
    assert s["resources"]["market"]["food"] == 4
    close_offer(s, DomainEvent("MarketOfferClosed", "salma",
                              "real seller withdraws aged listing",
                              s["time"], {"id": "old"}), market_authorized=True)
    assert s["market_offers"]["old"]["status"] == "closed"
    # Explicit local shopkeeper re-lists only the physically uncommitted 2.
    quote = choose_local_food_offer(
        WorldState(**s), "salma", reserve_signed_relief=True)
    assert quote is not None and quote.quantity == 2 and quote.unit_price == 2
    _post(s, offer_id="new", amount=quote.quantity)
    assert s["market_offers"]["new"]["remaining"] == 2
    for recipient in ("adel", "nora"):
        assert choose_market_ration(WorldState(**s)) == recipient
        pay_market_ration(s, DomainEvent(
            "MarketCommunityRationIssued", None, "owner-authorized actual loaf",
            s["time"], {"site_id": "market", "recipient_id": recipient, "amount": 1}),
            market_authorized=True)
    assert s["resources"]["market"]["food"] == 2
    assert s["market_offers"]["new"]["remaining"] == 2
    assert s["resources"]["adel"]["food"] == 1
    assert s["resources"]["nora"]["food"] == 1
    assert choose_market_relief_quote_retirement(WorldState(**s)) is None
    validate_market(s)


def test_never_withdraw_aged_retail_listing_with_solvent_present_buyer():
    s = _world(paying_customer=True)
    _post(s, offer_id="old", amount=4)
    s["time"] = 8 * 3600
    assert signed_local_relief_quote_capacity(WorldState(**s)) == 0
    assert choose_market_relief_quote_retirement(WorldState(**s)) is None
    assert choose_market_ration(WorldState(**s)) is None
    assert s["market_offers"]["old"]["remaining"] == 4


def test_no_market_owner_contract_cannot_reserve_or_withdraw_stock():
    s = _world()
    del s["market_stalls"]["market"]["community_food"]
    _post(s, offer_id="old", amount=4)
    s["time"] = 48 * 3600
    assert signed_local_relief_quote_capacity(WorldState(**s)) == 0
    assert choose_market_relief_quote_retirement(WorldState(**s)) is None
    assert choose_market_ration(WorldState(**s)) is None


@pytest.mark.parametrize("invalid", [None, 1, 0, "true", [], {}])
def test_relief_quote_flag_rejects_non_boolean_without_masking_adaptive_error(invalid):
    s = WorldState(**_world())
    with pytest.raises(ValueError, match="reserve_signed_relief"):
        choose_local_food_offer(s, "salma", reserve_signed_relief=invalid)
    with pytest.raises(ValueError, match="adaptive"):
        choose_local_food_offer(s, "salma", adaptive=invalid)
