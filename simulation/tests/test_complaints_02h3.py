"""02-H3: actual desk registration, claimant intake, non-punitive acknowledgement."""
import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        NPCPropertyService, NPCComplaintService, personal_complaints)
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict
from test_property_02h1 import village


def ev(kind, data, actor=None, time=0):
    return DomainEvent(kind, actor, "02-H3 disposable village", time, data)


@pytest.fixture
def scene(tmp_path):
    with SQLiteEventStore(tmp_path / "desk.sqlite") as db:
        village(db)
        db.append("v", "desk-setup", db.load("v").revision, [
            ev("ComplaintDeskConfigured", {"site_id": "bakery", "officer_id": "layla"})
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("v")
        property_service = NPCPropertyService(db, clock)
        complaint_service = NPCComplaintService(db, clock)
        yield db, clock, property_service, complaint_service


def claim(db, service, claimant="nora", ident="claim1", subject="basim"):
    return service.claim("v", claimant, ident, "accusation", "bakery", "bread", 1,
                         subject_id=subject, expected_revision=db.load("v").revision).state


def file(db, service, who="nora", ident="complaint1", claim_id="claim1", site="bakery"):
    return service.file("v", who, ident, claim_id, site,
                        expected_revision=db.load("v").revision).state


def ack(db, service, who="layla", ident="complaint1"):
    return service.acknowledge("v", who, ident,
                               expected_revision=db.load("v").revision).state


def test_false_accusation_received_and_acknowledged_without_guilt_or_money(scene):
    db, clock, property_service, complaints = scene
    claim(db, property_service, subject="adel")
    original = db.load("v").resources
    received = file(db, complaints)
    assert received.property_complaints["complaint1"]["status"] == "received"
    assert received.property_claims["claim1"]["status"] == "unverified"
    assert received.resources == original
    done = ack(db, complaints)
    assert done.property_complaints["complaint1"]["status"] == "acknowledged"
    assert done.property_complaints["complaint1"]["acknowledged_by"] == "layla"
    assert done.property_claims["claim1"]["subject_id"] == "adel"
    assert done.property_claims["claim1"]["status"] == "unverified"
    assert done.resources == original
    assert len(personal_complaints(done, "nora")) == 1
    assert personal_complaints(done, "salma") == ()
    assert db.verify("v").to_dict() == done.to_dict()


@pytest.mark.parametrize("who,claim_id,site", [
    ("adel", "claim1", "bakery"), ("omar", "claim1", "bakery"),
    ("nora", "missing", "bakery"), ("nora", "claim1", "square"),
])
def test_unrelated_claimant_remote_or_nonexistent_desk_cannot_file(scene, who, claim_id, site):
    db, _, ps, service = scene
    claim(db, ps)
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        file(db, service, who=who, claim_id=claim_id, site=site)
    assert db.load("v").to_dict() == before


def test_assigned_officer_only_and_ack_once(scene):
    db, _, ps, service = scene
    claim(db, ps)
    file(db, service)
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        ack(db, service, who="adel")
    assert db.load("v").to_dict() == before
    result = ack(db, service)
    with pytest.raises(DuplicateCommand):
        ack(db, service)
    assert db.load("v").to_dict() == result.to_dict()


def test_no_second_complaint_for_same_claim(scene):
    db, _, ps, service = scene
    claim(db, ps)
    file(db, service)
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        file(db, service, ident="second")
    assert db.load("v").to_dict() == before


def test_no_officer_appointment_through_ordinary_append(scene):
    db, _, ps, service = scene
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        db.append("v", "fake-office", db.load("v").revision, [
            ev("ComplaintDeskConfigured", {"site_id": "square", "officer_id": "omar"})
        ])
    assert db.load("v").to_dict() == before


def test_unprivileged_complaint_intake_and_ack_rejected(scene):
    db, _, ps, service = scene
    claim(db, ps)
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        db.append("v", "fake-complaint", db.load("v").revision, [
            ev("PropertyComplaintReceived", {
                "id": "forged", "claim_id": "claim1", "desk_site_id": "bakery"
            }, "nora")
        ])
    assert db.load("v").to_dict() == before
    file(db, service)
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        db.append("v", "fake-ack", db.load("v").revision, [
            ev("PropertyComplaintAcknowledged", {"id": "complaint1"}, "layla")
        ])
    assert db.load("v").to_dict() == before


def test_future_or_unfiled_claim_is_not_official_complaint(scene):
    db, _, ps, service = scene
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        file(db, service)
    assert db.load("v").to_dict() == before


def test_duplicate_desk_or_officer_never_accepted(scene):
    db, _, ps, service = scene
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        db.append("v", "double-desk", db.load("v").revision, [
            ev("ComplaintDeskConfigured", {"site_id": "bakery", "officer_id": "salma"})
        ], bootstrap=True)
    assert db.load("v").to_dict() == before


def test_stale_revision_cannot_backdate_intake(scene):
    db, _, ps, service = scene
    claim(db, ps)
    before = db.load("v").to_dict()
    with pytest.raises(RevisionConflict):
        service.file("v", "nora", "complaint1", "claim1", "bakery",
                     expected_revision=db.load("v").revision - 1)
    assert db.load("v").to_dict() == before


def test_replay_and_snapshot_preserve_private_complaint(scene):
    db, _, ps, service = scene
    claim(db, ps)
    file(db, service)
    done = ack(db, service)
    db.snapshot("v")
    assert db.load("v").to_dict() == done.to_dict()
    assert db.verify("v").to_dict() == done.to_dict()
