"""J1c2b founding institutions: real records, no judicial power."""
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.domain import WorldState, SCHEMA_VERSION, RULES_VERSION
from carlos_sim.local_institutions import institution_record
from carlos_sim.store import InvalidEvent, UnsupportedVersion
from test_property_02h1 import village


def event(ident="village-council", site="bakery", officer="adel",
          model="local_council", actor=None):
    return DomainEvent("LocalInstitutionRegistered", actor, "trusted founding record", 0, {
        "id": ident, "site_id": site,
        "representative_id": officer, "model": model,
    })


def register(db, ev, *, bootstrap=True):
    return db.append("v", "local-institution:" + str(db.load("v").revision),
                     db.load("v").revision, [ev], bootstrap=bootstrap)


@pytest.fixture
def scenario(tmp_path):
    with SQLiteEventStore(tmp_path/"institution.sqlite") as db:
        village(db)
        yield db


def test_founder_registers_factual_institution_without_title_or_court(scenario):
    db = scenario
    before = db.load("v")
    after = register(db, event())
    record = institution_record(after, "village-council")
    assert record["site_id"] == "bakery"
    assert record["representative_id"] == "adel"
    assert record["mandate"] == "existence_record_only"
    assert record["can_decide_title"] is False
    assert record["can_seize_property"] is False
    assert record["legal_title_status"] == "undetermined"
    assert record["authorized_court_id"] is None
    assert after.resources == before.resources
    assert after.property_title_origins == before.property_title_origins
    assert after.registered_claim_balances == before.registered_claim_balances
    assert db.verify("v").to_dict() == after.to_dict()


@pytest.mark.parametrize("changes", [
    {"ident": "bad id"}, {"site": "ghost"}, {"officer": "ghost"},
    {"officer": "omar"}, {"model": "supreme_court"},
    {"actor": "adel"},
])
def test_bad_institution_and_impostor_rejected_atomically(scenario, changes):
    db = scenario
    args = dict(ident="council", site="bakery", officer="adel",
                model="local_council", actor=None)
    args.update(changes)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        register(db, event(**args))
    assert db.verify("v").to_dict() == old


def test_untrusted_event_cannot_register_institution(scenario):
    db = scenario
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        register(db, event(), bootstrap=False)
    assert db.verify("v").to_dict() == before


def test_second_institution_same_site_rejected(scenario):
    db = scenario
    register(db, event())
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        register(db, event(ident="second", officer="salma"))
    assert db.verify("v").to_dict() == before


def test_rollback_if_second_event_invalid(scenario):
    db = scenario
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        db.append("v", "two-institutions", db.load("v").revision, [
            event(), event(ident="bad", officer="ghost")], bootstrap=True)
    assert db.verify("v").to_dict() == before


def test_snapshot_forgery_appointing_judge_rejected(scenario):
    db = scenario
    register(db, event())
    corrupt = db.load("v").to_dict()
    corrupt["local_institutions"]["village-council"]["mandate"] = "seize_bread"
    with pytest.raises(ValueError):
        WorldState.from_dict(corrupt)
    corrupt = db.load("v").to_dict()
    corrupt["local_institutions"]["village-council"]["representative_id"] = "ghost"
    with pytest.raises(ValueError):
        WorldState.from_dict(corrupt)


def test_snapshot_reopen_full_replay_and_record_detachment(tmp_path):
    path = tmp_path/"institution-persist.sqlite"
    with SQLiteEventStore(path) as db:
        village(db)
        register(db, event())
        saved = db.snapshot("v").to_dict()
        assert db.verify("v").to_dict() == saved
    with SQLiteEventStore(path) as db:
        assert db.verify("v").to_dict() == saved
        info = institution_record(db.load("v"), "village-council")
        info["mandate"] = "judge"
        assert institution_record(db.load("v"), "village-council")[
            "mandate"] == "existence_record_only"


def test_old_schema_state_rejected_without_accepting_old_version():
    s = WorldState(world_id="old").to_dict()
    s["schema_version"] = SCHEMA_VERSION - 1
    s["rules_version"] = RULES_VERSION - 1
    with pytest.raises(ValueError, match="unsupported world version"):
        WorldState.from_dict(s)
