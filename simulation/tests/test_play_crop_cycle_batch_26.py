"""PLAY-26: seeded crop growth, real labor, finite water and multiday replay."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, apply_event
from carlos_sim.store import SQLiteEventStore, InvalidEvent, DuplicateCommand, RevisionConflict
from carlos_sim.time_engine import TimeEngine, AdvanceLimitExceeded
from carlos_sim.economic_autonomy import choose_local_production
from carlos_sim.agriculture import choose_local_growth

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scenarios" / "test_village"))
from play_crop_cycle import (DAY, WORLD, setup_planted_world, conserved_audit,
                             run_planted_village)


def begin(path, **options):
    db = SQLiteEventStore(path)
    try:
        setup_planted_world(db, **options)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        engine = LivingWorldEngine(
            db, clock, economic_enabled=True, agriculture_enabled=True,
            economy_only_enabled=True, consumption_enabled=True,
        )
        return db, clock, engine
    except BaseException:
        db.close()
        raise


def wait(db, engine, seconds, command):
    return engine.advance(
        WORLD, seconds=seconds, command_id=command,
        expected_revision=db.load(WORLD).revision,
    )


def test_seed_to_real_planting_job_then_exact_day_growth(tmp_path):
    db, clock, engine = begin(tmp_path / "first.sqlite")
    try:
        initial = db.load(WORLD)
        assert initial.schema_version == 42 and initial.rules_version == 57
        assert initial.resources["square"]["crop_ready"] == 0
        assert initial.resources["square"]["grain"] == 0
        assert choose_local_production(initial, "nora", agriculture_enabled=True).recipe_id == "seed-planting"
        assert choose_local_production(initial, "nora") is None
        assert choose_local_growth(initial, "square") is False

        first = wait(db, engine, 60, "plant")
        crop = first.state.farm_plots["square"]
        assert crop["status"] == "growing"
        assert crop["started"] == 1 and crop["matured"] == 0
        assert crop["due"] == DAY + 60
        assert first.state.resources["square"]["water"] == 1
        assert first.state.resources["square"]["crop_ready"] == 0
        assert first.state.resources["square"]["seed"] == 0
        assert any(j["recipe_id"] == "seed-planting" and j["status"] == "completed"
                   for j in first.state.production_jobs.values())
        assert db.verify(WORLD).to_dict() == first.state.to_dict()

        one_second_early = wait(db, engine, DAY - 1, "not-ready")
        assert one_second_early.state.farm_plots["square"]["matured"] == 0
        assert one_second_early.state.resources["square"]["crop_ready"] == 0
        at_due = wait(db, engine, 1, "maturity")
        assert at_due.state.farm_plots["square"]["matured"] == 1
        # Nora immediately chooses to harvest the physically ripe crop.
        assert any(j["recipe_id"] == "finite-harvest" and j["started_at"] == DAY + 60
                   for j in at_due.state.production_jobs.values())
        assert at_due.state.resources["square"]["seed"] == 1
        assert db.verify(WORLD).to_dict() == at_due.state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("options,expected_planted", [
    ({"seed": 0}, False),
    ({"water": 0}, False),
    ({"hoe": 0}, False),
    ({"farmer_shift": (0, 30)}, False),
    ({}, True),
])
def test_finite_seed_water_tool_shift_gates(tmp_path, options, expected_planted):
    db, clock, engine = begin(tmp_path / "counter.sqlite", **options)
    try:
        state = wait(db, engine, 60, "sixty").state
        assert (state.farm_plots["square"]["status"] == "growing") == expected_planted
        assert state.resources["square"]["crop_ready"] == 0
        assert db.verify(WORLD).to_dict() == state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("options,expected_grown,expected_harvest,expected_bake", [
    ({}, 2, 2, 2),
    ({"water": 1}, 1, 1, 1),
    ({"water": 0}, 0, 0, 0),
    ({"seed": 0}, 0, 0, 0),
    ({"hoe": 0}, 0, 0, 0),
    ({"sickle": 0}, 1, 0, 0),
])
def test_seven_npc_multiple_days_and_counterfactuals(
        tmp_path, options, expected_grown, expected_harvest, expected_bake):
    world = run_planted_village(tmp_path / "seven.sqlite", **options)
    stats = world["private_test_audit_only"]
    assert world["logical_seconds"] > 2 * DAY
    assert world["verified_replay"] and world["disposable_test"]
    assert not world["canonical_story"]
    assert stats["npcs"] == 7
    assert stats["grown"] == expected_grown
    assert stats["harvests"] == expected_harvest
    assert stats["bakes"] == expected_bake
    assert stats["player_issued_npc_orders"] == 0
    assert stats["copper"] == 12
    if expected_grown == 2:
        assert stats["remaining_water"] == 0
        assert stats["trades"] == 1


def test_barren_dry_field_cannot_grow_after_first_watering(tmp_path):
    result = run_planted_village(tmp_path / "dry.sqlite", water=1)
    a = result["private_test_audit_only"]
    assert a["grown"] == a["harvests"] == 1
    assert a["plantings"] == 1
    assert a["remaining_water"] == 0 and a["remaining_seed"] == 1


def test_full_event_budget_rollback_keeps_seed_water_clock_unchanged(tmp_path):
    db, clock, _ = begin(tmp_path / "budget.sqlite")
    try:
        before = db.load(WORLD).to_dict()
        count = db.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
        small = LivingWorldEngine(
            db, clock, economic_enabled=True, agriculture_enabled=True,
            economy_only_enabled=True, max_events_per_advance=1,
        )
        with pytest.raises(AdvanceLimitExceeded):
            wait(db, small, 60, "over-limit")
        assert db.load(WORLD).to_dict() == before
        assert db.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0] == count
    finally:
        clock.close_session(WORLD)
        db.close()


def test_unauthorized_growth_and_forged_clock_appointments_rejected(tmp_path):
    db, clock, engine = begin(tmp_path / "security.sqlite")
    try:
        first = wait(db, engine, 60, "first").state
        before = first.to_dict()
        forged = DomainEvent("CropGrowthStarted", None, "untrusted", first.time,
                             {"site_id": "square"})
        with pytest.raises((ValueError, InvalidEvent)):
            apply_event(first, forged)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged", first.revision, [forged])
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "double-water", first.revision,
                      [forged], agriculture_authorized=True)
        cancel = DomainEvent("ScheduledEventCancelled", None, "fraud", first.time,
                             {"id": "crop-growth:square:1"})
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "cancel", first.revision, [cancel])
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before
    finally:
        clock.close_session(WORLD)
        db.close()


def test_closed_plot_forbids_untrusted_configuration_and_fake_seedling(tmp_path):
    db, clock, engine = begin(tmp_path / "plot.sqlite", seed=0)
    try:
        state = db.load(WORLD)
        event = DomainEvent("FarmPlotConfigured", None, "repeat", 0,
                            {"site_id": "square", "growth_seconds": DAY,
                             "capacity": 1})
        with pytest.raises(ValueError):
            apply_event(state, event, bootstrap=True)
        grow = DomainEvent("CropGrowthStarted", None, "forged", 0,
                           {"site_id": "square"})
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "missing-seedling", state.revision, [grow],
                      agriculture_authorized=True)
    finally:
        clock.close_session(WORLD)
        db.close()


def test_two_databases_match_every_bit_and_snapshot_reopen(tmp_path):
    files = []
    for label in ("left", "right"):
        db, clock, engine = begin(tmp_path / (label + ".sqlite"))
        try:
            wait(db, engine, 60, "start")
            state = wait(db, engine, 2 * DAY + 440, "days").state
            files.append(state.to_dict())
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
            db.close()
    assert files[0] == files[1]
    with SQLiteEventStore(tmp_path / "left.sqlite") as db:
        assert db.verify(WORLD).to_dict() == files[0]
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, economic_enabled=True,
                agriculture_enabled=True, economy_only_enabled=True,
            )
            with pytest.raises(DuplicateCommand):
                engine.advance(WORLD, seconds=1, command_id="days",
                               expected_revision=db.load(WORLD).revision)
            with pytest.raises(RevisionConflict):
                engine.advance(WORLD, seconds=1, command_id="stale",
                               expected_revision=files[0]["revision"] - 1)
            assert db.verify(WORLD).to_dict() == files[0]
        finally:
            clock.close_session(WORLD)


def test_flags_do_not_affect_legacy_opt_out_and_validate_types(tmp_path):
    db, clock, engine = begin(tmp_path / "flags.sqlite")
    try:
        for opts in (
            {"agriculture_enabled": 1, "economic_enabled": True},
            {"agriculture_enabled": True, "economic_enabled": False},
            {"economy_only_enabled": True, "economic_enabled": True},
            {"economy_only_enabled": "true", "agriculture_enabled": True,
             "economic_enabled": True},
        ):
            with pytest.raises(ValueError):
                LivingWorldEngine(db, clock, **opts)
        old = LivingWorldEngine(db, clock, economic_enabled=False)
        state = wait(db, old, 60, "legacy").state
        assert state.farm_plots["square"]["started"] == 0
        assert state.resources["square"]["seed"] == 1
        assert state.production_jobs == {}
        assert db.verify(WORLD).to_dict() == state.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_economic_endurance_omits_generic_npc_actions(tmp_path):
    db, clock, engine = begin(tmp_path / "focused.sqlite")
    try:
        state = wait(db, engine, 2 * DAY + 500, "endurance").state
        assert len(state.actions) == 0
        assert state.farm_plots["square"]["matured"] == 2
        assert all(j["npc_id"] in ("nora", "basim")
                   for j in state.production_jobs.values())
        conserved_audit(state, initial_seed=1, initial_water=2,
                        initial_copper=12)
    finally:
        clock.close_session(WORLD)
        db.close()
