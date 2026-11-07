"""PLAY-25: physical finite harvest -> bakery -> local market regression gates."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from carlos_sim import LivingWorldEngine
from carlos_sim.store import (SQLiteEventStore, DuplicateCommand,
                              RevisionConflict)
from carlos_sim.time_engine import TimeEngine, AdvanceLimitExceeded
from carlos_sim.economic_autonomy import choose_local_production

HERE = Path(__file__).resolve().parents[1] / "scenarios" / "test_village"
sys.path.insert(0, str(HERE))
from play_finite_harvest import (WORLD, PEOPLE, seed_finite_field,
                                 physical_totals, run_finite_field)


def begin(path, **options):
    db = SQLiteEventStore(path)
    try:
        seed_finite_field(db, **options)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        engine = LivingWorldEngine(
            db, clock, economic_enabled=True,
            consumption_enabled=True, survival_enabled=True,
        )
        return db, clock, engine
    except BaseException:
        db.close()
        raise


def tick(db, engine, seconds, name):
    return engine.advance(
        WORLD, seconds=seconds, command_id=name,
        expected_revision=db.load(WORLD).revision,
    )


def test_farm_then_bakery_two_real_jobs_without_orders(tmp_path):
    db, clock, engine = begin(tmp_path / "basic.sqlite")
    try:
        state = db.load(WORLD)
        assert len(state.npcs) == 7
        assert state.resources["square"]["grain"] == 0
        assert physical_totals(state) == {"crop_food_equivalent": 1, "copper": 12}
        assert choose_local_production(state, "nora").recipe_id == "finite-harvest"
        assert choose_local_production(state, "basim") is None

        first = tick(db, engine, 60, "farm")
        state = first.state
        harvest = [j for j in state.production_jobs.values()
                   if j["recipe_id"] == "finite-harvest"]
        bakery = [j for j in state.production_jobs.values()
                  if j["recipe_id"] == "grain-to-bread"]
        assert len(harvest) == 1 and harvest[0]["status"] == "completed"
        assert harvest[0]["due"] == 60
        assert len(bakery) == 1 and bakery[0]["started_at"] == 60
        assert bakery[0]["status"] == "running"
        assert state.resources["square"]["crop_ready"] == 0
        assert state.resources["square"]["grain"] == 0
        assert physical_totals(state) == {"crop_food_equivalent": 1, "copper": 12}

        second = tick(db, engine, 90, "bake")
        state = second.state
        assert state.production_jobs[next(k for k, j in state.production_jobs.items()
                                         if j["recipe_id"] == "grain-to-bread")]["status"] == "completed"
        assert physical_totals(state) == {"crop_food_equivalent": 1, "copper": 12}
        third = tick(db, engine, 150, "market")
        assert third.state.time == 300
        assert len(third.state.production_jobs) == 2
        assert len(third.state.market_offers) >= 1
        assert len(third.state.market_trades) == 1
        trade = next(iter(third.state.market_trades.values()))
        assert trade["buyer_id"] == "adel"
        assert trade["total_paid"] == 2
        assert len(third.state.consumptions) >= 1
        assert physical_totals(third.state) == {"crop_food_equivalent": 1, "copper": 12}
        assert db.verify(WORLD).to_dict() == third.state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("options,harvest_expected,bake_expected", [
    ({"crop": 0}, False, False),
    ({"sickle": 0}, False, False),
    ({"farmer_site": "home"}, False, False),
    ({"farmer_shift": (200, 600)}, False, False),
    ({"farmer_shift": (0, 30)}, False, False),
    ({"baker_site": "home"}, True, False),
    ({"baker_shift": (200, 600)}, True, False),
    ({"baker_shift": (0, 60)}, True, False),
])
def test_real_constraints_prevent_miracle_harvest_or_bake(
        tmp_path, options, harvest_expected, bake_expected):
    db, clock, engine = begin(tmp_path / "blocked.sqlite", **options)
    try:
        before = physical_totals(db.load(WORLD))
        result = tick(db, engine, 150, "blocked-time")
        jobs = result.state.production_jobs.values()
        harvest = [j for j in jobs if j["recipe_id"] == "finite-harvest"]
        bake = [j for j in jobs if j["recipe_id"] == "grain-to-bread"]
        assert bool(harvest) == harvest_expected
        assert bool(bake) == bake_expected
        assert physical_totals(result.state) == before
        assert db.verify(WORLD).to_dict() == result.state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("crop,copper,sickle,expected_sale", [
    (1, 2, 1, True),
    (1, 0, 1, False),
    (0, 2, 1, False),
    (1, 2, 0, False),
])
def test_real_seven_npc_counterfactual_villages(
        tmp_path, crop, copper, sickle, expected_sale):
    data = run_finite_field(
        tmp_path / "seven.sqlite", crop=crop,
        buyer_copper=copper, sickle=sickle,
    )
    audit = data["private_test_audit_only"]
    assert data["disposable_test"] and not data["canonical_story"]
    assert data["logical_seconds"] == 300 and data["verified_replay"]
    assert audit["npcs"] == len(PEOPLE) == 7
    assert audit["player_commanded_npc_actions"] == 0
    assert audit["final_totals"] == {
        "crop_food_equivalent": crop, "copper": copper + 10,
    }
    assert (audit["harvests"] >= 1) == (crop > 0 and sickle > 0)
    assert (audit["bakes"] >= 1) == (crop > 0 and sickle > 0)
    assert bool(audit["trades"]) == expected_sale
    assert audit["buyers"] == (["adel"] if expected_sale else [])


def test_finite_multiple_harvest_lots_never_exceed_field_inventory(tmp_path):
    db, clock, engine = begin(tmp_path / "limited.sqlite", crop=2, buyer_copper=4)
    try:
        source = physical_totals(db.load(WORLD))
        for t in (60, 150, 240, 330, 420):
            state = tick(db, engine, t - db.load(WORLD).time, f"multi-{t}").state
            assert physical_totals(state) == source
            farm_jobs = [j for j in state.production_jobs.values()
                         if j["recipe_id"] == "finite-harvest"]
            bake_jobs = [j for j in state.production_jobs.values()
                         if j["recipe_id"] == "grain-to-bread"]
            assert len(farm_jobs) <= 2
            assert len(bake_jobs) <= len(farm_jobs)
            assert state.resources["square"]["crop_ready"] + len(farm_jobs) == 2
            assert len(state.market_trades) <= len(bake_jobs)
            assert db.verify(WORLD).to_dict() == state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_gate_default_off_keeps_finite_crop_untouched(tmp_path):
    db, clock, _ = begin(tmp_path / "off.sqlite")
    try:
        old = LivingWorldEngine(db, clock, consumption_enabled=True,
                                survival_enabled=True)
        state = tick(db, old, 180, "no-economic").state
        assert state.production_jobs == {}
        assert state.market_trades == {}
        assert state.resources["square"]["crop_ready"] == 1
        assert physical_totals(state) == {"crop_food_equivalent": 1, "copper": 12}
    finally:
        clock.close_session(WORLD)
        db.close()


def test_failed_event_budget_is_fully_atomic(tmp_path):
    db, clock, _ = begin(tmp_path / "rollback.sqlite")
    try:
        before = db.load(WORLD).to_dict()
        count = db.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
        limited = LivingWorldEngine(
            db, clock, economic_enabled=True,
            consumption_enabled=True, survival_enabled=True,
            max_events_per_advance=1,
        )
        with pytest.raises(AdvanceLimitExceeded):
            tick(db, limited, 60, "too-small")
        assert db.load(WORLD).to_dict() == before
        assert db.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0] == count
    finally:
        clock.close_session(WORLD)
        db.close()


def test_replay_duplicate_stale_and_reopen(tmp_path):
    path = tmp_path / "reopen.sqlite"
    db, clock, engine = begin(path)
    try:
        tick(db, engine, 60, "first")
        state = tick(db, engine, 90, "second").state
        assert db.verify(WORLD).to_dict() == state.to_dict()
        db.snapshot(WORLD)
        saved = state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == saved
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, economic_enabled=True,
                consumption_enabled=True, survival_enabled=True,
            )
            with pytest.raises(DuplicateCommand):
                engine.advance(WORLD, seconds=1, command_id="second",
                               expected_revision=db.load(WORLD).revision)
            with pytest.raises(RevisionConflict):
                engine.advance(WORLD, seconds=1, command_id="stale",
                               expected_revision=saved["revision"] - 1)
            assert db.load(WORLD).to_dict() == saved
        finally:
            clock.close_session(WORLD)


def test_identical_seeds_and_commands_produce_identical_event_state(tmp_path):
    final = []
    for name in ("left", "right"):
        db, clock, engine = begin(tmp_path / f"{name}.sqlite")
        try:
            tick(db, engine, 60, "first")
            result = tick(db, engine, 240, "second")
            final.append(result.state.to_dict())
            assert db.verify(WORLD).to_dict() == result.state.to_dict()
        finally:
            clock.close_session(WORLD)
            db.close()
    assert final[0] == final[1]


def test_no_market_never_forges_sale(tmp_path):
    data = run_finite_field(tmp_path / "no-market.sqlite", with_market=False)
    audit = data["private_test_audit_only"]
    assert audit["harvests"] >= 1 and audit["bakes"] >= 1
    assert audit["offers"] == audit["trades"] == 0
    assert audit["final_totals"]["crop_food_equivalent"] == 1
