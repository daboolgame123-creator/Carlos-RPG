"""J1c2b-LAW: proposals for registered institutions have NO legal effect."""
import pytest

from carlos_sim import SQLiteEventStore
from carlos_sim.institution_authority_draft import (
    prepare_registered_institution_authority_draft as propose,
)
from test_property_02h1 import village
from test_local_institutions_04a_j1c2b import event, register


@pytest.fixture
def institution_db(tmp_path):
    with SQLiteEventStore(tmp_path / "law-proposal.sqlite") as db:
        village(db)
        register(db, event())
        yield db


def test_registered_institution_proposal_is_powerless_and_read_only(institution_db):
    db = institution_db
    before = db.verify("v").to_dict()
    proposal = propose(db.load("v"), institution_id="village-council", effective_from=1)
    assert proposal["site_id"] == "bakery"
    assert proposal["representative_id"] == "adel"
    assert proposal["authority_model_proposed"] == "local_council"
    assert proposal["charter_status"] == "unapproved_draft"
    assert proposal["registration_mandate"] == "existence_record_only"
    assert proposal["authorized_issuer_id"] is None
    assert proposal["representative_consent_recorded"] is False
    assert proposal["jurisdiction_effective"] is False
    for permission in ("can_make_binding_law", "can_decide_title",
                       "can_seize_property", "can_delegate_authority"):
        assert proposal[permission] is False
    assert proposal["legally_enforceable_owner"] is None
    assert db.verify("v").to_dict() == before


@pytest.mark.parametrize("identifier,when", [
    ("missing", 1), ("", 1), (None, 1), (True, 1),
    ("village-council", 0), ("village-council", -1),
    ("village-council", True), ("village-council", 1.0),
    ("village-council", 2**63),
])
def test_invalid_proposal_rejected_without_mutation(institution_db, identifier, when):
    db = institution_db
    before = db.verify("v").to_dict()
    with pytest.raises(ValueError):
        propose(db.load("v"), institution_id=identifier, effective_from=when)
    assert db.verify("v").to_dict() == before


def test_replay_and_snapshot_do_not_create_a_charter(institution_db):
    db = institution_db
    before = db.verify("v").to_dict()
    expected = propose(db.load("v"), institution_id="village-council", effective_from=1)
    db.snapshot("v")
    assert propose(db.verify("v"), institution_id="village-council", effective_from=1) == expected
    assert propose(db.load("v", use_snapshot=False),
                   institution_id="village-council", effective_from=1) == expected
    expected["next_prerequisites"].clear()
    actual = propose(db.load("v"), institution_id="village-council", effective_from=1)
    assert len(actual["next_prerequisites"]) == 4
    assert db.verify("v").to_dict() == before
