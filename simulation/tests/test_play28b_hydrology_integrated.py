"""PLAY-28B: real event-sourced, active-session water source and measured rain.

This is an isolated integration branch: no weather generator or magic supply.
"""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

# Both the isolated workflow and the inherited full-suite runner import this
# physical-world scenario; avoid depending on runner-specific PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scenarios" / "test_village"))

from carlos_sim import (SQLiteEventStore, TimeEngine, LivingWorldEngine,
                        DomainEvent, WorldState, apply_event)
from carlos_sim.store import InvalidEvent, UnsupportedVersion, RevisionConflict
from carlos_sim.hydrology import FiniteWaterService
from play_physical_supply import WORLD, seed_physical_supply, audit_physical_supply


def source_event(*, capacity=3):
    return DomainEvent("WaterSourceConfigured", None, "physical source bootstrap",
                       0, {"site_id": "well", "capacity": capacity})


def rain_event(time, *, units=1, ident="gauge-1", actor=None):
    return DomainEvent("RainWaterRecorded", actor,
                       "observed finite rain at the well", time,
                       {"source_id": "well", "observation_id": ident,
                        "units": units})


def setup_water(db, *, capacity=3):
    seed_physical_supply(db)
    previous = db.load(WORLD)
    return db.append(WORLD, "hydrology-time-zero", previous.revision,
                     [source_event(capacity=capacity)], bootstrap=True)


def session(db):
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    return clock, FiniteWaterService(db, clock)


def test_source_config_is_time_zero_only_and_replayable(tmp_path):
    with SQLiteEventStore(tmp_path / "site.sqlite") as db:
        initial = setup_water(db)
        assert (initial.schema_version, initial.rules_version) == (45, 63)
        assert initial.hydrology_sources["well"]["capacity"] == 3
        assert initial.hydrology_sources["well"]["initial"] == 2
        assert db.verify(WORLD).to_dict() == initial.to_dict()
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "repeat-source", initial.revision,
                      [source_event()], bootstrap=True)
        assert db.load(WORLD).to_dict() == initial.to_dict()


def test_drought_does_not_create_free_water_through_real_time_advances(tmp_path):
    with SQLiteEventStore(tmp_path / "dry.sqlite") as db:
        setup_water(db)
        clock, svc = session(db)
        for day in range(3):
            before = db.load(WORLD)
            after = clock.advance(WORLD, seconds=86400, command_id=f"dry-{day}",
                                  expected_revision=before.revision).state
            assert after.resources["well"]["water"] == 2
            assert after.hydrology_sources["well"]["received_total"] == 0
            audit_physical_supply(after, seed=1, water=2, buyer_copper=2)
        assert db.verify(WORLD).to_dict() == after.to_dict()


def test_measured_rain_uses_dedicated_authority_and_updates_the_real_well(tmp_path):
    with SQLiteEventStore(tmp_path / "rain.sqlite") as db:
        setup_water(db)
        clock, svc = session(db)
        old = db.load(WORLD)
        clock.advance(WORLD, seconds=300, command_id="quarter-hour",
                      expected_revision=old.revision)
        before = db.load(WORLD)
        measured = svc.record(WORLD, "well", "real-gauge-1", 1,
                              command_id="rain:1", expected_revision=before.revision)
        state = measured.state
        assert state.time == 300
        assert state.resources["well"]["water"] == 3
        assert state.hydrology_sources["well"]["received_total"] == 1
        assert state.hydrology_sources["well"]["observations"]["real-gauge-1"] == {
            "units": 1, "at": 300}
        audit_physical_supply(state, seed=1, water=3, buyer_copper=2)
        assert db.verify(WORLD).to_dict() == state.to_dict()
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()


@pytest.mark.parametrize("amount", [0, -1, True, False, 1.5, "1", 1001, None])
def test_invalid_rain_units_never_mutate_saved_resources(tmp_path, amount):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        setup_water(db)
        clock, svc = session(db)
        before = db.load(WORLD)
        with pytest.raises(InvalidEvent):
            svc.record(WORLD, "well", "invalid-units", amount,
                       command_id="rain-invalid", expected_revision=before.revision)
        assert db.load(WORLD).to_dict() == before.to_dict()


def test_overflow_duplicate_and_unsupported_site_rejected_atomically(tmp_path):
    with SQLiteEventStore(tmp_path / "overflow.sqlite") as db:
        setup_water(db)
        clock, svc = session(db)
        previous = db.load(WORLD)
        for site, ident, units in (("well", "over-capacity", 2),
                                   ("market", "wrong-site", 1)):
            with pytest.raises(InvalidEvent):
                svc.record(WORLD, site, ident, units, command_id=f"reject:{ident}",
                           expected_revision=previous.revision)
        good = svc.record(WORLD, "well", "real-rain", 1,
                          command_id="accept-rain", expected_revision=previous.revision).state
        assert good.resources["well"]["water"] == 3
        with pytest.raises(InvalidEvent):
            svc.record(WORLD, "well", "real-rain", 1,
                       command_id="repeat-observation", expected_revision=good.revision)
        with pytest.raises(InvalidEvent):
            svc.record(WORLD, "well", "different-gauge", 1,
                       command_id="overflow", expected_revision=good.revision)
        assert db.load(WORLD).to_dict() == good.to_dict()


