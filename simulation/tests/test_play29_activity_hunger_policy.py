"""PLAY-29: real completed NPC actions obey an immutable, positive-cost policy."""
from __future__ import annotations

import pytest
from carlos_sim import DomainEvent, WorldState, SQLiteEventStore, TimeEngine, LivingWorldEngine
from carlos_sim.store import InvalidEvent
from test_living_world import build


def make_world(db, *, rate=None, cost=None, fatigue=5):
    build(db, npcs=("nora",), fatigue=fatigue)
    initial = db.load("test")
    if rate is not None:
        payload = {"hunger_seconds_per_point": rate}
        if cost is not None:
            payload["activity_hunger_percent"] = cost
        initial = db.append("test", "configure-once", initial.revision,
            [DomainEvent("MetabolismPolicyConfigured", None, "trusted one-time setup",
                         0, payload)], bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session("test")
    return clock, initial


def advance_real_action(db, clock, seconds=180):
    initial = db.load("test")
    after = LivingWorldEngine(db, clock, survival_enabled=False).advance(
        "test", seconds=seconds, command_id="actual-npc-actions",
        expected_revision=initial.revision).state
    assert db.verify("test").to_dict() == after.to_dict()
    return after


@pytest.mark.parametrize("rate,cost,expected", [
    (None, None, 30), (300, 100, 30), (3600, None, 30),
    (3600, 100, 30), (3600, 20, 22), (300, 20, 22),
])
def test_real_work_charge_preserves_time_tool_and_fatigue(tmp_path, rate, cost, expected):
    with SQLiteEventStore(tmp_path / "w.sqlite") as db:
        clock, initial = make_world(db, rate=rate, cost=cost)
        result = advance_real_action(db, clock)
        assert result.time == 180
        assert result.schema_version == 45 and result.rules_version == 63
        assert result.npcs["nora"]["needs"]["hunger"] == expected
        assert result.npcs["nora"]["needs"]["fatigue"] == 20
        assert result.resources["nora"]["labor_units"] == 1
        assert result.actions["auto:nora:0"]["status"] == "completed"
        assert result.actions["auto:nora:0"]["result"]["needs"]["hunger"] == (20, expected)
        assert result.resources["nora"].get("food", 0) == 0
        assert result.consumptions == {}


@pytest.mark.parametrize("cost,expected", [(None, 25), (100, 25), (20, 21)])
def test_real_rest_remains_an_actual_hunger_and_fatigue_cost(tmp_path, cost, expected):
    with SQLiteEventStore(tmp_path / "rest.sqlite") as db:
        clock, _ = make_world(db, rate=3600, cost=cost, fatigue=95)
        after = advance_real_action(db, clock, seconds=120)
        assert after.actions["auto:nora:0"]["action"] == "rest"
        assert after.npcs["nora"]["needs"]["hunger"] == expected
        assert after.npcs["nora"]["needs"]["fatigue"] == 75


@pytest.mark.parametrize("value", [0, -1, 1, 19, 21, 101, 0.2, 20.0, True, False, None, "20"])
def test_invalid_activity_cost_is_rejected_before_persistence(tmp_path, value):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        clock, before = make_world(db)
        with pytest.raises(InvalidEvent):
            db.append("test", "attempt", before.revision,
                [DomainEvent("MetabolismPolicyConfigured", None, "unauthorized input",
                             0, {"hunger_seconds_per_point": 3600,
                                 "activity_hunger_percent": value})], bootstrap=True)
        assert db.load("test").to_dict() == before.to_dict()


def test_reject_midgame_overwrite_and_bootstrap_forgery(tmp_path):
    with SQLiteEventStore(tmp_path / "guard.sqlite") as db:
        clock, configured = make_world(db, rate=3600, cost=20)
        with pytest.raises(InvalidEvent):
            db.append("test", "double-set", configured.revision,
                [DomainEvent("MetabolismPolicyConfigured", None, "duplicate",
                             0, {"hunger_seconds_per_point": 300,
                                 "activity_hunger_percent": 100})], bootstrap=True)
        after = advance_real_action(db, clock)
        with pytest.raises(InvalidEvent):
            db.append("test", "late", after.revision,
                [DomainEvent("MetabolismPolicyConfigured", None, "late",
                             180, {"hunger_seconds_per_point": 300,
                                   "activity_hunger_percent": 100})], bootstrap=True)
        with pytest.raises(InvalidEvent):
            db.append("test", "forged-actor", after.revision,
                [DomainEvent("MetabolismPolicyConfigured", "nora", "forgery",
                             180, {"hunger_seconds_per_point": 300})], bootstrap=True)
        assert db.verify("test").to_dict() == after.to_dict()


def test_snapshot_replay_roundtrip_and_strict_policy_type(tmp_path):
    file = tmp_path / "persist.sqlite"
    with SQLiteEventStore(file) as db:
        clock, _ = make_world(db, rate=3600, cost=20)
        after = advance_real_action(db, clock)
        data = after.to_dict()
        assert data["metabolism_policy"] == {
            "hunger_seconds_per_point": 3600, "activity_hunger_percent": 20
        }
        db.snapshot("test")
        for p in ({"hunger_seconds_per_point": 3600, "activity_hunger_percent": 0},
                  {"hunger_seconds_per_point": 3600, "activity_hunger_percent": True},
                  {"hunger_seconds_per_point": 3600, "activity_hunger_percent": 20.0},
                  {"hunger_seconds_per_point": 3600, "activity_hunger_percent": 20,
                   "secret_food": 99}):
            invalid = {**data, "metabolism_policy": p}
            with pytest.raises(ValueError):
                WorldState.from_dict(invalid)
    with SQLiteEventStore(file) as db:
        assert db.verify("test").to_dict() == data
        assert db.load("test").metabolism_policy["activity_hunger_percent"] == 20


def test_legacy_defaults_untouched_when_rate_and_cost_unconfigured(tmp_path):
    with SQLiteEventStore(tmp_path / "legacy-default.sqlite") as db:
        clock, original = make_world(db)
        after = advance_real_action(db, clock)
        assert after.metabolism_policy == {}
        assert after.npcs["nora"]["needs"]["hunger"] == 30
        assert after.actions["auto:nora:0"]["result"]["needs"]["hunger"] == (20, 30)
