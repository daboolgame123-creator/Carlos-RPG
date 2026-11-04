"""Phase 01-Q — bounded, event-audited gathering from a finite site."""
from __future__ import annotations
import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCService, NPCActionService,
    NPCGatheringService, NPCConsumptionService, WorldState,
)
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.time_engine import SessionClosed


def ev(name, values, actor=None, t=0):
    return DomainEvent(name, actor, "isolated gathering fixture", t, values)


def make(db, *, supply=2, initialize_site=True, initialize_food=True,
         characters=("nora", "basim")):
    db.create_world("w")
    events = [ev("LocationCreated", {"id": "grove", "name": "Grove"}),
              ev("LocationCreated", {"id": "village", "name": "Village"})]
    if initialize_site:
        events.append(ev("ResourceChanged", {"owner_id": "grove", "resource": "wild_food",
                                            "previous": None, "current": supply,
                                            "source": "initialization"}))
    for name in characters:
        events += [
            ev("EntityCreated", {"id": name, "name": name, "location_id": "grove",
                                 "controller": "npc"}),
            ev("NPCConfigured", {"npc_id": name, "role": "explorer",
                                 "needs": {"fatigue": 5, "hunger": 40, "safety": 0},
                                 "goals": {"earn": 0, "explore": 95, "survive": 30}}),
        ]
        for resource in (["investigation_attempts", "labor_units"] +
                         (["food"] if initialize_food else [])):
            events.append(ev("ResourceChanged", {
                "owner_id": name, "resource": resource, "previous": None,
                "current": 0, "source": "initialization"}))
    return db.append("w", "setup", 0, events, bootstrap=True)


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / "gather.sqlite") as db:
        make(db)
        clock = TimeEngine(db)
        clock.open_session("w")
        yield db, clock, NPCGatheringService(db, clock)


def finish_investigations(db, clock, assignments=(("nora", "search-n"),),
                          *, tick_id="travel-time"):
    npc = NPCService(db, clock)
    actions = NPCActionService(db, clock)
    for who, action_id in assignments:
        planned = npc.decide("w", who, command_id="decide:" + action_id,
                             expected_revision=db.load("w").revision)
        assert planned.action == "investigate"
        action = actions.start("w", who, action_id,
                               expected_revision=db.load("w").revision)
        assert action.action == "investigate" and action.due == 90
    state = db.load("w")
    return clock.advance("w", seconds=90, command_id=tick_id,
                         expected_revision=state.revision).state


def gather(db, svc, npc="nora", action="search-n", command="gather"):
    return svc.collect("w", npc, action, command_id=command,
                       expected_revision=db.load("w").revision)


def test_completed_investigation_recovers_one_unit_and_preserves_total(world):
    db, clock, svc = world
    ready = finish_investigations(db, clock)
    before = (ready.resources["grove"]["wild_food"]
              + ready.resources["nora"]["food"])
    result = gather(db, svc)
    s = result.state
    assert result.quantity == 1 and s.time == 90
    assert s.resources["grove"]["wild_food"] == 1
    assert s.resources["nora"]["food"] == 1
    assert s.resources["grove"]["wild_food"] + s.resources["nora"]["food"] == before
    assert s.gatherings["search-n"]["at"] == 90
    assert s.gatherings["search-n"]["site_id"] == "grove"
    assert s.gatherings["search-n"]["site_before"] == 2
    assert s.gatherings["search-n"]["site_after"] == 1
    assert db.verify("w").to_dict() == s.to_dict()


def test_two_characters_share_finite_stock_and_cannot_duplicate(world):
    db, clock, svc = world
    finish_investigations(db, clock, [("nora", "search-n"), ("basim", "search-b")])
    a = gather(db, svc)
    b = gather(db, svc, npc="basim", action="search-b", command="b")
    assert b.state.resources["grove"]["wild_food"] == 0
    assert b.state.resources["nora"]["food"] == 1
    assert b.state.resources["basim"]["food"] == 1
    assert len(b.state.gatherings) == 2
    assert db.verify("w").to_dict() == b.state.to_dict()
    with pytest.raises(InvalidEvent, match="already"):
        gather(db, svc, command="repeat")
    assert db.load("w").to_dict() == b.state.to_dict()


def test_zero_and_missing_natural_resources_are_not_infinite(tmp_path):
    for supply, initialized in [(0, True), (2, False)]:
        with SQLiteEventStore(tmp_path / f"{supply}-{initialized}.db") as db:
            make(db, supply=supply, initialize_site=initialized)
            clock = TimeEngine(db)
            clock.open_session("w")
            ready = finish_investigations(db, clock)
            with pytest.raises(InvalidEvent, match="initialized, sufficient"):
                gather(db, NPCGatheringService(db, clock))
            assert db.load("w").to_dict() == ready.to_dict()


def test_absent_owned_food_is_unknown_not_free_inventory(tmp_path):
    with SQLiteEventStore(tmp_path / "unknown.db") as db:
        make(db, initialize_food=False)
        clock = TimeEngine(db)
        clock.open_session("w")
        old = finish_investigations(db, clock)
        with pytest.raises(InvalidEvent, match="initialized, sufficient"):
            gather(db, NPCGatheringService(db, clock))
        assert db.load("w").to_dict() == old.to_dict()


