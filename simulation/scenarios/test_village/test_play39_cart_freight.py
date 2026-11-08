"""PLAY-39A: quantified, physically owned cart freight with strict anti-cheat.

One courier with one real owned cart may move 1–3 units per *real* route
leg, never inspect a distant owner, mint cargo, or eat consigned food.
The previous one-parcel contract remains an entirely separate control.
"""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, InvalidEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine, WorldState
from carlos_sim.consumption import _reserved_food
from play_physical_supply import WORLD
from test_play38_multi_farm_couriers import seed_two_field_world, _conserve


def _advance(db, seconds, *, economic=False):
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    try:
        engine = LivingWorldEngine(
            db, clock, max_events_per_advance=5000,
            decision_cooldown=3600, navigation_enabled=True,
            routines_enabled=True, survival_enabled=True,
            consumption_enabled=True, supply_enabled=True,
            economic_enabled=economic, agriculture_enabled=economic,
            economy_only_enabled=economic,
        )
        before = db.load(WORLD)
        return engine.advance(WORLD, seconds=seconds,
                              command_id=f"play39a:{seconds}:{economic}",
                              expected_revision=before.revision).state
    finally:
        clock.close_session(WORLD)


def test_real_cart_moves_two_existing_water_units_on_one_real_road(tmp_path):
    with SQLiteEventStore(tmp_path / "water-cart.sqlite") as db:
        seed_two_field_world(db, east_cart_capacity=3)
        before = db.verify(WORLD)
        assert before.resources["hana"]["cart"] == 1
        assert before.resources["well"]["water"] == 2
        assert before.supply_circuits["huda"].get("cargo_capacity") is None
        assert before.supply_circuits["hana"]["cargo_capacity"] == 3
        state = _advance(db, 50)
        assert state.time == 50
        assert state.resources["well"]["water"] == 0
        assert state.resources["farm_east"]["water"] == 2
        assert state.resources["hana"]["water"] == 0
        assert state.supply_circuits["hana"]["loads"] == 1
        assert state.supply_circuits["hana"]["deliveries"] == 1
        assert state.resources["hana"]["cart"] == 1
        _conserve(state)
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_cart_cannot_be_registered_without_real_vehicle_or_safe_capacity(tmp_path):
    for cap, has_cart in ((2, False), (3, False), (1.5, True),
                          (0, True), (4, True), (True, True)):
        with SQLiteEventStore(tmp_path / f"invalid-{str(cap)}-{has_cart}.sqlite") as db:
            with pytest.raises((InvalidEvent, ValueError)):
                seed_two_field_world(db, east_cart_capacity=cap, cart_owned=has_cart)
            baseline = db.verify(WORLD)
            assert "farm_east" not in baseline.locations
            assert "hana" not in baseline.supply_circuits


@pytest.mark.parametrize("count", [0, -1, 3, 4, True, 2.5, "2"])
def test_cart_rejects_invalid_or_unowned_loads_atomically(tmp_path, count):
    with SQLiteEventStore(tmp_path / "forged.sqlite") as db:
        seed_two_field_world(db, east_cart_capacity=2)
        before = db.verify(WORLD)
        e = DomainEvent(
            "SupplyCargoPicked", "hana", "unbacked or invalid pickup", 0,
            {"courier_id": "hana", "resource": "water", "quantity": count},
        )
        with pytest.raises((InvalidEvent, ValueError, TypeError)):
            db.append(WORLD, "cart-forgery", before.revision, [e],
                      supply_authorized=True)
        assert db.verify(WORLD).to_dict() == before.to_dict()


def test_legacy_courier_rejects_quantity_and_forged_cart_event(tmp_path):
    with SQLiteEventStore(tmp_path / "no-legacy-upgrade.sqlite") as db:
        seed_two_field_world(db)
        initial = db.verify(WORLD)
        assert "cargo_capacity" not in initial.supply_circuits["huda"]
        event = DomainEvent(
            "SupplyCargoPicked", "huda", "attempted silent cart upgrade", 0,
            {"courier_id": "huda", "resource": "water", "quantity": 2},
        )
        with pytest.raises((InvalidEvent, ValueError)):
            db.append(WORLD, "bad-upgrade", initial.revision, [event],
                      supply_authorized=True)
        assert db.verify(WORLD).to_dict() == initial.to_dict()


def test_cart_water_delivery_and_owner_scarcity_stay_auditable(tmp_path):
    with SQLiteEventStore(tmp_path / "actual-crop-cart.sqlite") as db:
        seed_two_field_world(db, east_cart_capacity=3)
        initial = db.verify(WORLD)
        state = _advance(db, 12000, economic=True)
        assert state.time == 12000
        assert len(state.farm_plots) == 2
        assert state.resources["hana"]["cart"] == 1
        assert state.farm_plots["farm_east"]["matured"] == 1
        assert sum(j["recipe_id"] == "east-finite-harvest"
                   and j["status"] == "completed"
                   for j in state.production_jobs.values()) == 1
        assert sum(j["recipe_id"] == "grain-to-bread"
                   and j["status"] == "completed"
                   for j in state.production_jobs.values()) >= 1
        assert state.supply_circuits["hana"]["deliveries"] >= 2
        _conserve(state)
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
        assert initial.time == 0


def test_reserved_multi_unit_food_cargo_is_not_a_courier_meal():
    assert _reserved_food({"hana": {
        "carry": {"source": "bakery", "destination": "market",
                  "resource": "food", "quantity": 3}
    }}, "hana") == 3
    assert _reserved_food({"huda": {
        "carry": {"source": "bakery", "destination": "market",
                  "resource": "food"}
    }}, "huda") == 1
    assert _reserved_food({}, "hana") == 0


def test_corrupt_cart_quantity_is_rejected_by_world_state(tmp_path):
    with SQLiteEventStore(tmp_path / "cart-validation.sqlite") as db:
        seed_two_field_world(db, east_cart_capacity=3)
        state = _advance(db, 20)
        assert state.supply_circuits["hana"]["carry"] is not None
        valid = state.to_dict()
        tampered = state.to_dict()
        tampered["supply_circuits"]["hana"]["carry"]["quantity"] = 4
        with pytest.raises(ValueError):
            WorldState.from_dict(tampered)
        assert WorldState.from_dict(valid).to_dict() == valid
