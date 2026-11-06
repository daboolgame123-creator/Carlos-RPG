"""03-A7c conservative interpretation never upgrades visible rest to injury fact."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, NPCService, TimeEngine
from carlos_sim.actions import NPCActionService
from carlos_sim.movement import NPCMovementService
from carlos_sim.injury_observation import explain_visible_rest
from test_actions import setup as setup_action_world


@pytest.mark.parametrize("injury,fatigue", [(True, 5), (False, 90)])
def test_same_observation_same_agnostic_interpretation(tmp_path, injury, fatigue):
    with SQLiteEventStore(tmp_path / "interpretation.sqlite") as db:
        setup_action_world(db, fatigue=fatigue)
        if injury:
            state = db.load("world")
            db.append("world", "private-injury", state.revision, [
                DomainEvent("InjuryRecorded", None, "trusted test bootstrap", 0, {
                    "injury_id": "nora-hidden-65", "subject_id": "nora",
                    "severity": 65, "source": "trusted_test_bootstrap",
                })
            ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("world")
        movement = NPCMovementService(db, clock)
        assert explain_visible_rest(db.load("world"), "basim", "nora") is None
        choice = NPCService(db, clock).decide(
            "world", "nora", command_id="decide", expected_revision=db.load("world").revision)
        assert choice.action == "rest"
        action = NPCActionService(db, clock).start(
            "world", "nora", "rest-nora", expected_revision=db.load("world").revision)
        assert explain_visible_rest(action.state, "basim", "nora") is None
        recorded = movement.observe(
            "world", "basim", command_id="look", expected_revision=action.state.revision, activity_enabled=True)
        interpretation = explain_visible_rest(recorded, "basim", "nora")
        assert interpretation == {
            "subject_id": "nora", "sign": "visible_resting",
            "site_id": "square", "observed_at": 0,
            "interpretation": "cause_unknown", "medical_conclusion": None,
        }
        assert "nora-hidden-65" not in repr(interpretation)
        assert "65" not in repr(interpretation)
        assert recorded.npcs["nora"]["beliefs"] == {}
        assert "visible-rest:nora:0" in recorded.npcs["basim"]["beliefs"]
        assert explain_visible_rest(recorded, "nora", "basim") is None
        assert db.verify("world").to_dict() == recorded.to_dict()


def test_historical_sighting_cannot_claim_present_cause_after_tick(tmp_path):
    with SQLiteEventStore(tmp_path / "interpret-time.sqlite") as db:
        setup_action_world(db, fatigue=90)
        clock = TimeEngine(db)
        clock.open_session("world")
        NPCService(db, clock).decide("world", "nora", command_id="d",
                                     expected_revision=db.load("world").revision)
        NPCActionService(db, clock).start("world", "nora", "rest",
                                          expected_revision=db.load("world").revision)
        movement = NPCMovementService(db, clock)
        seen = movement.observe("world", "basim", command_id="look",
                                expected_revision=db.load("world").revision, activity_enabled=True)
        assert explain_visible_rest(seen, "basim", "nora") is not None
        later = clock.advance("world", seconds=1, command_id="tick",
                              expected_revision=seen.revision).state
        assert explain_visible_rest(later, "basim", "nora") is None


@pytest.mark.parametrize("observer,target", [(None, "nora"), ("basim", None),
                                               ("basim", "basim"), ("unknown", "nora")])
def test_invalid_observer_cannot_obtain_interpretation(tmp_path, observer, target):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        setup_action_world(db, fatigue=90)
        assert explain_visible_rest(db.load("world"), observer, target) is None
