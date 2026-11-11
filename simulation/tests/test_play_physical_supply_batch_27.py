"""PLAY-27 adversarial physical supply: no material can teleport."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine, apply_event
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import AdvanceLimitExceeded

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scenarios" / "test_village"))
from play_physical_supply import (
    DAY, PERIOD, TARGET, WORLD, seed_physical_supply,
    audit_physical_supply, run_physical_supply,
)


def begin(path, **options):
    db = SQLiteEventStore(path)
    try:
        seed_physical_supply(db, **options)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        engine = LivingWorldEngine(
            db, clock, supply_enabled=True, agriculture_enabled=True,
            economic_enabled=True, economy_only_enabled=True,
            consumption_enabled=True,
        )
        return db, clock, engine
    except Exception:
        db.close()
        raise


def tick(db, engine, seconds, name):
    return engine.advance(WORLD, seconds=seconds, command_id=name,
                          expected_revision=db.load(WORLD).revision)


def test_registered_four_sites_are_truly_separated_with_known_finite_stock(tmp_path):
    db, clock, engine = begin(tmp_path / "four.sqlite")
    try:
        state = db.load(WORLD)
        assert state.schema_version == 45 and state.rules_version == 62
        assert len(state.npcs) == 7
        assert set(["farm", "well", "bakery", "market"]).issubset(state.locations)
        assert state.entities["nora"]["location_id"] == "farm"
        assert state.entities["basim"]["location_id"] == "bakery"
        assert state.entities["salma"]["location_id"] == "market"
        assert state.entities["huda"]["location_id"] == "well"
        assert state.resources["well"]["water"] == 2
        assert state.resources["farm"]["water"] == 0
        assert state.resources["bakery"]["grain"] == 0
        assert state.resources["market"]["food"] == 0
        assert len(state.routes) == 3
        rec = state.supply_circuits["huda"]
        assert rec["period_seconds"] == PERIOD
        assert rec["index"] == 0 and rec["rounds"] == 0
        audit_physical_supply(state, seed=1, water=2, buyer_copper=2)
        assert db.verify(WORLD).to_dict() == state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_courier_carries_water_through_real_fifty_second_road(tmp_path):
    db, clock, engine = begin(tmp_path / "first.sqlite")
    try:
        s = tick(db, engine, 49, "before-arrival").state
        assert s.time == 49
        assert s.entities["huda"]["location_id"] == "well"
        assert s.resources["huda"]["water"] == 1
        assert s.resources["well"]["water"] == 1
        assert s.resources["farm"]["water"] == 0
        assert s.farm_plots["farm"]["status"] == "idle"
        assert any(t["due"] == 50 and t["status"] == "traveling"
                   for t in s.travels.values())
        assert db.verify(WORLD).to_dict() == s.to_dict()
        arrived = tick(db, engine, 1, "arrival").state
        assert arrived.entities["huda"]["location_id"] == "farm"
        assert arrived.resources["huda"]["water"] == 0
        assert arrived.resources["farm"]["water"] == 1
        assert arrived.resources["well"]["water"] == 1
        # Only now may the physically present farmer spend 60s planting.
        assert any(j["recipe_id"] == "seed-planting" and j["started_at"] == 50
                   for j in arrived.production_jobs.values())
        assert db.verify(WORLD).to_dict() == arrived.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_grain_waits_at_farm_then_is_carried_to_bakery_before_baking(tmp_path):
    db, clock, engine = begin(tmp_path / "grain.sqlite")
    try:
        # First crop is ready on day 1 around 86,510; courier tour
        # at 86,400 arrives before the crop is ready. Pickup is next tour.
        state = tick(db, engine, DAY + 200, "day-one").state
        assert state.farm_plots["farm"]["matured"] == 1
        assert state.resources["bakery"]["grain"] == 0
        if state.resources["farm"]["grain"] != 1:
            import json
            snap = state.to_dict()
            pytest.fail("PLAY27_FARM_DIAGNOSTIC=" + json.dumps({
                "farm": snap["resources"]["farm"],
                "plot": snap["farm_plots"]["farm"],
                "jobs": snap["production_jobs"],
                "courier": snap["supply_circuits"]["huda"],
                "huda": snap["npcs"]["huda"],
                "travels": list(snap["travels"].values())[-8:],
            }, sort_keys=True))
        assert not any(j["recipe_id"] == "grain-to-bread"
                       for j in state.production_jobs.values())
        assert db.verify(WORLD).to_dict() == state.to_dict()
        before = tick(db, engine, PERIOD - 200 + 49, "before-grain").state
        # courier arrived at farm t=108050 and picked up grain; bakery
        # cannot receive it until actual 60s travel is complete.
        assert before.time == DAY + PERIOD + 49
        assert before.resources["bakery"]["grain"] == 0
        assert before.resources["huda"]["grain"] == 0  # farm arrival still pending
        after = tick(db, engine, 61, "real-delivery").state
        assert after.resources["huda"]["grain"] == 0
        assert any(j["recipe_id"] == "grain-to-bread" and j["started_at"] >= DAY + PERIOD
                   for j in after.production_jobs.values())
        assert db.verify(WORLD).to_dict() == after.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("opts,grown,harvests,bakes", [
    ({}, 2, 2, 2),
    ({"water": 1}, 1, 1, 1),
    ({"water": 0}, 0, 0, 0),
    ({"seed": 0}, 0, 0, 0),
    ({"courier": False}, 0, 0, 0),
    ({"hoe": 0}, 0, 0, 0),
    ({"sickle": 0}, 1, 0, 0),
])
def test_seven_characters_three_days_and_reality_counterfactuals(
        tmp_path, opts, grown, harvests, bakes):
    result = run_physical_supply(tmp_path / "trial.sqlite", **opts)
    stats = result["private_test_audit_only"]
    assert result["logical_seconds"] > 3 * DAY
    assert result["verified_replay"]
    assert stats["npcs"] == 7
    assert stats["grown"] == grown, __import__("json").dumps(stats, sort_keys=True)
    assert stats["harvests"] == harvests
    assert stats["bakes"] == bakes, __import__("json").dumps(stats, sort_keys=True)
    assert stats["copper"] == 12
    assert stats["player_issued_courier_orders"] == 0
    if opts == {}:
        assert stats["trades"] == 1
        assert stats["deliveries"] >= 6
        assert stats["well_water"] == 0
        assert stats["max_hunger"] < 100


def test_real_metabolism_exposes_unsustainable_personal_needs(tmp_path):
    result = run_physical_supply(tmp_path / "hungry.sqlite",
                                 metabolism=True)
    stats = result["private_test_audit_only"]
    assert result["metabolism_enabled"]
    assert stats["max_hunger"] == 100
    assert stats["max_fatigue"] == 100
    assert stats["grown"] <= 2
    assert stats["bakes"] <= 2
    # No fictitious hunger rescue, no instantaneous shipments.
    assert stats["copper"] == 12


def test_cargo_permission_cannot_be_forged_or_replayed(tmp_path):
    db, clock, engine = begin(tmp_path / "guards.sqlite")
    try:
        before = db.load(WORLD)
        e = DomainEvent("SupplyCargoPicked", "huda", "forged", 0,
                        {"courier_id": "huda", "resource": "water"})
        with pytest.raises(ValueError):
            apply_event(before, e)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "unauthorized", before.revision, [e])
        assert db.verify(WORLD).to_dict() == before.to_dict()
        first = tick(db, engine, 49, "first").state
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "double-pick", first.revision, [DomainEvent(
                "SupplyCargoPicked", "huda", "double", first.time,
                {"courier_id": "huda", "resource": "water"},
            )], supply_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "remote-deliver", first.revision, [DomainEvent(
                "SupplyCargoDelivered", "huda", "illegal", first.time,
                {"courier_id": "huda", "resource": "water"},
            )], supply_authorized=True)
        assert db.verify(WORLD).to_dict() == first.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_wrong_inventory_and_circuit_not_interchangeable(tmp_path):
    db, clock, engine = begin(tmp_path / "wrong.sqlite")
    try:
        first = tick(db, engine, 49, "first").state
        for resource in ("grain", "food"):
            e = DomainEvent("SupplyCargoDelivered", "huda", "forged",
                            first.time,
                            {"courier_id": "huda", "resource": resource})
            with pytest.raises(ValueError):
                apply_event(first, e, supply_authorized=True)
        assert db.verify(WORLD).to_dict() == first.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_small_event_budget_rolls_back_cargo_and_clock(tmp_path):
    db, clock, engine = begin(tmp_path / "budget.sqlite")
    try:
        before = db.load(WORLD).to_dict()
        limited = LivingWorldEngine(db, clock,
                                    economic_enabled=True, agriculture_enabled=True,
                                    supply_enabled=True, economy_only_enabled=True,
                                    max_events_per_advance=1)
        with pytest.raises(AdvanceLimitExceeded):
            tick(db, limited, 50, "over-budget")
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before
    finally:
        clock.close_session(WORLD)
        db.close()


def test_old_modes_have_no_implicit_cargo_actions(tmp_path):
    db, clock, engine = begin(tmp_path / "off.sqlite")
    try:
        with pytest.raises(ValueError):
            LivingWorldEngine(db, clock, supply_enabled=True,
                              agriculture_enabled=False, economic_enabled=True)
        with pytest.raises(ValueError):
            LivingWorldEngine(db, clock, supply_enabled=1, economic_enabled=True,
                              agriculture_enabled=True)
        legacy = LivingWorldEngine(db, clock, economic_enabled=True,
                                   agriculture_enabled=True, economy_only_enabled=True)
        state = tick(db, legacy, 100, "opted-out").state
        assert state.supply_circuits["huda"]["loads"] == 0
        assert state.resources["well"]["water"] == 2
        assert state.resources["farm"]["water"] == 0
        assert state.travels == {}
        assert db.verify(WORLD).to_dict() == state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_two_real_runs_match_byte_for_byte_and_restart(tmp_path):
    states = []
    for name in ("A", "B"):
        db, clock, engine = begin(tmp_path / (name + ".sqlite"))
        try:
            s = tick(db, engine, DAY + 1500, "day1").state
            s = tick(db, engine, DAY + 1500, "day2").state
            states.append(s.to_dict())
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == s.to_dict()
        finally:
            clock.close_session(WORLD)
            db.close()
    assert states[0] == states[1]
    with SQLiteEventStore(tmp_path / "A.sqlite") as db:
        assert db.verify(WORLD).to_dict() == states[0]
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            e = LivingWorldEngine(db, clock, economic_enabled=True,
                                  agriculture_enabled=True, supply_enabled=True,
                                  economy_only_enabled=True)
            with pytest.raises(DuplicateCommand):
                e.advance(WORLD, seconds=1, command_id="day2",
                          expected_revision=db.load(WORLD).revision)
            with pytest.raises(RevisionConflict):
                e.advance(WORLD, seconds=1, command_id="bad-rev",
                          expected_revision=states[0]["revision"] - 1)
        finally:
            clock.close_session(WORLD)


def test_hungry_courier_cannot_eat_consigned_customer_food(tmp_path):
    outcome = run_physical_supply(tmp_path / "honest-courier.sqlite",
                                  courier_hunger=80)
    stats = outcome["private_test_audit_only"]
    assert stats["bakes"] == 2
    assert stats["trades"] == 1
    assert stats["deliveries"] >= 6
    assert stats["food_equivalent"] == stats["grown"] == 2
    assert outcome["verified_replay"]
