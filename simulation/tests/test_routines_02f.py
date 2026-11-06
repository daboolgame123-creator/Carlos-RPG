"""02-F: real home/work commute, private routines, and hostile configuration."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine, NPCService, NPCActionService
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, WorldState
from carlos_sim.routines import choose_routine_route
from carlos_sim.store import InvalidEvent
from carlos_sim.time_engine import AdvanceLimitExceeded
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
    assert (SCHEMA_VERSION, RULES_VERSION) == (30, 38)
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


def test_exact_shift_start_does_not_trigger_early_commute(tmp_path):
    with SQLiteEventStore(tmp_path / "boundary.sqlite") as db:
        scenario(db, work_start=100, work_end=260)
        clock = TimeEngine(db)
        clock.open_session("test")
        engine = LivingWorldEngine(db, clock, navigation_enabled=True, routines_enabled=True)
        before = engine.advance("test", seconds=99, command_id="before",
                                expected_revision=db.load("test").revision).state
        assert not any(t["npc_id"] == "basim" for t in before.travels.values())
        at_start = engine.advance("test", seconds=1, command_id="at-start",
                                  expected_revision=before.revision).state
        routes = [t for t in at_start.travels.values() if t["npc_id"] == "basim"]
        assert len(routes) == 1
        assert routes[0]["start"] == 100
        assert routes[0]["due"] == 150
        assert at_start.entities["basim"]["location_id"] == "square"
        assert db.verify("test").to_dict() == at_start.to_dict()


def test_emergency_while_busy_does_not_cancel_physical_work(tmp_path):
    with SQLiteEventStore(tmp_path / "emergency.sqlite") as db:
        scenario(db, work_start=0, work_end=300)
        clock = TimeEngine(db)
        clock.open_session("test")
        engine = LivingWorldEngine(db, clock, navigation_enabled=True, routines_enabled=True)
        at_60 = engine.advance("test", seconds=60, command_id="to-60",
                               expected_revision=db.load("test").revision).state
        doing = [a for a in at_60.actions.values()
                 if a["npc_id"] == "basim" and a["status"] == "running"]
        assert len(doing) == 1 and doing[0]["action"] == "work"
        elevated = db.append("test", "hungry-on-shift", at_60.revision, [
            ev("NPCNeedChanged", {"npc_id": "basim", "need": "hunger",
                                  "previous": 5, "current": 95}, who="basim", at=60)
        ])
        assert choose_routine_route(elevated, "basim") is None
        after = engine.advance("test", seconds=175, command_id="complete-existing",
                               expected_revision=elevated.revision).state
        finished = [a for a in after.actions.values() if a["npc_id"] == "basim"
                    and a["status"] == "completed" and a["action"] == "work"]
        assert len(finished) == 1 and finished[0]["completed_at"] == 230
        assert len([t for t in after.travels.values() if t["npc_id"] == "basim"]) == 1
        assert db.verify("test").to_dict() == after.to_dict()


def test_manual_direct_work_outside_workplace_is_rejected_atomically(tmp_path):
    with SQLiteEventStore(tmp_path / "direct.sqlite") as db:
        scenario(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        decision = NPCService(db, clock).decide(
            "test", "basim", command_id="manual-choice",
            expected_revision=db.load("test").revision)
        assert decision.action == "work"
        before = db.load("test")
        with pytest.raises(InvalidEvent, match="outside its assigned workplace"):
            NPCActionService(db, clock).start(
                "test", "basim", "fake-remote-labor",
                expected_revision=before.revision)
        assert db.load("test").to_dict() == before.to_dict()
        assert db.db.execute(
            "SELECT COUNT(*) FROM commands WHERE command_id='action-start:fake-remote-labor'"
        ).fetchone()[0] == 0
        assert db.verify("test").to_dict() == before.to_dict()


def test_seven_npcs_with_different_shifts_and_unconfigured_neighbors(tmp_path):
    with SQLiteEventStore(tmp_path / "seven.sqlite") as db:
        setup(db, configured=False)
        who = ("basim", "nora", "salma")
        events = [
            ev("LocationCreated", {"id": "bakery", "name": "Bakery"}),
            ev("RouteCreated", {"id": "square-bakery", "a": "square",
                                "b": "bakery", "seconds": 50}),
        ]
        for index, npc in enumerate(who):
            events.append(ev("NPCRoutineConfigured", {
                "npc_id": npc, "home_id": "square", "workplace_id": "bakery",
                "work_start": index * 100, "work_end": 400 + index * 100
            }))
        db.append("test", "seven-setup", db.load("test").revision, events,
                  bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("test")
        result = LivingWorldEngine(db, clock, navigation_enabled=True,
                                   routines_enabled=True).advance(
            "test", seconds=50, command_id="seven",
            expected_revision=db.load("test").revision).state
        assert len(result.npcs) == 7
        assert set(result.npc_routines) == set(who)
        assert result.entities["basim"]["location_id"] == "bakery"
        assert result.entities["nora"]["location_id"] == "square"
        assert result.entities["salma"]["location_id"] == "square"
        assert db.verify("test").to_dict() == result.to_dict()


def test_inflight_commute_survives_close_snapshot_and_resume(tmp_path):
    path = tmp_path / "resume.sqlite"
    with SQLiteEventStore(path) as db:
        scenario(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        in_transit = LivingWorldEngine(db, clock, navigation_enabled=True,
                                      routines_enabled=True).advance(
            "test", seconds=1, command_id="start-journey",
            expected_revision=db.load("test").revision).state
        assert in_transit.entities["basim"]["location_id"] == "square"
        assert any(t["status"] == "traveling" and t["npc_id"] == "basim"
                   for t in in_transit.travels.values())
        db.snapshot("test")
        saved = in_transit.to_dict()
        clock.close_session("test")
    with SQLiteEventStore(path) as db:
        assert db.load("test").to_dict() == saved
        assert db.verify("test").to_dict() == saved
        clock = TimeEngine(db)
        clock.open_session("test")
        at_arrival = LivingWorldEngine(db, clock, navigation_enabled=True,
                                       routines_enabled=True).advance(
            "test", seconds=49, command_id="finish-journey",
            expected_revision=db.load("test").revision).state
        assert at_arrival.time == 50
        assert at_arrival.entities["basim"]["location_id"] == "smithy"
        assert db.verify("test").to_dict() == at_arrival.to_dict()


def test_split_time_preserves_physical_work_and_travel_results(tmp_path):
    results = []
    for name, chunks in (("lump", (465,)), ("split", (200, 265))):
        with SQLiteEventStore(tmp_path / (name + ".sqlite")) as db:
            scenario(db)
            clock = TimeEngine(db)
            clock.open_session("test")
            engine = LivingWorldEngine(db, clock, navigation_enabled=True,
                                       routines_enabled=True)
            for index, seconds in enumerate(chunks):
                engine.advance("test", seconds=seconds,
                               command_id=f"{name}-{index}",
                               expected_revision=db.load("test").revision)
            state = db.load("test")
            assert db.verify("test").to_dict() == state.to_dict()
            results.append(state)
    a, b = results
    for collection in ("npcs", "entities", "resources", "actions", "travels",
                       "npc_routines", "npc_temperaments"):
        assert getattr(a, collection) == getattr(b, collection), collection
    assert a.time == b.time == 465


def test_event_limit_failure_rolls_back_entire_routine_tick(tmp_path):
    with SQLiteEventStore(tmp_path / "limit.sqlite") as db:
        scenario(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        original = db.load("test")
        engine = LivingWorldEngine(db, clock, navigation_enabled=True,
                                   routines_enabled=True, max_events_per_advance=1)
        with pytest.raises(AdvanceLimitExceeded):
            engine.advance("test", seconds=1, command_id="too-many",
                           expected_revision=original.revision)
        assert db.load("test").to_dict() == original.to_dict()
        assert db.db.execute(
            "SELECT COUNT(*) FROM commands WHERE command_id='too-many'"
        ).fetchone()[0] == 0
