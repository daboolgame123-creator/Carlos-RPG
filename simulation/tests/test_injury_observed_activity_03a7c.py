"""03-A7c: only a scheduled real rest is locally visible; no diagnosis."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCService
from carlos_sim.actions import NPCActionService
from carlos_sim.movement import NPCMovementService
from carlos_sim.injury_observation import observed_resting_activity
from test_actions import setup as setup_actions


def scenario(tmp_path, *, injury=False, fatigue=5):
    db = SQLiteEventStore(tmp_path / ("rest-injured.sqlite" if injury else "rest-tired.sqlite"))
    setup_actions(db, fatigue=fatigue)
    if injury:
        state = db.load("world")
        db.append("world", "bootstrap:visible-rest", state.revision, [
            DomainEvent("InjuryRecorded", None, "trusted test injury", 0, {
                "injury_id": "nora-secret", "subject_id": "nora",
                "severity": 65, "source": "trusted_test_bootstrap"
            })], bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session("world")
    movement = NPCMovementService(db, clock)
    return db, clock, movement


@pytest.mark.parametrize("injury,fatigue", [(True, 5), (False, 90)])
def test_same_visible_rest_cannot_disclose_injury(tmp_path, injury, fatigue):
    db, clock, movement = scenario(tmp_path, injury=injury, fatigue=fatigue)
    with db:
        before = db.load("world")
        assert observed_resting_activity(before, "basim", "nora") is None
        selected = NPCService(db, clock).decide(
            "world", "nora", command_id="choose-rest", expected_revision=before.revision)
        assert selected.action == "rest"
        started = NPCActionService(db, clock).start(
            "world", "nora", "rest-by-nora", expected_revision=db.load("world").revision)
        assert observed_resting_activity(started.state, "basim", "nora") is None
        observed = movement.observe(
            "world", "basim", command_id="look:rest",
            expected_revision=started.state.revision)
        evidence = observed_resting_activity(observed, "basim", "nora")
        assert evidence == {
            "subject_id": "nora", "sign": "visible_resting",
            "site_id": "square", "observed_at": 0,
        }
        assert "nora-secret" not in repr(evidence)
        assert "severity" not in repr(evidence)
        assert observed_resting_activity(observed, "nora", "basim") is None
        assert all(not npc["beliefs"] for npc in observed.npcs.values())
        assert db.verify("world").to_dict() == observed.to_dict()


def test_rest_visibility_expires_and_reopen_remains_private(tmp_path):
    db, clock, movement = scenario(tmp_path, injury=True)
    path = tmp_path / "rest-injured.sqlite"
    with db:
        NPCService(db, clock).decide(
            "world", "nora", command_id="choose", expected_revision=db.load("world").revision)
        started = NPCActionService(db, clock).start(
            "world", "nora", "active-rest", expected_revision=db.load("world").revision)
        seen = movement.observe(
            "world", "basim", command_id="look", expected_revision=started.state.revision)
        assert observed_resting_activity(seen, "basim", "nora") is not None
        db.snapshot("world")
        original = seen.to_dict()
    with SQLiteEventStore(path) as db:
        recovered = db.load("world")
        assert recovered.to_dict() == original
        assert observed_resting_activity(recovered, "basim", "nora") is not None
        assert db.verify("world").to_dict() == original
        clock = TimeEngine(db)
        clock.open_session("world")
        later = clock.advance("world", seconds=1, command_id="step",
                              expected_revision=recovered.revision).state
        assert observed_resting_activity(later, "basim", "nora") is None
        assert db.verify("world").to_dict() == later.to_dict()


@pytest.mark.parametrize("observer,target", [
    ("nora", "nora"), ("basim", "basim"), ("missing", "nora"),
    ("basim", "missing"), (None, "nora"), ("basim", False),
])
def test_bad_identifiers_never_yield_resting_evidence(tmp_path, observer, target):
    db, clock, movement = scenario(tmp_path, fatigue=90)
    with db:
        NPCService(db, clock).decide(
            "world", "nora", command_id="choose", expected_revision=db.load("world").revision)
        action = NPCActionService(db, clock).start(
            "world", "nora", "rest", expected_revision=db.load("world").revision)
        sight = movement.observe(
            "world", "basim", command_id="watch", expected_revision=action.state.revision)
        assert observed_resting_activity(sight, observer, target) is None


def test_plain_dict_cannot_impersonate_validated_world(tmp_path):
    db, clock, _movement = scenario(tmp_path)
    with db:
        with pytest.raises(ValueError):
            observed_resting_activity(db.load("world").to_dict(), "basim", "nora")