def test_gathering_requires_completed_investigation_not_a_hope(world):
    db, clock, svc = world
    before = db.load("w")
    with pytest.raises(InvalidEvent, match="newly completed"):
        gather(db, svc)
    assert db.load("w").to_dict() == before.to_dict()


def test_only_authorized_actor_can_recover_from_current_site(world):
    db, clock, svc = world
    ready = finish_investigations(db, clock)
    for who, site, action, cmd in [
        ("basim", "grove", "search-n", "wrong-actor"),
        ("nora", "village", "search-n", "remote-site"),
        ("nora", "grove", "does-not-exist", "unknown-action")]:
        bad = ev("NPCFoodGathered", {"npc_id": who, "action_id": action,
                                    "site_id": site}, actor=who, t=90)
        with pytest.raises(InvalidEvent):
            db.append("w", cmd, ready.revision, [bad], action_authorized=True)
    assert db.load("w").to_dict() == ready.to_dict()


def test_provenance_capability_and_active_session_are_required(world):
    db, clock, svc = world
    ready = finish_investigations(db, clock)
    event = ev("NPCFoodGathered", {"npc_id": "nora", "action_id": "search-n",
                                   "site_id": "grove"}, actor="nora", t=90)
    with pytest.raises(InvalidEvent, match="capability"):
        db.append("w", "raw", ready.revision, [event])
    clock.close_session("w")
    with pytest.raises(SessionClosed):
        gather(db, svc)
    with pytest.raises(InvalidEvent, match="active play session"):
        db.append("w", "offline", ready.revision, [event], action_authorized=True)
    assert db.load("w").to_dict() == ready.to_dict()


def test_atomic_bad_double_gather_rolls_back_entire_batch(world):
    db, clock, svc = world
    before = finish_investigations(db, clock)
    event = ev("NPCFoodGathered", {"npc_id": "nora", "action_id": "search-n",
                                   "site_id": "grove"}, actor="nora", t=90)
    with pytest.raises(InvalidEvent, match="already"):
        db.append("w", "bad-batch", before.revision, [event, event],
                  action_authorized=True)
    assert db.load("w").to_dict() == before.to_dict()
    assert db.db.execute(
        "SELECT count(*) FROM commands WHERE command_id='bad-batch'"
    ).fetchone()[0] == 0


def test_snapshot_full_replay_and_process_restart_are_equal(tmp_path):
    path = tmp_path / "saved.sqlite"
    with SQLiteEventStore(path) as db:
        make(db)
        clock = TimeEngine(db); clock.open_session("w")
        finish_investigations(db, clock)
        collected = gather(db, NPCGatheringService(db, clock))
        db.snapshot("w")
        expected = collected.state.to_dict()
    with SQLiteEventStore(path) as restored:
        assert restored.load("w").to_dict() == expected
        assert restored.load("w", use_snapshot=False).to_dict() == expected
        assert restored.verify("w").to_dict() == expected
        assert "search-n" in restored.load("w").gatherings


def test_no_reuse_after_next_tick_and_revision_conflicts(world):
    db, clock, svc = world
    finish_investigations(db, clock)
    old = db.load("w")
    gathered = gather(db, svc)
    with pytest.raises(RevisionConflict):
        svc.collect("w", "nora", "search-n", command_id="stale",
                    expected_revision=old.revision)
    clock.advance("w", seconds=1, command_id="tick",
                  expected_revision=gathered.state.revision)
    with pytest.raises(InvalidEvent, match="newly completed"):
        gather(db, svc, command="late")


def test_gathered_food_can_actually_be_eaten_without_hidden_minting(world):
    db, clock, svc = world
    ready = finish_investigations(db, clock)
    gathered = gather(db, svc)
    assert ready.npcs["nora"]["needs"]["hunger"] == 45
    meal = NPCConsumptionService(db, clock).eat(
        "w", "nora", 1, command_id="eat", expected_revision=gathered.state.revision)
    assert meal.state.resources["nora"]["food"] == 0
    assert meal.state.resources["grove"]["wild_food"] == 1
    assert meal.state.npcs["nora"]["needs"]["hunger"] == 20
    assert db.verify("w").to_dict() == meal.state.to_dict()


def test_forged_or_malformed_gathering_history_is_rejected(world):
    db, clock, svc = world
    finish_investigations(db, clock)
    saved = gather(db, svc).state.to_dict()
    saved["gatherings"]["search-n"]["site_after"] = 1000
    with pytest.raises(ValueError, match="conserve"):
        WorldState.from_dict(saved)
    saved["gatherings"]["search-n"]["site_after"] = 1
    saved["gatherings"]["search-n"]["action_id"] = "invented"
    with pytest.raises(ValueError, match="invalid food-gathering"):
        WorldState.from_dict(saved)


def test_unrelated_autonomous_world_has_no_implicit_gathering(world):
    db, clock, svc = world
    assert db.load("w").gatherings == {}
    # No new automatic decisions or map harvesting were added in this phase.
    # Even finishing an investigation alone does not materialize inventory.
    ready = finish_investigations(db, clock)
    assert ready.gatherings == {}
    assert ready.resources["grove"]["wild_food"] == 2
    assert ready.resources["nora"]["food"] == 0
