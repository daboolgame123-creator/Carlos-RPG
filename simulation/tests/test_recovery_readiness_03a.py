"""03-A3: readiness cannot invent recovery authority or remote care."""
import pytest
from carlos_sim import SQLiteEventStore
from carlos_sim.injury_transitions import draft_injury_record
from carlos_sim.recovery_readiness import assess_npc_recovery_readiness as assess
from test_property_02h1 import village


@pytest.fixture
def scene(tmp_path):
    with SQLiteEventStore(tmp_path / "recovery-readiness.sqlite") as db:
        village(db)
        yield db


def record(w, who="adel"):
    return draft_injury_record(injury_id="sample-injury", subject_id=who,
                               severity=30, onset=w.time)


def test_local_self_care_is_only_a_readiness_proposal(scene):
    db = scene
    w = db.load("v")
    before = db.verify("v").to_dict()
    p = assess(w, injury=record(w), caregiver_id="adel", duration=60,
               improvement=10)
    assert p["site_id"] == "bakery"
    assert p["physical_eligibility_checked"] is True
    assert p["due_at_proposed"] == w.time + 60
    assert p["scheduled_event_created"] is False
    assert p["recovery_authorized"] is False
    assert p["injury_persisted_and_source_verified"] is False
    assert db.verify("v").to_dict() == before


def test_remote_caregiver_rejected_without_mutation(scene):
    db = scene
    w = db.load("v")
    before = db.verify("v").to_dict()
    # omar is remote from adel in the established village fixture.
    with pytest.raises(ValueError):
        assess(w, injury=record(w), caregiver_id="omar", duration=60,
               improvement=10)
    assert db.verify("v").to_dict() == before


@pytest.mark.parametrize("overrides", [
    {"caregiver_id": "ghost"}, {"caregiver_id": True},
    {"duration": 0}, {"duration": True}, {"duration": -1},
    {"improvement": 0}, {"improvement": True}, {"improvement": 101},
])
def test_invalid_proposals_do_not_write_to_world(scene, overrides):
    db = scene
    w = db.load("v")
    before = db.verify("v").to_dict()
    args = dict(injury=record(w), caregiver_id="adel", duration=60, improvement=10)
    args.update(overrides)
    with pytest.raises(ValueError):
        assess(w, **args)
    assert db.verify("v").to_dict() == before


def test_future_and_finished_injury_do_not_pass_readiness(scene):
    db = scene
    w = db.load("v")
    future = draft_injury_record(injury_id="i-f", subject_id="adel", severity=5,
                                 onset=w.time + 1)
    with pytest.raises(ValueError):
        assess(w, injury=future, caregiver_id="adel", duration=1, improvement=1)
    finished = record(w)
    finished.update(status="recovered", severity=0)
    with pytest.raises(ValueError):
        assess(w, injury=finished, caregiver_id="adel", duration=1, improvement=1)
