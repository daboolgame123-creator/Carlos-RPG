"""03-A7c1: character-level perception contract, never medical omniscience."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.injury_observation import interpret_visible_symptom
from test_property_02h1 import village


def seed_injury(db, ident="nora-injury", severity=65):
    state = db.load("v")
    return db.append("v", "seed:" + ident, state.revision, [
        DomainEvent("InjuryRecorded", None, "trusted fixture", state.time, {
            "injury_id": ident, "subject_id": "nora", "severity": severity,
            "source": "trusted_test_bootstrap",
        })
    ], bootstrap=True)


def test_basim_sees_nora_limp_without_diagnosis_or_health_leak(tmp_path):
    path = tmp_path / "symptom.sqlite"
    with SQLiteEventStore(path) as db:
        village(db)
        seed_injury(db)
        before = db.load("v").to_dict()
        seen = interpret_visible_symptom(
            db.load("v"), "basim", "nora", "limping", observed_at=0)
        assert seen.visible_signal == "limping"
        assert seen.inference == "possible_mobility_problem"
        assert not seen.confirmed_diagnosis
        assert seen.location_id == "bakery"
        for secret in ("65", "nora-injury", "trusted_test_bootstrap"):
            assert secret not in repr(seen)
        assert db.load("v").to_dict() == before
        db.snapshot("v")
        assert db.verify("v").to_dict() == before
    with SQLiteEventStore(path) as reopened:
        assert reopened.load("v").to_dict() == before
        assert reopened.verify("v").to_dict() == before
        assert interpret_visible_symptom(
            reopened.load("v"), "basim", "nora", "limping",
            observed_at=0) == seen


def test_omar_remote_cannot_see_nora_and_no_belief_changes(tmp_path):
    with SQLiteEventStore(tmp_path / "remote.sqlite") as db:
        village(db)
        seed_injury(db)
        before = db.load("v").to_dict()
        with pytest.raises(ValueError, match="remote"):
            interpret_visible_symptom(db.load("v"), "omar", "nora",
                                      "limping", observed_at=0)
        assert db.verify("v").to_dict() == before
        assert db.load("v").npcs["omar"]["beliefs"] == {}


def test_no_injury_registry_required_and_no_automatic_sighting(tmp_path):
    with SQLiteEventStore(tmp_path / "healthy.sqlite") as db:
        village(db)
        state = db.load("v")
        assert state.injuries == {}
        assert state.npcs["basim"]["beliefs"] == {}
        # A manually supplied signal is only a candidate, not a stored fact.
        candidate = interpret_visible_symptom(
            state, "basim", "nora", "difficulty_moving", observed_at=0)
        assert candidate.inference == "possible_mobility_problem"
        assert db.verify("v").to_dict() == state.to_dict()
        assert db.load("v").npcs["basim"]["beliefs"] == {}


@pytest.mark.parametrize("observer,subject,signal,at", [
    ("basim", "basim", "limping", 0),
    ("ghost", "nora", "limping", 0),
    ("basim", "ghost", "limping", 0),
    ("basim", "nora", "diagnosed_fracture", 0),
    ("basim", "nora", "limping", 1),
    ("basim", "nora", "limping", True),
    ("basim", "nora", "", 0),
])
def test_invalid_character_or_signal_is_rejected(tmp_path, observer, subject, signal, at):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        village(db)
        before = db.load("v").to_dict()
        with pytest.raises(ValueError):
            interpret_visible_symptom(db.load("v"), observer, subject, signal,
                                      observed_at=at)
        assert db.load("v").to_dict() == before
