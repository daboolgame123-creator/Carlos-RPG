"""03-A7b: severe own injury changes real NPC decisions, not other NPCs."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.actions import NPCActionService
from carlos_sim.domain import WorldState
from carlos_sim.npc import NPCService, choose_action
from carlos_sim.store import InvalidEvent
from carlos_sim.time_engine import TimeEngine
from test_property_02h1 import village


def setup(tmp_path):
    db = SQLiteEventStore(tmp_path / "injury-choice.sqlite")
    village(db)
    clock = TimeEngine(db)
    clock.open_session("v")
    return db, clock


def injury(db, severity=25):
    state = db.load("v")
    return db.append("v", "injury", state.revision, [
        DomainEvent("InjuryRecorded", None, "trusted initial injury", state.time,
                    {"injury_id": "nora-hurt", "subject_id": "nora",
                     "severity": severity, "source": "trusted_test_bootstrap"})
    ], bootstrap=True)


def test_injured_npc_rest_decision_is_persisted_and_replayed(tmp_path):
    db, clock = setup(tmp_path)
    try:
        before = db.load("v")
        unaffected = choose_action(before, "basim")
        injury(db, severity=25)
        wounded = db.load("v")
        choice = choose_action(wounded, "nora", survival_enabled=True, foraging_enabled=True)
        assert choice.action == "rest"
        assert "self_active_injury_rest" in choice.reason
        assert choose_action(wounded, "basim") == unaffected
        issued = NPCService(db, clock).decide(
            "v", "nora", command_id="decide-nora",
            expected_revision=wounded.revision)
        assert issued == choice
        after = db.load("v")
        assert after.npcs["nora"]["last_decision"]["action"] == "rest"
        assert db.verify("v").to_dict() == after.to_dict()
        assert db.snapshot("v").to_dict() == after.to_dict()
    finally:
        db.close()
    with SQLiteEventStore(tmp_path / "injury-choice.sqlite") as reopened:
        assert reopened.verify("v").npcs["nora"]["last_decision"]["action"] == "rest"
        assert reopened.load("v", use_snapshot=False).to_dict() == reopened.load("v").to_dict()


def test_recorded_rest_does_not_heal_injury(tmp_path):
    db, clock = setup(tmp_path)
    try:
        injury(db)
        NPCService(db, clock).decide(
            "v", "nora", command_id="self-rest",
            expected_revision=db.load("v").revision)
        started = NPCActionService(db, clock).start(
            "v", "nora", "self-rest-action",
            expected_revision=db.load("v").revision).state
        assert started.injuries["nora-hurt"]["severity"] == 25
        finished = clock.advance(
            "v", seconds=120, command_id="rest-time",
            expected_revision=started.revision).state
        assert finished.injuries["nora-hurt"]["severity"] == 25
        assert db.verify("v").to_dict() == finished.to_dict()
    finally:
        db.close()


def test_forced_injured_npc_work_decision_is_rejected_atomically(tmp_path):
    db, clock = setup(tmp_path)
    try:
        injury(db)
        before = db.load("v")
        fake = DomainEvent("NPCDecisionRecorded", "nora", "forged healthy choice", before.time,
                           {"npc_id": "nora", "action": "work", "score": 65,
                            "reason": "utility[work]=65; belief_danger=0; npc=nora",
                            "next_decision_at": before.time + 60})
        with pytest.raises(InvalidEvent):
            db.append("v", "forged-work", before.revision, [fake], npc_authorized=True)
        assert db.verify("v").to_dict() == before.to_dict()
    finally:
        db.close()


def test_minor_injury_does_not_rewrite_existing_utility_choice(tmp_path):
    db, clock = setup(tmp_path)
    try:
        before = db.load("v")
        expected = choose_action(before, "nora")
        injury(db, severity=10)
        assert choose_action(db.load("v"), "nora") == expected
        assert db.verify("v").injuries["nora-hurt"]["severity"] == 10
    finally:
        db.close()
