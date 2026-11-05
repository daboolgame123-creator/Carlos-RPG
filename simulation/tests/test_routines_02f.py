"""02-F: real home/work commute, private routines, and hostile configuration."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, WorldState
from carlos_sim.routines import choose_routine_route
from carlos_sim.store import InvalidEvent
from test_temperament_02e import setup, ev


def scenario(db, *, configured=True, work_start=0, work_end=300, route=True):
    setup(db, configured=False, members=("basim", "nora"))
    genesis = [
        ev("LocationCreated", {"id": "smithy", "name": "Smithy"}),
    ]
    if route:
        genesis.append(ev("RouteCreated", {"id": "square-smithy", "a": "square",
                                           "b": "smithy", "seconds": 50}))
    if configured:
        genesis.append(ev("NPCRoutineConfigured", {
            "npc_id": "basim", "home_id": "square", "workplace_id": "smithy",
            "work_start": work_start, "work_end": work_end
        }))
    db.append("test", "setup-routine", db.load("test").revision, genesis,
              bootstrap=True)


def test_routine_is_opt_in_and_cannot_teleport_to_unlearned_workplace(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (20, 27)
    with SQLiteEventStore(tmp_path / "unlearned.sqlite") as db:
        scenario(db)
        original = db.load("test")
        assert choose_routine_route(original, "basim") is None
        assert choose_routine_route(original, "nora") is None
        clock = TimeEngine(db)
        clock.open_session("test")
        # Basim may locally survey before commuting, not learn a distant route
        # by being assigned an address.
        result = LivingWorldEngine(db, clock, navigation_enabled=True,
                                   routines_enabled=True).advance(
            "test", seconds=1, command_id="advance",
            expected_revision=original.revision)
        traveling = [t for t in result.state.travels.values()
                     if t["npc_id"] == "basim" and t["status"] == "traveling"]
        assert len(traveling) == 1
        assert result.state.entities["basim"]["location_id"] == "square"
        assert traveling[0]["due"] == 50
        assert db.verify("test").to_dict() == result.state.to_dict()


def test_direct_known_route_and_next_eligible_homeward_intent(tmp_path):
    with SQLiteEventStore(tmp_path / "choice.sqlite") as db:
        scenario(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        state = db.load("test")
        db.append("test", "survey", state.revision,
                  [ev("NPCNavigationSurveyed", {"npc_id": "basim"}, who="basim")],
                  movement_authorized=True)
        selected = choose_routine_route(db.load("test"), "basim")
        assert selected is not None and selected.destination == "smithy"
        assert selected.route_id == "square-smithy"
        assert choose_routine_route(db.load("test"), "nora") is None


def test_bad_routine_configuration_is_atomic_and_duplicate_refused(tmp_path):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        scenario(db, configured=False)
        baseline = db.load("test")
        valid = ev("NPCRoutineConfigured", {
            "npc_id": "basim", "home_id": "square", "workplace_id": "smithy",
            "work_start": 0, "work_end": 300,
        })
        invalid = ev("NPCRoutineConfigured", {
            "npc_id": "nora", "home_id": "square", "workplace_id": "ghost",
            "work_start": 0, "work_end": 300,
        })
        with pytest.raises(InvalidEvent):
            db.append("test", "atomic-bad", baseline.revision, [valid, invalid],
                      bootstrap=True)
        assert db.load("test").to_dict() == baseline.to_dict()
        for bad in (True, -1, 86400, "0"):
            altered = ev("NPCRoutineConfigured", {
                "npc_id": "basim", "home_id": "square", "workplace_id": "smithy",
                "work_start": bad, "work_end": 300,
            })
            with pytest.raises(InvalidEvent):
                db.append("test", f"bad-{bad}", baseline.revision, [altered],
                          bootstrap=True)
        db.append("test", "good", baseline.revision, [valid], bootstrap=True)
        after = db.load("test")
        with pytest.raises(InvalidEvent):
            db.append("test", "duplicate", after.revision, [valid], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("test")
        clock.advance("test", seconds=1, command_id="tick",
                      expected_revision=after.revision)
        latest = db.load("test")
        with pytest.raises(InvalidEvent):
            db.append("test", "late", latest.revision,
                      [ev("NPCRoutineConfigured", {
                          "npc_id": "nora", "home_id": "square",
                          "workplace_id": "smithy", "work_start": 0, "work_end": 300
                      })], bootstrap=True)
        assert db.verify("test").to_dict() == db.load("test").to_dict()


def test_invalid_snapshot_cannot_reassign_workplace(tmp_path):
    with SQLiteEventStore(tmp_path / "snapshot.sqlite") as db:
        scenario(db)
        snap = db.load("test").to_dict()
        snap["npc_routines"]["basim"]["home_id"] = "unknown-location"
        with pytest.raises(ValueError):
            WorldState.from_dict(snap)


def test_full_commute_shift_and_return_home_without_teleport(tmp_path):
    with SQLiteEventStore(tmp_path / "shift.sqlite") as db:
        scenario(db, work_start=0, work_end=300)
        clock = TimeEngine(db)
        clock.open_session("test")
        engine = LivingWorldEngine(db, clock, navigation_enabled=True, routines_enabled=True)
        result = engine.advance("test", seconds=465, command_id="one-day-part",
                                expected_revision=db.load("test").revision)
        state = result.state
        history = [t for t in state.travels.values() if t["npc_id"] == "basim"]
        assert len(history) == 2
        ordered = sorted(history, key=lambda t: t["start"])
        assert (ordered[0]["origin"], ordered[0]["destination"],
                ordered[0]["start"], ordered[0]["arrived_at"]) == (
                    "square", "smithy", 0, 50)
        assert ordered[1]["origin"] == "smithy" and ordered[1]["destination"] == "square"
        assert ordered[1]["start"] >= 300
        assert ordered[1]["arrived_at"] == ordered[1]["start"] + 50
        work = [a for a in state.actions.values()
                if a["npc_id"] == "basim" and a["action"] == "work"]
        assert work
        assert all(50 <= a["start"] < 300 for a in work)
        assert state.entities["basim"]["location_id"] == "square"
        assert db.verify("test").to_dict() == state.to_dict()


def test_no_known_road_cannot_work_remotely_or_teleport(tmp_path):
    with SQLiteEventStore(tmp_path / "isolated.sqlite") as db:
        scenario(db, route=False, work_start=0, work_end=300)
        clock = TimeEngine(db)
        clock.open_session("test")
        state = LivingWorldEngine(db, clock, navigation_enabled=True,
                                  routines_enabled=True).advance(
            "test", seconds=301, command_id="isolated",
            expected_revision=db.load("test").revision).state
        assert not [t for t in state.travels.values() if t["npc_id"] == "basim"]
        assert not [a for a in state.actions.values()
                    if a["npc_id"] == "basim" and a["action"] == "work"]
        assert state.entities["basim"]["location_id"] == "square"
        assert db.verify("test").to_dict() == state.to_dict()


def test_critical_need_prevents_optional_commute(tmp_path):
    with SQLiteEventStore(tmp_path / "hungry.sqlite") as db:
        scenario(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        current = db.load("test")
        db.append("test", "urgent-hunger", current.revision, [
            ev("NPCNeedChanged", {"npc_id": "basim", "need": "hunger",
                                  "previous": 5, "current": 95}, who="basim")
        ])
        state = db.load("test")
        assert choose_routine_route(state, "basim") is None
        result = LivingWorldEngine(db, clock, navigation_enabled=True,
                                   routines_enabled=True).advance(
            "test", seconds=1, command_id="urgent",
            expected_revision=state.revision)
        assert not any(t["npc_id"] == "basim" for t in result.state.travels.values())
        assert db.verify("test").to_dict() == result.state.to_dict()
