"""PLAY48AB: bakery honors real farm-grain bread obligations before market shipping.

These small tests use a deliberately artificial local snapshot to attack
custody rules; actual 13-NPC true 48h is a separate full event-sourced test.
"""
from __future__ import annotations

import pytest

from carlos_sim.supply import (
    _signed_physical_lane, _bakery_return_unpromised_food,
    project_cargo,
)
from carlos_sim import DomainEvent
from test_play48aa_actual_barter_bread_return import _seed_signed_share


def event(kind, who, resource):
    return DomainEvent(kind, who, "test-only forged physical cargo", 0, {
        "courier_id": who, "resource": resource,
    })


def test_one_earned_grain_claim_must_reserve_real_bakery_food_for_return(tmp_path):
    state = _seed_signed_share(tmp_path / "farm-claim.sqlite", share=True)
    s = state.to_dict()
    h = s["supply_circuits"]["huda"]
    hana = s["supply_circuits"]["hana"]
    h["bread_share_earned"] = 1  # fixture only, never injected into a world.
    h["index"] = 2
    hana["index"] = 2
    s["entities"]["huda"]["location_id"] = "bakery"
    s["entities"]["hana"]["location_id"] = "bakery"
    s["resources"]["bakery"]["food"] = 1  # one actual test-owned loaf
    assert _bakery_return_unpromised_food(s) == 1

    assert _signed_physical_lane(s, h, "huda") is None
    assert _signed_physical_lane(s, hana, "hana") is None
    for who in ("huda", "hana"):
        with pytest.raises(ValueError, match="planned shipping lane"):
            project_cargo(s, event("SupplyCargoPicked", who, "food"),
                          supply_authorized=True)
    assert s["resources"]["bakery"]["food"] == 1

    # If a *second* physical loaf exists, the market can ship exactly one.
    s["resources"]["bakery"]["food"] = 2
    assert _signed_physical_lane(s, hana, "hana") == ("bakery", "market", "food")
    project_cargo(s, event("SupplyCargoPicked", "hana", "food"),
                  supply_authorized=True)
    assert s["resources"]["bakery"]["food"] == 1
    assert s["resources"]["hana"]["food"] == 1
    assert s["resources"]["market"]["food"] == 1  # original unmodified
    # Huda's obligation must survive that distinct sale cargo.
    h["index"] = 4
    assert _signed_physical_lane(s, h, "huda") == ("bakery", "farm", "food")
    project_cargo(s, event("SupplyCargoPicked", "huda", "food"),
                  supply_authorized=True)
    assert s["resources"]["bakery"]["food"] == 0
    assert s["resources"]["huda"]["food"] == 1
    assert h["bread_share_delivered"] == 0
    h["index"] = 5
    s["entities"]["huda"]["location_id"] = "farm"
    project_cargo(s, event("SupplyCargoDelivered", "huda", "food"),
                  supply_authorized=True)
    assert s["resources"]["farm"]["food"] == 1
    assert s["resources"]["huda"]["food"] == 0
    assert h["bread_share_earned"] == h["bread_share_delivered"] == 1
    assert s["resources"]["bakery"]["coin_copper"] >= 0


def test_no_claim_or_no_baked_food_never_blocks_other_market_couriers(tmp_path):
    a = _seed_signed_share(tmp_path / "default.sqlite", share=False)
    d = a.to_dict()
    d["resources"]["bakery"]["food"] = 1
    d["supply_circuits"]["hana"]["index"] = 2
    d["entities"]["hana"]["location_id"] = "bakery"
    assert _signed_physical_lane(d, d["supply_circuits"]["hana"], "hana") == (
        "bakery", "market", "food"
    )
    # A signed contract with no actual grain delivered earns NO claim.
    b = _seed_signed_share(tmp_path / "signed-no-work.sqlite", share=True)
    p = b.to_dict()
    p["resources"]["bakery"]["food"] = 1
    p["supply_circuits"]["hana"]["index"] = 2
    p["entities"]["hana"]["location_id"] = "bakery"
    assert _signed_physical_lane(p, p["supply_circuits"]["hana"], "hana") == (
        "bakery", "market", "food"
    )
    # No bakery food at all means neither market nor farm can conjure cargo.
    p["resources"]["bakery"]["food"] = 0
    p["supply_circuits"]["huda"]["bread_share_earned"] = 1
    assert _signed_physical_lane(p, p["supply_circuits"]["hana"], "hana") is None


def test_open_bakery_offers_cannot_be_repurposed_for_signed_farm(tmp_path):
    state = _seed_signed_share(tmp_path / "customer-rights.sqlite", share=True)
    s = state.to_dict()
    c = s["supply_circuits"]["huda"]
    c["bread_share_earned"] = 1
    c["index"] = 4
    s["entities"]["huda"]["location_id"] = "bakery"
    s["resources"]["bakery"]["food"] = 1
    s["market_offers"]["synthetic-protected-offer"] = {
        "status": "open", "site_id": "bakery",
        "stock_owner_id": "bakery", "resource": "food", "remaining": 1,
    }
    assert _bakery_return_unpromised_food(s) == 0
    assert _signed_physical_lane(s, c, "huda")[2] == "coin_copper"
    with pytest.raises(ValueError):
        project_cargo(s, event("SupplyCargoPicked", "huda", "food"),
                      supply_authorized=True)
    assert s["resources"]["bakery"]["food"] == 1
