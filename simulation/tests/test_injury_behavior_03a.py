"""03-A7a self-only advisory: strict knowledge isolation and no auto-heal."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.domain import WorldState
from carlos_sim.injury_behavior import assess_own_injuries
from test_property_02h1 import village


def initialized_world(tmp_path):
    db = SQLiteEventStore(tmp_path / "self-injury.sqlite")
    village(db)
    return db


def bootstrap(db, injury_id, subject, severity):
    w = db.load("v")
    event = DomainEvent(
        "InjuryRecorded", None, "known time-zero injury source", w.time,
        {"injury_id": injury_id, "subject_id": subject, "severity": severity,
         "source": "trusted_test_bootstrap"},
    )
    return db.append("v", "init:" + injury_id, w.revision, [event], bootstrap=True)


def test_self_only_advisory_no_peer_knowledge_leak(tmp_path):
    with initialized_world(tmp_path) as db:
        bootstrap(db, "nora-bad", "nora", 65)
        w = db.load("v")
        prior = w.to_dict()
        own = assess_own_injuries(w, "nora")
        other = assess_own_injuries(w, "basim")
        assert (own.active_injury_count, own.maximum_severity) == (1, 65)
        assert own.should_prioritize_rest is True
        assert other.active_injury_count == 0
        assert other.maximum_severity == 0
        assert other.should_prioritize_rest is False
        assert other.reason == "no_self_injury_recorded"
        assert "nora" not in repr(other)
        assert w.to_dict() == prior
        assert db.verify("v").to_dict() == prior


def test_injury_is_not_healed_by_read_only_assessment(tmp_path):
    with initialized_world(tmp_path) as db:
        bootstrap(db, "nora-low", "nora", 10)
        w = db.load("v")
        for _ in range(3):
            opinion = assess_own_injuries(w, "nora")
            assert opinion.reason == "self_known_minor_injury_caution"
            assert opinion.should_prioritize_rest is False
        assert w.injuries["nora-low"]["severity"] == 10
        assert db.load("v").injuries["nora-low"]["severity"] == 10
        assert db.verify("v").to_dict() == w.to_dict()


def test_multiple_self_injuries_ignore_unrelated_cases(tmp_path):
    with initialized_world(tmp_path) as db:
        bootstrap(db, "nora-small", "nora", 5)
        bootstrap(db, "basim-large", "basim", 90)
        bootstrap(db, "nora-medium", "nora", 25)
        report = assess_own_injuries(db.load("v"), "nora")
        assert (report.active_injury_count, report.maximum_severity) == (2, 25)
        assert report.should_prioritize_rest is True
        assert "basim" not in repr(report)
        assert db.verify("v").injuries["basim-large"]["severity"] == 90


@pytest.mark.parametrize("invalid", [None, False, True, 0, "", "unknown", "Nora"])
def test_invalid_npc_cannot_obtain_health_advisory(tmp_path, invalid):
    with initialized_world(tmp_path) as db:
        before = db.load("v").to_dict()
        with pytest.raises(ValueError):
            assess_own_injuries(db.load("v"), invalid)
        assert db.load("v").to_dict() == before


def test_invalid_world_not_accepted_as_trusted_state():
    with pytest.raises(ValueError):
        assess_own_injuries({"npcs": {"nora": {}}}, "nora")


def test_fresh_world_is_feature_off_and_unchanged():
    state = WorldState("isolated")
    with pytest.raises(ValueError):
        assess_own_injuries(state, "nora")
    assert state.injuries == {}
    assert state.treatments == {}
