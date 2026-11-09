"""Courier bottleneck diagnostics: demonstrate disabled flag versus real route.

All tests use real trusted time-zero fixture state; no NPC planner receives
operator-wide information. No global stock estimate is used as courier intent.
"""
from __future__ import annotations

import pytest

from carlos_sim import SQLiteEventStore
from carlos_sim.supply_diagnostics import audit_courier
from play_physical_supply import seed_physical_supply, WORLD


@pytest.mark.parametrize("flag", [None, 0, 1, "yes", [], {}])
def test_courier_diagnostics_require_explicit_boolean_engine_flag(tmp_path, flag):
    with SQLiteEventStore(tmp_path / "invalid-flag.sqlite") as db:
        seed_physical_supply(db, initial_market_food=3)
        with pytest.raises(ValueError, match="boolean"):
            audit_courier(db.load(WORLD), "huda", supply_enabled=flag)


def test_disabled_engine_is_not_misreported_as_an_empty_well(tmp_path):
    with SQLiteEventStore(tmp_path / "courier-flag-off.sqlite") as db:
        seed_physical_supply(db, water=2, initial_market_food=3)
        state = db.load(WORLD)
        previous = state.to_dict()
        report = audit_courier(state, "huda", supply_enabled=False)
        assert report["next_action"] is None
        assert report["blocked_reasons"] == ("engine_supply_flag_disabled",)
        assert report["local_source_quantity_known"] == 2
        assert report["expected_pickup_resource"] == "water"
        assert state.to_dict() == previous


def test_enabled_engine_sees_real_water_pickup_not_generated_inventory(tmp_path):
    with SQLiteEventStore(tmp_path / "courier-flag-on.sqlite") as db:
        seed_physical_supply(db, water=2, initial_market_food=3)
        state = db.load(WORLD)
        before = state.to_dict()
        report = audit_courier(state, "huda", supply_enabled=True)
        assert report["next_action"] == "SupplyCargoPicked"
        assert report["local_source_quantity_known"] == 2
        assert report["blocked_reasons"] == ()
        assert db.verify(WORLD).to_dict() == before
        assert state.to_dict() == before


def test_zero_water_allows_empty_travel_but_not_fake_water_pickup(tmp_path):
    with SQLiteEventStore(tmp_path / "courier-well-empty.sqlite") as db:
        seed_physical_supply(db, water=0, initial_market_food=3)
        state = db.load(WORLD)
        audit = audit_courier(state, "huda", supply_enabled=True)
        assert audit["local_source_quantity_known"] == 0
        assert audit["expected_pickup_resource"] == "water"
        assert audit["next_action"] != "SupplyCargoPicked"
        assert state.resources["well"]["water"] == 0


def test_nonexistent_courier_is_rejected_not_a_virtual_worker(tmp_path):
    with SQLiteEventStore(tmp_path / "no-fictional-worker.sqlite") as db:
        seed_physical_supply(db, initial_market_food=3)
        with pytest.raises(ValueError, match="actual configured"):
            audit_courier(db.load(WORLD), "invented_person", supply_enabled=True)