def test_untrusted_forgery_actor_and_mismatched_time_fail_without_damage(tmp_path):
    with SQLiteEventStore(tmp_path / "forged.sqlite") as db:
        setup_water(db)
        clock, svc = session(db)
        initial = db.load(WORLD)
        event = rain_event(initial.time)
        with pytest.raises(InvalidEvent, match="hydrology authority"):
            db.append(WORLD, "plain-rain", initial.revision, [event])
        with pytest.raises(ValueError, match="authority"):
            apply_event(initial, event)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-by-player", initial.revision,
                      [rain_event(initial.time, actor="carlos")],
                      hydrology_authorized=True)
        with pytest.raises(InvalidEvent, match="ordinary event"):
            db.append(WORLD, "future-rain", initial.revision,
                      [rain_event(initial.time + 1)], hydrology_authorized=True)
        with pytest.raises(InvalidEvent, match="unsupported resource source"):
            db.append(WORLD, "unbounded-generic-resource", initial.revision, [
                DomainEvent("ResourceChanged", "carlos", "cannot create water", 0,
                            {"owner_id": "well", "resource": "water",
                             "previous": 2, "current": 3, "source": "rain"})
            ])
        assert db.load(WORLD).to_dict() == initial.to_dict()


def test_runtime_rain_cannot_be_hidden_in_privileged_bootstrap(tmp_path):
    """A rain receipt is never a free time-zero initialization allowance."""
    with SQLiteEventStore(tmp_path / "rain-not-bootstrap.sqlite") as db:
        setup_water(db)
        clock, service = session(db)
        before = db.load(WORLD)
        with pytest.raises(InvalidEvent, match="observation authority"):
            db.append(WORLD, "malicious-rain-bootstrap", before.revision,
                      [rain_event(0)], hydrology_authorized=True,
                      bootstrap=True)
        assert db.load(WORLD).to_dict() == before.to_dict()
        assert db.verify(WORLD).to_dict() == before.to_dict()


def test_paused_clock_stale_revision_and_snapshot_recovery(tmp_path):
    file = tmp_path / "resume.sqlite"
    with SQLiteEventStore(file) as db:
        setup_water(db)
        clock, svc = session(db)
        before = db.load(WORLD)
        saved = svc.record(WORLD, "well", "one-off", 1,
                           command_id="rain-provenance", expected_revision=before.revision).state
        with pytest.raises(RevisionConflict):
            svc.record(WORLD, "well", "stale", 1,
                       command_id="stale-rain", expected_revision=before.revision)
        db.snapshot(WORLD)
        clock.close_session(WORLD)
        with pytest.raises(PermissionError):
            svc.record(WORLD, "well", "paused", 1,
                       command_id="paused-rain", expected_revision=saved.revision)
    with SQLiteEventStore(file) as db:
        assert db.verify(WORLD).to_dict() == saved.to_dict()
        assert db.load(WORLD).hydrology_sources["well"]["received_total"] == 1


def test_snapshot_corruption_and_previous_version_are_rejected(tmp_path):
    with SQLiteEventStore(tmp_path / "version.sqlite") as db:
        setup_water(db)
        correct = db.load(WORLD)
        altered = correct.to_dict()
        altered["hydrology_sources"]["well"]["received_total"] = 15
        with pytest.raises(ValueError, match="rain receipts"):
            WorldState.from_dict(altered)
        db.db.execute("UPDATE worlds SET schema_version=36, rules_version=48 WHERE id=?",
                      (WORLD,))
        with pytest.raises(UnsupportedVersion):
            db.load(WORLD)
        db.db.execute("UPDATE worlds SET schema_version=41, rules_version=56 WHERE id=?",
                      (WORLD,))
        with pytest.raises(UnsupportedVersion):
            db.verify(WORLD)


def test_rain_refills_well_only_then_existing_courier_moves_real_water(tmp_path):
    with SQLiteEventStore(tmp_path / "transport.sqlite") as db:
        setup_water(db)
        clock, svc = session(db)
        before = db.load(WORLD)
        clock.advance(WORLD, seconds=600, command_id="arrival-to-well",
                      expected_revision=before.revision)
        at = db.load(WORLD)
        rained = svc.record(WORLD, "well", "rain-before-route", 1,
                            command_id="one-measured-rain",
                            expected_revision=at.revision).state
        assert rained.resources["farm"]["water"] == 0
        assert rained.resources["well"]["water"] == 3
        engine = LivingWorldEngine(db, clock, economic_enabled=True,
                                   agriculture_enabled=True, supply_enabled=True,
                                   economy_only_enabled=True)
        simulated = engine.advance(WORLD, seconds=1800, command_id="courier-route",
                                   expected_revision=rained.revision).state
        assert simulated.time == 2400
        assert simulated.resources["well"]["water"] < 3
        assert simulated.farm_plots["farm"]["started"] >= 1
        assert db.verify(WORLD).to_dict() == simulated.to_dict()
        audit_physical_supply(simulated, seed=1, water=3, buyer_copper=2)
