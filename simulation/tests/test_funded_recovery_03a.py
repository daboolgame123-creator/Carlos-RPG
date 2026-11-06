"""03-A6: funded recovery succeeds only at due time and replays exactly."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.store import InvalidEvent, UnsupportedVersion
from carlos_sim.time_engine import TimeEngine
from carlos_sim.injury_service import NPCExhaustionInjuryService
from carlos_sim.recovery_service import NPCRecoveryService
from test_property_02h1 import village


def scene(tmp_path, stock=2):
    db = SQLiteEventStore(tmp_path / "care.sqlite")
    village(db)
    before = db.load("v")
    db.append("v", "caregiver-stock", before.revision, [
        DomainEvent("ResourceChanged", None, "starting owned food", 0,
                    {"owner_id": "adel", "resource": "food", "previous": None,
                     "current": stock, "source": "initialization"}),
    ], bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session("v")
    w = db.load("v")
    db.append("v", "nora-exhausted", w.revision, [
        DomainEvent("NPCNeedChanged", None, "verified fatigue increase", 0,
                    {"npc_id": "nora", "need": "fatigue",
                     "previous": 5, "current": 95}),
    ], npc_authorized=True)
    NPCExhaustionInjuryService(db, clock).record(
        "v", subject_id="nora", injury_id="nora-fatigue",
        command_id="initial-injury", expected_revision=db.load("v").revision)
    return db, clock, NPCRecoveryService(db, clock)


def begin(db, service, tid="care-one"):
    return service.start("v", treatment_id=tid, injury_id="nora-fatigue",
                         caregiver_id="adel", command_id="start-"+tid,
                         expected_revision=db.load("v").revision)


def test_funded_recovery_waits_exact_time_and_replays_after_restart(tmp_path):
    db, clock, svc = scene(tmp_path)
    try:
        before = db.load("v")
        assert before.injuries["nora-fatigue"]["severity"] == 25
        started = begin(db, svc)
        assert started.resources["adel"]["food"] == before.resources["adel"]["food"] - 1
        assert started.injuries["nora-fatigue"]["severity"] == 25
        assert started.treatments["care-one"]["status"] == "pending"
        assert started.scheduled["heal.care-one"]["due"] == 600
        partial = clock.advance("v", seconds=599, command_id="wait-599",
                                expected_revision=started.revision).state
        assert partial.injuries["nora-fatigue"]["severity"] == 25
        assert partial.treatments["care-one"]["status"] == "pending"
        finished = clock.advance("v", seconds=1, command_id="wait-1",
                                 expected_revision=partial.revision).state
        assert finished.injuries["nora-fatigue"]["severity"] == 15
        assert finished.injuries["nora-fatigue"]["last_changed"] == 600
        assert finished.treatments["care-one"]["status"] == "completed"
        assert "heal.care-one" not in finished.scheduled
        assert finished.resources["adel"]["food"] == 1
        assert db.verify("v").to_dict() == finished.to_dict()
        assert db.snapshot("v").to_dict() == finished.to_dict()
    finally:
        db.close()
    with SQLiteEventStore(tmp_path / "care.sqlite") as reopened:
        assert reopened.verify("v").injuries["nora-fatigue"]["severity"] == 15
        assert reopened.load("v", use_snapshot=False).to_dict() == reopened.load("v").to_dict()


def test_double_treatment_and_missing_funds_are_atomic(tmp_path):
    db, clock, svc = scene(tmp_path)
    try:
        first = begin(db, svc)
        with pytest.raises(InvalidEvent):
            begin(db, svc, "care-two")
        assert db.verify("v").to_dict() == first.to_dict()
    finally:
        db.close()
    separate = tmp_path / "separate"
    separate.mkdir()
    db, clock, svc = scene(separate, stock=0)
    try:
        before = db.load("v").to_dict()
        with pytest.raises(InvalidEvent):
            begin(db, svc)
        assert db.verify("v").to_dict() == before
    finally:
        db.close()


def test_generic_signal_cannot_forge_or_cancel_paid_recovery(tmp_path):
    db, clock, svc = scene(tmp_path)
    try:
        before = db.load("v")
        with pytest.raises(InvalidEvent):
            db.append("v", "fake-appt", before.revision, [
                DomainEvent("ScheduledEventCreated", None, "fake recovery", 0,
                            {"id": "heal.fake", "due": 600,
                             "order": before.next_schedule_order, "kind": "signal",
                             "payload": {"__npc_recovery": "care-one"},
                             "interrupt": False}),
            ])
        begun = begin(db, svc)
        with pytest.raises(InvalidEvent):
            db.append("v", "cancel", begun.revision, [
                DomainEvent("ScheduledEventCancelled", None, "unpaid refund", 0,
                            {"id": "heal.care-one"}),
            ])
        assert db.verify("v").to_dict() == begun.to_dict()
    finally:
        db.close()


@pytest.mark.parametrize("value", [True, 0, -1, "10", 999])
def test_untrusted_effect_cannot_change_supplies_or_severity(tmp_path, value):
    db, clock, svc = scene(tmp_path)
    try:
        w = db.load("v")
        event = DomainEvent("RecoveryStarted", "adel", "forged remedy", 0, {
            "id": "fake", "injury_id": "nora-fatigue",
            "subject_id": "nora", "caregiver_id": "adel", "site_id": "bakery",
            "schedule_id": "heal.fake", "started_at": 0, "due_at": 600,
            "resource": "food", "quantity": 1, "improvement": value,
        })
        with pytest.raises(InvalidEvent):
            db.append("v", "forged", w.revision, [event], recovery_authorized=True)
        assert db.verify("v").to_dict() == w.to_dict()
    finally:
        db.close()


def test_previous_31_39_world_refused_without_migration(tmp_path):
    db, clock, svc = scene(tmp_path)
    try:
        db.db.execute("UPDATE worlds SET schema_version=31, rules_version=39 WHERE id='v'")
        before = db.db.execute("SELECT * FROM worlds WHERE id='v'").fetchone()
        with pytest.raises(UnsupportedVersion):
            db.load("v")
        assert db.db.execute("SELECT * FROM worlds WHERE id='v'").fetchone() == before
    finally:
        db.close()
