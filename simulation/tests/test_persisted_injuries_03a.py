"""03-A4: persistent bootstrap NPC injury provenance and fail-closed replay."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, WorldState
from carlos_sim.store import InvalidEvent
from test_property_02h1 import village


def injury(name="inj-1", subject="nora", severity=30, *, actor=None, time=0,
           source="trusted_test_bootstrap"):
    return DomainEvent(
        "InjuryRecorded", actor, "trusted test-world injury initialization",
        time, {"injury_id": name, "subject_id": subject,
               "severity": severity, "source": source},
    )


def test_npc_injury_is_persisted_and_replayed(tmp_path):
    path = tmp_path / "world.sqlite"
    with SQLiteEventStore(path) as db:
        village(db)
        rev = db.load("v").revision
        after = db.append("v", "initial-injury", rev, [injury()], bootstrap=True)
        assert after.injuries["inj-1"]["severity"] == 30
        assert after.injuries["inj-1"]["subject_id"] == "nora"
        assert after.injuries["inj-1"]["status"] == "active"
        assert after.injuries["inj-1"]["onset"] == 0
        assert db.verify("v").to_dict() == after.to_dict()
        assert db.snapshot("v").to_dict() == after.to_dict()
    with SQLiteEventStore(path) as reopened:
        assert reopened.load("v").injuries["inj-1"]["severity"] == 30
        assert reopened.load("v", use_snapshot=False).injuries["inj-1"]["severity"] == 30


@pytest.mark.parametrize("bad", [
    {"bootstrap": False},
    {"event": injury(actor="nora")},
    {"event": injury(subject="ghost")},
    {"event": injury(subject="nora", severity=0)},
    {"event": injury(subject="nora", severity=True)},
    {"event": injury(subject="nora", severity=101)},
    {"event": injury(source="untrusted")},
    {"event": injury(name="bad id")},
])
def test_invalid_injury_bootstrap_is_atomic(tmp_path, bad):
    with SQLiteEventStore(tmp_path / "world.sqlite") as db:
        village(db)
        before = db.load("v").to_dict()
        kwargs = {"event": injury(), "bootstrap": True}
        kwargs.update(bad)
        with pytest.raises(InvalidEvent):
            db.append("v", "bad", before["revision"],
                      [kwargs["event"]], bootstrap=kwargs["bootstrap"])
        assert db.load("v").to_dict() == before
        assert db.verify("v").to_dict() == before


def test_duplicate_id_rejected_and_snapshot_unchanged(tmp_path):
    with SQLiteEventStore(tmp_path / "world.sqlite") as db:
        village(db)
        first = db.append("v", "initial-injury", db.load("v").revision,
                          [injury()], bootstrap=True)
        with pytest.raises(InvalidEvent):
            db.append("v", "second-injury", first.revision, [injury()], bootstrap=True)
        assert db.verify("v").to_dict() == first.to_dict()


def test_injury_cannot_materialize_after_logical_time_zero(tmp_path):
    from carlos_sim.time_engine import TimeEngine
    with SQLiteEventStore(tmp_path / "world.sqlite") as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        clock.advance("v", seconds=1, command_id="time-forward",
                      expected_revision=db.load("v").revision)
        now = db.load("v")
        with pytest.raises(InvalidEvent):
            db.append("v", "late-injury", now.revision,
                      [injury(time=now.time)], bootstrap=True)
        assert db.verify("v").to_dict() == now.to_dict()


def test_strict_world_schema_and_invalid_injury_collection():
    base = WorldState("v").to_dict()
    assert base["schema_version"] == SCHEMA_VERSION == 34
    assert base["rules_version"] == RULES_VERSION == 45
    assert base["injuries"] == {}
    missing = dict(base)
    missing.pop("injuries")
    with pytest.raises(ValueError):
        WorldState.from_dict(missing)
    corrupt = dict(base)
    corrupt["injuries"] = {"i1": {
        "injury_id": "i1", "subject_id": "missing", "severity": 40,
        "status": "active", "onset": 0, "last_changed": 0,
    }}
    with pytest.raises(ValueError):
        WorldState.from_dict(corrupt)
