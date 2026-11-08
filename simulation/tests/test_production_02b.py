"""02-B opt-in bakery: profession, local inputs, shared tools, timed output."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCProductionService,
    LivingWorldEngine, WorldState, apply_event,
)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from carlos_sim.store import InvalidEvent

RECIPE = {
    "id": "bread", "site_id": "bakery", "role": "baker",
    "input_resource": "grain", "input_amount": 2,
    "output_resource": "bread", "output_amount": 1,
    "tool_resource": "oven", "duration_seconds": 90,
}
PEOPLE = ("basim", "nora", "salma", "adel", "huda", "omar", "layla")


def ev(kind, data, actor=None, at=0):
    return DomainEvent(kind, actor, "synthetic 02-B bakery test", at, data)


def setup(db, *, grain=6, oven=1, bread=0, recipe=True, people=PEOPLE,
          role_override=None, routes=False):
    db.create_world("test")
    events = [ev("LocationCreated", {"id": "bakery", "name": "Bakery"})]
    if routes:
        events.extend([
            ev("LocationCreated", {"id": "square", "name": "Square"}),
            ev("RouteCreated", {"id": "bakery-square", "a": "bakery",
                                "b": "square", "seconds": 50}),
        ])
    for resource, amount in (("grain", grain), ("oven", oven), ("bread", bread)):
        if amount is not None:
            events.append(ev("ResourceChanged", {
                "owner_id": "bakery", "resource": resource,
                "previous": None, "current": amount,
                "source": "initialization",
            }))
    for who in people:
        role = (role_override if who == "basim" and role_override is not None
                else "baker" if who in ("basim", "nora") else "resident")
        events.extend([
            ev("EntityCreated", {
                "id": who, "name": who, "location_id": "bakery",
                "controller": "npc",
            }),
            ev("NPCConfigured", {
                "npc_id": who, "role": role,
                "needs": {"fatigue": 5, "hunger": 30, "safety": 0},
                "goals": {"earn": 40, "explore": 10, "survive": 30},
            }),
        ])
        for metric in ("labor_units", "investigation_attempts"):
            events.append(ev("ResourceChanged", {
                "owner_id": who, "resource": metric,
                "previous": None, "current": 0, "source": "initialization",
            }))
    if recipe:
        events.append(ev("ProductionRecipeConfigured", RECIPE))
    db.append("test", "bootstrap", 0, events, bootstrap=True)


def start(db, clock, who="basim", name="batch"):
    return NPCProductionService(db, clock).start(
        "test", who, "bread", name,
        expected_revision=db.load("test").revision)


def advance(db, clock, secs, cid):
    return clock.advance(
        "test", seconds=secs, command_id=cid,
        expected_revision=db.load("test").revision).state


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / "bakery.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        yield db, clock


def test_versions_and_no_recipe_cannot_produce(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (39, 51)
    with SQLiteEventStore(tmp_path / "off.sqlite") as db:
        setup(db, recipe=False)
        clock = TimeEngine(db)
        clock.open_session("test")
        assert db.load("test").production_jobs == {}
        with pytest.raises(InvalidEvent):
            start(db, clock)
        s = advance(db, clock, 500, "time")
        assert s.resources["bakery"]["grain"] == 6
        assert s.resources["bakery"]["bread"] == 0
        assert db.verify("test").to_dict() == s.to_dict()


def test_grain_reserved_first_bread_exists_only_at_due(world):
    db, clock = world
    result = start(db, clock)
    assert result.due == 90
    s = result.state
    assert s.resources["bakery"]["grain"] == 4
    assert s.resources["bakery"]["bread"] == 0
    assert s.resources["bakery"]["oven"] == 1
    job = s.production_jobs["batch"]
    assert job["input_before"] == 6 and job["input_after"] == 4
    assert job["tool_seen"] == 1 and job["status"] == "running"
    before = advance(db, clock, 89, "time89")
    assert before.resources["bakery"]["bread"] == 0
    after = advance(db, clock, 1, "time90")
    assert after.resources["bakery"]["bread"] == 1
    assert after.resources["bakery"]["grain"] == 4
    assert after.resources["bakery"]["oven"] == 1
    assert after.production_jobs["batch"]["finished_at"] == 90
    assert after.production_jobs["batch"]["output_before"] == 0
    assert after.production_jobs["batch"]["output_after"] == 1
    assert "production:batch" not in after.scheduled
    assert db.verify("test").to_dict() == after.to_dict()


def test_one_oven_no_double_booking_two_ovens_allow_two_workers(tmp_path):
    for ovens in (1, 2):
        with SQLiteEventStore(tmp_path / f"{ovens}.sqlite") as db:
            setup(db, oven=ovens)
            clock = TimeEngine(db)
            clock.open_session("test")
            start(db, clock, "basim", "first")
            state = db.load("test").to_dict()
            if ovens == 1:
                with pytest.raises(InvalidEvent, match="tool"):
                    start(db, clock, "nora", "second")
                assert db.load("test").to_dict() == state
            else:
                start(db, clock, "nora", "second")
                assert db.load("test").resources["bakery"]["grain"] == 2
                assert db.load("test").resources["bakery"]["bread"] == 0
                after = advance(db, clock, 90, "bake-both")
                assert after.resources["bakery"]["bread"] == 2
                assert len(after.production_jobs) == 2
                assert all(j["status"] == "completed"
                           for j in after.production_jobs.values())
                assert db.verify("test").to_dict() == after.to_dict()


def test_missing_or_insufficient_material_tool_and_output(tmp_path):
    for i, kwargs in enumerate((
        {"grain": 1}, {"oven": 0},
        {"grain": None}, {"oven": None}, {"bread": None},
    )):
        with SQLiteEventStore(tmp_path / f"no-{i}.sqlite") as db:
            if any(value is None for value in kwargs.values()):
                # The recipe contract requires explicitly initialized stocks.
                with pytest.raises(InvalidEvent):
                    setup(db, **kwargs)
                assert db.load("test").revision == 0
                assert db.load("test").resources == {}
            else:
                setup(db, **kwargs)
                clock = TimeEngine(db)
                clock.open_session("test")
                prior = db.load("test").to_dict()
                with pytest.raises(InvalidEvent):
                    start(db, clock)
                assert db.load("test").to_dict() == prior


def test_wrong_profession_and_reserved_worker_busy(world):
    db, clock = world
    with pytest.raises(InvalidEvent):
        start(db, clock, "adel", "not-baker")
    start(db, clock, "basim", "real")
    saved = db.load("test")
    with pytest.raises(InvalidEvent):
        start(db, clock, "basim", "work-again")
    # Even a trusted reducer cannot start a second physical task during work.
    forged = ev("NPCActionStarted", {
        "action_id": "fake", "npc_id": "basim", "action": "work",
        "schedule_id": "npc-action:fake", "due": 180,
    }, actor="basim")
    with pytest.raises(ValueError):
        apply_event(saved, forged, action_authorized=True)
    assert db.load("test").to_dict() == saved.to_dict()


def test_production_appointment_may_not_be_forged_or_cancelled(world):
    db, clock = world
    old = db.load("test")
    forged = ev("ScheduledEventCreated", {
        "id": "production:invented", "due": 90,
        "order": old.next_schedule_order, "kind": "signal",
        "payload": {"__production_job": "invented"}, "interrupt": False,
    })
    with pytest.raises(InvalidEvent, match="fabricated"):
        db.append("test", "forge", old.revision, [forged],
                  production_authorized=True)
    start(db, clock)
    in_process = db.load("test")
    with pytest.raises(InvalidEvent, match="cannot cancel"):
        clock.cancel("test", "production:batch", command_id="cancel",
                     expected_revision=in_process.revision)
    with pytest.raises(InvalidEvent):
        db.append("test", "early", in_process.revision, [
            ev("ScheduledEventFired", {"id": "production:batch"})
        ], clock_authorized=True)
    assert db.load("test").to_dict() == in_process.to_dict()


def test_seven_npcs_continue_other_work_while_one_bakes(tmp_path):
    with SQLiteEventStore(tmp_path / "seven.sqlite") as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session("test")
        start(db, clock, "basim", "baker")
        before = LivingWorldEngine(db, clock).advance(
            "test", seconds=89, command_id="first",
            expected_revision=db.load("test").revision)
        assert len(before.state.npcs) == 7
        assert before.state.resources["bakery"]["bread"] == 0
        assert all(a["npc_id"] != "basim"
                   for a in before.state.actions.values())
        done = LivingWorldEngine(db, clock).advance(
            "test", seconds=1, command_id="finish",
            expected_revision=db.load("test").revision)
        assert done.state.resources["bakery"]["bread"] == 1
        assert done.state.production_jobs["baker"]["status"] == "completed"
        assert db.verify("test").to_dict() == done.state.to_dict()


def test_real_navigation_cannot_interrupt_baker_and_remote_baker_cannot_start(tmp_path):
    from carlos_sim import NPCMovementService
    with SQLiteEventStore(tmp_path / "busy-travel.sqlite") as db:
        setup(db, routes=True)
        clock = TimeEngine(db)
        clock.open_session("test")
        start(db, clock, "basim", "first")
        baseline = db.load("test").to_dict()
        with pytest.raises(InvalidEvent, match="producing"):
            NPCMovementService(db, clock).start(
                "test", "basim", "bakery-square", "escape",
                expected_revision=baseline["revision"])
        assert db.load("test").to_dict() == baseline

    with SQLiteEventStore(tmp_path / "remote-worker.sqlite") as db:
        setup(db, routes=True)
        clock = TimeEngine(db)
        clock.open_session("test")
        NPCMovementService(db, clock).start(
            "test", "basim", "bakery-square", "real-trip",
            expected_revision=db.load("test").revision)
        with pytest.raises(InvalidEvent):
            start(db, clock, "basim", "in-transit")
        advance(db, clock, 50, "arrive")
        assert db.load("test").entities["basim"]["location_id"] == "square"
        with pytest.raises(InvalidEvent, match="physically"):
            start(db, clock, "basim", "absent")
