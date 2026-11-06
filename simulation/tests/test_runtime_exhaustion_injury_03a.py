"""03-A5 trusted exhaustion injury: persistent provenance and hostile attempts."""
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.injury_service import NPCExhaustionInjuryService
from carlos_sim.time_engine import TimeEngine
from carlos_sim.store import InvalidEvent, IntegrityError
from test_property_02h1 import village


def tired(db, value=95):
    state = db.load("v")
    e = DomainEvent("NPCNeedChanged", None, "trusted fatigue scenario", state.time, {
        "npc_id": "nora", "need": "fatigue", "previous": 5, "current": value,
    })
    db.append("v", "fatigue", state.revision, [e], npc_authorized=True)


def setup(tmp_path, fatigue=95):
    db = SQLiteEventStore(tmp_path / "injuries.sqlite")
    village(db)
    clock = TimeEngine(db)
    clock.open_session("v")
    tired(db, fatigue)
    return db, NPCExhaustionInjuryService(db, clock)


def incident(db, *, injury_id="fatigue-nora", severity=25, subject_id="nora",
             source="exhaustion", fatigue=95):
    return DomainEvent("InjuryRecorded", None, "untrusted candidate", db.load("v").time,
                       {"injury_id": injury_id, "subject_id": subject_id,
                        "severity": severity, "source": source,
                        "fatigue_at_onset": fatigue})


def test_runtime_injury_survives_snapshot_reopen_and_full_replay(tmp_path):
    db, svc = setup(tmp_path)
    try:
        before = db.load("v")
        after = svc.record("v", subject_id="nora", injury_id="fatigue-nora",
                           command_id="collapse-1", expected_revision=before.revision)
        assert after.injuries["fatigue-nora"]["severity"] == 25
        assert after.injuries["fatigue-nora"]["onset"] == after.time
        assert after.resources == before.resources
        assert db.verify("v").to_dict() == after.to_dict()
        assert db.snapshot("v").to_dict() == after.to_dict()
    finally:
        db.close()
    with SQLiteEventStore(tmp_path / "injuries.sqlite") as restored:
        assert restored.verify("v").injuries["fatigue-nora"]["severity"] == 25
        assert restored.load("v", use_snapshot=False).to_dict() == restored.load("v").to_dict()


def test_untrusted_runtime_event_cannot_record_injury(tmp_path):
    db, svc = setup(tmp_path)
    try:
        before = db.load("v")
        with pytest.raises(InvalidEvent):
            db.append("v", "forge", before.revision, [incident(db)])
        assert db.verify("v").to_dict() == before.to_dict()
    finally:
        db.close()


@pytest.mark.parametrize("changes", [
    {"severity": 26}, {"severity": 0}, {"severity": True},
    {"source": "fall"}, {"fatigue": 96}, {"fatigue": True},
    {"subject_id": "ghost"}, {"injury_id": "bad id"},
])
def test_untrusted_payload_cannot_bypass_rule_even_with_capability(tmp_path, changes):
    db, svc = setup(tmp_path)
    try:
        before = db.load("v")
        with pytest.raises(InvalidEvent):
            db.append("v", "fake", before.revision, [incident(db, **changes)],
                      injury_authorized=True)
        assert db.verify("v").to_dict() == before.to_dict()
    finally:
        db.close()


def test_duplicate_active_exhaustion_rejected(tmp_path):
    db, svc = setup(tmp_path)
    try:
        first = svc.record("v", subject_id="nora", injury_id="one",
                           command_id="first", expected_revision=db.load("v").revision)
        with pytest.raises(InvalidEvent):
            svc.record("v", subject_id="nora", injury_id="two",
                       command_id="second", expected_revision=first.revision)
        assert db.verify("v").to_dict() == first.to_dict()
    finally:
        db.close()


def test_fatigue_below_threshold_cannot_create_injury(tmp_path):
    db, svc = setup(tmp_path, fatigue=85)
    try:
        with pytest.raises(ValueError):
            svc.record("v", subject_id="nora", injury_id="no-injury",
                       command_id="first", expected_revision=db.load("v").revision)
        assert db.verify("v").injuries == {}
    finally:
        db.close()


def test_tampering_command_capability_breaks_full_replay(tmp_path):
    db, svc = setup(tmp_path)
    try:
        svc.record("v", subject_id="nora", injury_id="one",
                   command_id="first", expected_revision=db.load("v").revision)
        db.db.execute("UPDATE commands SET injury_authorized=0 WHERE world_id='v' AND command_id='first'")
        with pytest.raises(IntegrityError):
            db.load("v", use_snapshot=False)
    finally:
        db.close()


def test_runtime_injury_requires_active_session(tmp_path):
    db, svc = setup(tmp_path)
    try:
        svc.clock.close_session("v")
        before = db.load("v").to_dict()
        with pytest.raises(PermissionError):
            svc.record("v", subject_id="nora", injury_id="no-session",
                       command_id="closed", expected_revision=before["revision"])
        with pytest.raises(InvalidEvent):
            db.append("v", "bypass", before["revision"], [incident(db)],
                      injury_authorized=True)
        assert db.verify("v").to_dict() == before
    finally:
        db.close()

