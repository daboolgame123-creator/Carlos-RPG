"""PLAY48AA isolated red-team checks for authentic farm grain-for-bread.

Synthetic resource changes below deliberately exercise internal guards and
are NOT game-world events, physical journeys or evidence of actual food
delivery. Full 13-NPC 48h real economic A/B runs in the independent AA CI.
"""
from __future__ import annotations

import json

import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.supply import (
    _signed_physical_lane, _bakery_return_unpromised_food,
    project_cargo, validate_supply_circuits,
)
from test_play47_closure_endurance import WORLD
from test_play48aa_actual_barter_bread_return import _seed_signed_share


def _return_site(state):
    d = state.to_dict()
    courier = d["supply_circuits"]["huda"]
    courier["index"] = 4
    d["entities"]["huda"]["location_id"] = "bakery"
    courier["bread_share_earned"] = 1
    d["resources"]["bakery"]["food"] = 10
    d["resources"]["bakery"]["coin_copper"] = 3
    return d, courier


def _fake_event(verb, resource):
    return DomainEvent(verb, "huda", "synthetic security test only", 0,
        {"courier_id": "huda", "resource": resource})


def test_shop_customer_quotes_unavailable_for_barter(tmp_path):
    base = _seed_signed_share(tmp_path / "aa-shop-commitment.sqlite", share=True)
    d, worker = _return_site(base)
    # This is a synthetic open offer: a bakery cannot pay an old farm
    # obligation with ten loaves it already promised to local customers.
    d["market_offers"]["fictitious-security-quote"] = {
        "status": "open", "site_id": "bakery", "stock_owner_id": "bakery",
        "resource": "food", "remaining": 10,
    }
    assert _bakery_return_unpromised_food(d) == 0
    assert _signed_physical_lane(d, worker, "huda")[2] == "coin_copper"
    with pytest.raises(ValueError, match="local planned shipping lane"):
        project_cargo(d, _fake_event("SupplyCargoPicked", "food"),
                      supply_authorized=True)
    assert d["resources"]["bakery"]["food"] == 10
    assert d["resources"]["farm"]["food"] == 0

    # Leave TWO legitimately unquoted bakery loaves, one stays at site.
    d["market_offers"]["fictitious-security-quote"]["remaining"] = 8
    assert _bakery_return_unpromised_food(d) == 2
    assert _signed_physical_lane(d, worker, "huda") == (
        "bakery", "farm", "food")
    project_cargo(d, _fake_event("SupplyCargoPicked", "food"),
                  supply_authorized=True)
    assert d["resources"]["bakery"]["food"] == 9
    assert d["resources"]["huda"]["food"] == 1
    assert d["resources"]["bakery"]["coin_copper"] == 3
    assert d["supply_circuits"]["huda"]["bread_share_delivered"] == 0
    with pytest.raises(ValueError):
        project_cargo(d, _fake_event("SupplyCargoPicked", "coin_copper"),
                      supply_authorized=True)


def test_one_parcel_per_return_trip_cash_rotation_and_no_double_delivery(tmp_path):
    base = _seed_signed_share(tmp_path / "aa-cash-and-food.sqlite", share=True)
    d, worker = _return_site(base)
    # The first eligible tour carries FOOD. The next with sufficient
    # copper carries CASH, so we do not promise two parcels on one road.
    assert _signed_physical_lane(d, worker, "huda") == (
        "bakery", "farm", "food")
    worker["rounds"] = 1
    assert _signed_physical_lane(d, worker, "huda") == (
        "bakery", "farm", "coin_copper")
    worker["rounds"] = 0
    project_cargo(d, _fake_event("SupplyCargoPicked", "food"),
                  supply_authorized=True)
    worker["index"] = 5
    d["entities"]["huda"]["location_id"] = "farm"
    project_cargo(d, _fake_event("SupplyCargoDelivered", "food"),
                  supply_authorized=True)
    assert d["resources"]["farm"]["food"] == 1
    assert d["resources"]["bakery"]["food"] == 9
    assert d["resources"]["huda"]["food"] == 0
    assert worker["bread_share_earned"] == worker["bread_share_delivered"] == 1
    assert worker["carry"] is None
    with pytest.raises(ValueError):
        project_cargo(d, _fake_event("SupplyCargoDelivered", "food"),
                      supply_authorized=True)
    assert d["resources"]["farm"]["food"] == 1


@pytest.mark.parametrize("earned, delivered", [(-1,0), (0,1), (True,0), (1,False)])
def test_tampered_barter_counts_are_rejected_by_durable_validator(tmp_path,
                                                                 earned, delivered):
    s = _seed_signed_share(tmp_path / f"bad-{earned}-{delivered}.sqlite", share=True)
    d = s.to_dict()
    d["supply_circuits"]["huda"]["bread_share_earned"] = earned
    d["supply_circuits"]["huda"]["bread_share_delivered"] = delivered
    with pytest.raises(ValueError, match="barter account"):
        validate_supply_circuits(d)


def test_invented_first_turn_bread_pickup_fails_closed_in_real_store(tmp_path):
    path = tmp_path / "real-store-no-credit.sqlite"
    s = _seed_signed_share(path, share=True)
    with SQLiteEventStore(path) as db:
        original = db.verify(WORLD).to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            with pytest.raises((ValueError, InvalidEvent)):
                db.append(WORLD, "forged-early-return-loaf", s.revision,
                    [_fake_event("SupplyCargoPicked", "food")],
                    supply_authorized=True)
            assert db.verify(WORLD).to_dict() == original
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        finally:
            clock.close_session(WORLD)
