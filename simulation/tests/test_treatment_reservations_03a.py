"""03-A8a: pending paid care cannot be stranded without a schedule."""
import pytest

from carlos_sim import DomainEvent
from carlos_sim.recovery_events import validate_treatment_reservations
from carlos_sim.store import InvalidEvent
from test_funded_recovery_03a import scene, begin


def treatment_event(state):
    return DomainEvent("RecoveryStarted", "adel", "trusted treatment", state.time, {
        "id": "care-one", "injury_id": "nora-fatigue", "subject_id": "nora",
        "caregiver_id": "adel", "site_id": "bakery", "schedule_id": "heal.care-one",
        "started_at": state.time, "due_at": state.time + 600,
        "resource": "food", "quantity": 1, "improvement": 10,
    })


def test_paid_treatment_without_appointment_is_rejected_atomically(tmp_path):
    db, clock, service = scene(tmp_path)
    try:
        before = db.load("v")
        with pytest.raises(InvalidEvent, match="no corresponding appointment"):
            db.append("v", "stranded", before.revision,
                      [treatment_event(before)], recovery_authorized=True)
        after = db.load("v")
        assert after.to_dict() == before.to_dict()
        assert after.resources["adel"]["food"] == before.resources["adel"]["food"]
        assert db.verify("v").to_dict() == before.to_dict()
        assert db.db.execute(
            "SELECT COUNT(*) FROM commands WHERE command_id='stranded'"
        ).fetchone()[0] == 0
    finally:
        db.close()


def test_registered_care_has_single_matching_schedule(tmp_path):
    db, clock, service = scene(tmp_path)
    try:
        after = begin(db, service)
        validate_treatment_reservations(after)
        assert db.verify("v").to_dict() == after.to_dict()
        assert len([x for x in after.scheduled.values()
                    if "__npc_recovery" in x["payload"]]) == 1
    finally:
        db.close()


def test_detached_corrupt_recovery_projection_rejected(tmp_path):
    db, clock, service = scene(tmp_path)
    try:
        after = begin(db, service)
        bad = after.to_dict()
        bad["scheduled"].pop("heal.care-one")
        with pytest.raises(ValueError, match="no corresponding appointment"):
            validate_treatment_reservations(bad)
        assert db.load("v").to_dict() == after.to_dict()
    finally:
        db.close()


def test_fake_duplicate_or_orphan_appointment_rejected(tmp_path):
    db, clock, service = scene(tmp_path)
    try:
        after = begin(db, service)
        duplicate = after.to_dict()
        duplicate["scheduled"]["heal.other"] = {
            **duplicate["scheduled"]["heal.care-one"],
            "order": duplicate["scheduled"]["heal.care-one"]["order"] + 1,
        }
        with pytest.raises(ValueError):
            validate_treatment_reservations(duplicate)
        orphan = after.to_dict()
        orphan["scheduled"]["heal.care-one"]["payload"] = {"__npc_recovery": "ghost"}
        with pytest.raises(ValueError, match="orphaned"):
            validate_treatment_reservations(orphan)
        assert db.verify("v").to_dict() == after.to_dict()
    finally:
        db.close()
