"""03-A7c recorded peer sighting gate: multi-character integration tests."""
import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.injury_observation import witnessed_peer_here
from carlos_sim.movement import NPCMovementService
from test_property_02h1 import village


@pytest.fixture
def scene(tmp_path):
    with SQLiteEventStore(tmp_path / "observation-opportunity.sqlite") as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        yield db, clock, NPCMovementService(db, clock)


def test_presence_is_not_a_recorded_sighting(scene):
    db, _clock, movement = scene
    before = db.load("v")
    assert not witnessed_peer_here(before, "basim", "nora")
    assert not witnessed_peer_here(before, "salma", "huda")
    assert not witnessed_peer_here(before, "basim", "omar")
    assert db.verify("v").to_dict() == before.to_dict()


def test_explicit_observation_only_grants_local_opportunity(scene):
    db, _clock, movement = scene
    before = db.load("v")
    after = movement.observe("v", "basim", command_id="watch:basim",
                             expected_revision=before.revision)
    assert witnessed_peer_here(after, "basim", "nora")
    assert witnessed_peer_here(after, "basim", "salma")
    assert witnessed_peer_here(after, "basim", "adel")
    assert witnessed_peer_here(after, "basim", "huda")
    assert not witnessed_peer_here(after, "nora", "basim")
    assert not witnessed_peer_here(after, "basim", "omar")
    assert not witnessed_peer_here(after, "basim", "basim")
    assert after.injuries == before.injuries
    assert after.treatments == before.treatments
    for person in ("basim", "nora", "salma", "adel", "huda"):
        assert after.npcs[person]["beliefs"] == before.npcs[person]["beliefs"]
    assert db.verify("v").to_dict() == after.to_dict()


def test_reopen_preserves_recorded_opportunity_without_health_disclosure(tmp_path):
    path = tmp_path / "reopen-opportunity.sqlite"
    with SQLiteEventStore(path) as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        after = NPCMovementService(db, clock).observe(
            "v", "basim", command_id="watch:durable",
            expected_revision=db.load("v").revision)
        assert witnessed_peer_here(after, "basim", "nora")
        expected = after.to_dict()
    with SQLiteEventStore(path) as reopened:
        state = reopened.load("v")
        assert witnessed_peer_here(state, "basim", "nora")
        assert not witnessed_peer_here(state, "nora", "basim")
        assert state.to_dict() == expected
        assert reopened.verify("v").to_dict() == expected


@pytest.mark.parametrize("observer,target", [
    ("basim", "basim"), ("basim", "omar"), ("omar", "nora"),
    ("missing", "nora"), ("basim", "missing"), ("basim", None),
    (None, "nora"), (True, "nora"), ("basim", False),
])
def test_unavailable_or_invalid_peer_fails_closed(scene, observer, target):
    db, _clock, movement = scene
    after = movement.observe("v", "basim", command_id="watch:fail",
                             expected_revision=db.load("v").revision)
    assert witnessed_peer_here(after, observer, target) is False


def test_reject_plain_dict_as_authoritative_world(scene):
    db, _clock, movement = scene
    with pytest.raises(ValueError):
        witnessed_peer_here(db.load("v").to_dict(), "basim", "nora")


def test_observation_expiring_after_logical_time_advance(scene):
    db, clock, movement = scene
    seen = movement.observe(
        "v", "basim", command_id="watch:old",
        expected_revision=db.load("v").revision,
    )
    assert witnessed_peer_here(seen, "basim", "nora")
    later = clock.advance(
        "v", seconds=1, command_id="time:after-watch",
        expected_revision=seen.revision,
    ).state
    assert not witnessed_peer_here(later, "basim", "nora")
    assert db.verify("v").to_dict() == later.to_dict()


def test_sighting_does_not_survive_target_departure(tmp_path):
    from test_movement import build
    with SQLiteEventStore(tmp_path / "departure.sqlite") as db:
        build(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        movement = NPCMovementService(db, clock)
        observed = movement.observe(
            "village", "basim", command_id="look:before-travel",
            expected_revision=db.load("village").revision,
        )
        assert witnessed_peer_here(observed, "basim", "nora")
        traveling = movement.start(
            "village", "nora", "path", "nora-departs",
            expected_revision=observed.revision,
        ).state
        assert not witnessed_peer_here(traveling, "basim", "nora")
        assert db.verify("village").to_dict() == traveling.to_dict()


def test_sighting_does_not_survive_observer_departure(tmp_path):
    from test_movement import build
    with SQLiteEventStore(tmp_path / "observer-departs.sqlite") as db:
        build(db)
        clock = TimeEngine(db)
        clock.open_session("village")
        movement = NPCMovementService(db, clock)
        observed = movement.observe(
            "village", "basim", command_id="look:before-departure",
            expected_revision=db.load("village").revision,
        )
        assert witnessed_peer_here(observed, "basim", "nora")
        traveling = movement.start(
            "village", "basim", "path", "basim-departs",
            expected_revision=observed.revision,
        ).state
        assert not witnessed_peer_here(traveling, "basim", "nora")
        assert db.verify("village").to_dict() == traveling.to_dict()


@pytest.mark.parametrize("busy_person", ["nora", "basim"])
def test_running_action_invalidates_current_sighting(tmp_path, busy_person):
    """Neither a working observer nor a busy subject is an available witness."""
    from carlos_sim import NPCService, NPCActionService
    from test_actions import setup as setup_action_world
    with SQLiteEventStore(tmp_path / ("busy-" + busy_person + ".sqlite")) as db:
        setup_action_world(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        movement = NPCMovementService(db, clock)
        observed = movement.observe(
            "world", "basim", command_id="watch:before-action",
            expected_revision=db.load("world").revision,
        )
        assert witnessed_peer_here(observed, "basim", "nora")
        decision = NPCService(db, clock).decide(
            "world", busy_person, command_id="decide:busy-" + busy_person,
            expected_revision=observed.revision,
        )
        assert decision is not None
        started = NPCActionService(db, clock).start(
            "world", busy_person, "action-" + busy_person,
            expected_revision=db.load("world").revision,
        )
        assert not witnessed_peer_here(started.state, "basim", "nora")
        assert db.verify("world").to_dict() == started.state.to_dict()


def test_observation_command_requires_live_revision(scene):
    from carlos_sim.store import RevisionConflict, DuplicateCommand
    db, _clock, movement = scene
    old = db.load("v")
    first = movement.observe(
        "v", "basim", command_id="watch:revision",
        expected_revision=old.revision,
    )
    with pytest.raises(RevisionConflict):
        movement.observe(
            "v", "nora", command_id="watch:outdated",
            expected_revision=old.revision,
        )
    with pytest.raises(DuplicateCommand):
        movement.observe(
            "v", "basim", command_id="watch:revision",
            expected_revision=first.revision,
        )
    assert db.load("v").to_dict() == first.to_dict()
    assert db.verify("v").to_dict() == first.to_dict()
