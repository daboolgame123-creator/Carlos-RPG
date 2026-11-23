"""P12 opt-in local ration RECEIPT during rest, never meal while busy.

The canonical recipient receives only one unquoted owner-owned loaf under an
already-signed market contract. Existing NPC eating/market authorization never
weakens. This is a tiny projection fixture; authentic save A/B is separate.
"""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent
from carlos_sim.community_food import (
    choose_market_ration, pay_market_ration, validate_market_relief,
)
from carlos_sim.consumption import choose_food_consumption
from carlos_sim.domain import WorldState
from test_play48_community_rations import configured


def resting_market():
    s = configured(food=4, hunger=100, cash=0)
    s["time"] = 3600
    s["npcs"]["nora"]["last_decision"] = None
    s["actions"]["rest:nora"] = {
        "npc_id": "nora", "action": "rest",
        "start": 3600, "due": 3720, "schedule_id": "npc-action:rest:nora",
        "status": "running", "completed_at": None, "result": None,
    }
    return s


def event(s, *, rest=True, recipient="nora"):
    p = {"site_id": "market", "recipient_id": recipient, "amount": 1}
    if rest:
        p["receive_while_resting"] = True
    return DomainEvent("MarketCommunityRationIssued", None,
                       "real signed local ration", s["time"], p)


def test_resting_citizen_receives_actual_loaf_then_eats_only_after_rest():
    s = resting_market()
    assert choose_market_ration(WorldState(**s)) is None
    assert choose_market_ration(
        WorldState(**s), receive_while_resting=True) == "nora"
    with pytest.raises(ValueError, match="signed, local"):
        pay_market_ration(s, event(s, rest=False), market_authorized=True)
    with pytest.raises(ValueError, match="signed, local"):
        pay_market_ration(s, event(s), market_authorized=False)
    pay_market_ration(s, event(s), market_authorized=True)
    assert s["resources"]["market"]["food"] == 3
    assert s["resources"]["nora"]["food"] == 1
    assert s["npcs"]["nora"]["needs"]["hunger"] == 100
    assert choose_food_consumption(WorldState(**s), "nora") is None
    validate_market_relief(s, s["market_stalls"]["market"])
    with pytest.raises(ValueError):
        pay_market_ration(s, event(s), market_authorized=True)
    s["time"] = 3720
    s["actions"]["rest:nora"]["status"] = "completed"
    s["actions"]["rest:nora"]["completed_at"] = 3720
    assert choose_food_consumption(WorldState(**s), "nora") == 1


@pytest.mark.parametrize("block", [
    "not_market", "traveling", "working", "producing",
    "two_actions", "solvent", "already_fed", "not_hungry",
    "keeper_resting", "no_stock", "quoted_stock",
])
def test_never_pays_unqualified_resting_recipient(block):
    s = resting_market()
    if block == "not_market":
        s["entities"]["nora"]["location_id"] = "farm"
    if block == "traveling":
        s["travels"]["t"] = {"npc_id": "nora", "status": "traveling"}
    if block == "working":
        s["actions"]["rest:nora"]["action"] = "work"
    if block == "producing":
        s["production_jobs"]["j"] = {"npc_id": "nora", "status": "running"}
    if block == "two_actions":
        s["actions"]["other"] = {"npc_id": "nora", "status": "running",
                                  "action": "work"}
    if block == "solvent":
        s["resources"]["nora"]["coin_copper"] = 2
    if block == "already_fed":
        s["resources"]["nora"]["food"] = 1
    if block == "not_hungry":
        s["npcs"]["nora"]["needs"]["hunger"] = 74
    if block == "keeper_resting":
        s["actions"]["rest:salma"] = {"npc_id": "salma", "status": "running",
                                      "action": "rest"}
    if block == "no_stock":
        s["resources"]["market"]["food"] = 0
    if block == "quoted_stock":
        s["market_offers"]["quote"] = {
            "status": "open", "site_id": "market",
            "stock_owner_id": "market", "resource": "food",
            "remaining": 4,
        }
    assert choose_market_ration(
        WorldState(**s), receive_while_resting=True) is None
    with pytest.raises(ValueError):
        pay_market_ration(s, event(s), market_authorized=True)


def test_explicit_rest_receipt_never_changes_daily_cap_or_merchant_consent():
    s = resting_market()
    pay_market_ration(s, event(s), market_authorized=True)
    assert len(s["market_stalls"]["market"]["community_food"]["payments"]) == 1
    assert s["market_stalls"]["market"]["community_food"]["daily_limit"] == 2
    # A separate poor person may receive the other real daily loaf.
    s["entities"]["adel"] = {"controller": "npc", "location_id": "market"}
    s["npcs"]["adel"] = {"role": "guard", "needs": {"hunger": 100}}
    s["resources"]["adel"] = {"food": 0, "coin_copper": 0}
    pay_market_ration(s, event(s, recipient="adel", rest=False),
                      market_authorized=True)
    assert s["resources"]["market"]["food"] == 2
    assert s["resources"]["nora"]["food"] == 1
    assert s["resources"]["adel"]["food"] == 1
    with pytest.raises(ValueError):
        pay_market_ration(s, event(s), market_authorized=True)
    validate_market_relief(s, s["market_stalls"]["market"])


def test_rest_receipt_flag_cannot_be_used_to_bypass_normal_idle_eligibility():
    s = resting_market()
    s["actions"]["rest:nora"]["status"] = "completed"
    assert choose_market_ration(WorldState(**s)) == "nora"
    assert choose_market_ration(
        WorldState(**s), receive_while_resting=True) == "nora"
    # Ordinary owner-signed local aid remains valid, but the separate
    # rest-only marker cannot be smuggled into a free recipient's receipt.
    with pytest.raises(ValueError):
        pay_market_ration(s, event(s, rest=True), market_authorized=True)
    pay_market_ration(s, event(s, rest=False), market_authorized=True)
    assert s["resources"]["nora"]["food"] == 1
