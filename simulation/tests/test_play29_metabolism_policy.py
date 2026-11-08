"""PLAY-29: frozen per-world hunger-clock opt-in, never an engine default."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scenarios" / "test_village"))

from carlos_sim import SQLiteEventStore, TimeEngine, DomainEvent, WorldState
from carlos_sim.store import InvalidEvent
from carlos_sim.survival import HUNGER_SECONDS_PER_POINT
from play_physical_supply import WORLD, seed_physical_supply


def config(rate, *, at=0, actor=None):
    return DomainEvent("MetabolismPolicyConfigured", actor,
                       "trusted experimental initial metabolism", at,
                       {"hunger_seconds_per_point": rate})


def create(db, rate=None):
    seed_physical_supply(db, personal_food=18)
    s = db.load(WORLD)
    if rate is not None:
        s = db.append(WORLD, "metabolism:configuration", s.revision,
                      [config(rate)], bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    return clock, s


def tick(db, seconds, name):
    s = db.load(WORLD)
    return db.append(
        WORLD, name, s.revision,
        [DomainEvent("TimeAdvanced", None, "explicit simulated passage",
                     s.time + seconds, {"from": s.time, "to": s.time + seconds})],
        clock_authorized=True, survival_authorized=True)


@pytest.mark.parametrize("period,hunger_after", [(None, 32), (300, 32), (3600, 21)])
def test_physical_3600_seconds_and_real_owned_food_without_mint(tmp_path, period, hunger_after):
    with SQLiteEventStore(tmp_path / "world.sqlite") as db:
        clock, baseline = create(db, period)
        assert baseline.metabolism_policy == (
            {} if period is None else {"hunger_seconds_per_point": period})
        assert HUNGER_SECONDS_PER_POINT == 300
        initial = db.load(WORLD)
        after = tick(db, 3600, "tick-3600")
        assert after.npcs["nora"]["needs"]["hunger"] == hunger_after
        assert after.npcs["nora"]["needs"]["fatigue"] == 11
        assert sum(after.resources[p]["food"] for p in after.npcs) == 126
        assert after.consumptions == {}
        assert after.schema_version == 39 and after.rules_version == 51
        assert db.verify(WORLD).to_dict() == after.to_dict()
        assert initial.time == 0


def test_split_steps_and_restart_preserve_configured_rate(tmp_path):
    path = tmp_path / "replay.sqlite"
    with SQLiteEventStore(path) as db:
        clock, before = create(db, 3600)
        for n, seconds in enumerate((3599, 1, 3600)):
            result = tick(db, seconds, f"elapsed:{n}")
            assert db.verify(WORLD).to_dict() == result.to_dict()
        assert result.npcs["nora"]["needs"]["hunger"] == 22
        assert result.survival_progress["nora"]["hunger_seconds"] == 0
        db.snapshot(WORLD)
    with SQLiteEventStore(path) as db:
        after = db.verify(WORLD)
        assert after.metabolism_policy["hunger_seconds_per_point"] == 3600
        assert after.npcs["nora"]["needs"]["hunger"] == 22
        assert after.to_dict() == result.to_dict()


@pytest.mark.parametrize("rate", [True, False, -1, 0, 299, 301, 7200, None, 3600.0, "3600"])
def test_bad_calibration_never_enters_history(tmp_path, rate):
    with SQLiteEventStore(tmp_path / "bad.sqlite") as db:
        clock, initial = create(db)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "bad-rate", initial.revision,
                      [config(rate)], bootstrap=True)
        assert db.verify(WORLD).to_dict() == initial.to_dict()


def test_ordinary_event_and_player_cannot_change_hunger_rate(tmp_path):
    with SQLiteEventStore(tmp_path / "guard.sqlite") as db:
        clock, initial = create(db)
        with pytest.raises(InvalidEvent, match="trusted time-zero"):
            db.append(WORLD, "untrusted-rate", initial.revision,
                      [config(3600)])
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "forged-player", initial.revision,
                      [config(3600, actor="carlos")], bootstrap=True)
        assert db.load(WORLD).metabolism_policy == {}


def test_rate_is_single_assignment_not_mutable_midgame(tmp_path):
    with SQLiteEventStore(tmp_path / "guard.sqlite") as db:
        clock, initial = create(db, 3600)
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "second-policy", initial.revision,
                      [config(300)], bootstrap=True)
        one = tick(db, 1, "one-second")
        with pytest.raises(InvalidEvent):
            db.append(WORLD, "late-policy", one.revision,
                      [config(300, at=1)], bootstrap=True)
        assert db.verify(WORLD).to_dict() == one.to_dict()


def test_world_snapshot_rejects_forged_rate_and_residuals(tmp_path):
    with SQLiteEventStore(tmp_path / "strict.sqlite") as db:
        clock, baseline = create(db, 3600)
        sample = tick(db, 3599, "near-boundary").to_dict()
        assert sample["survival_progress"]["nora"]["hunger_seconds"] == 3599
        assert WorldState.from_dict(sample).to_dict() == sample
        for invalid in ({"hunger_seconds_per_point": 300.0},
                        {"hunger_seconds_per_point": True},
                        {"hunger_seconds_per_point": 5000},
                        {"hunger_seconds_per_point": 3600, "free_food": 1}):
            forged = {**sample, "metabolism_policy": invalid}
            with pytest.raises(ValueError):
                WorldState.from_dict(forged)
        forged = {**sample, "metabolism_policy": {"hunger_seconds_per_point": 300}}
        with pytest.raises(ValueError, match="residuals"):
            WorldState.from_dict(forged)


def test_default_clock_does_not_activate_survival_implicitly(tmp_path):
    with SQLiteEventStore(tmp_path / "off.sqlite") as db:
        clock, initial = create(db, 3600)
        after = clock.advance(WORLD, seconds=3600, command_id="idle",
                              expected_revision=initial.revision).state
        assert after.npcs["nora"]["needs"]["hunger"] == 20
        assert after.survival_progress == {}
        assert db.verify(WORLD).to_dict() == after.to_dict()
