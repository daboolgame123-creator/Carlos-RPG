"""J1c2b: a drafted local law must never become legal authority by itself."""
import pytest

from carlos_sim.title_law_draft import prepare_local_title_law_draft
from test_rights_04a_j1a import scene, origin, register


RULE = "requires_preexisting_verified_title_and_mutual_consent"


def proposal(world, **changes):
    args = {
        "site_id": "bakery",
        "authority_model": "customary_assembly",
        "effective_from": world.time + 1,
        "transfer_rule": RULE,
    }
    args.update(changes)
    return prepare_local_title_law_draft(world, **args)


def test_draft_remains_unapproved_and_has_no_legal_force(scene):
    db, clock = scene
    register(db, [origin()])
    before = db.load("v").to_dict()
    item = proposal(db.load("v"))
    assert item["review_status"] == "unapproved_draft"
    assert item["installed_in_world"] is False
    assert item["jurisdiction_effective"] is False
    assert item["authorized_institution_id"] is None
    assert item["legally_enforceable_owner"] is None
    assert item["retroactive"] is False
    assert db.verify("v").to_dict() == before


@pytest.mark.parametrize("overrides", [
    {"site_id": "ghost"},
    {"site_id": ""},
    {"site_id": None},
    {"authority_model": "omniscient_judge"},
    {"authority_model": None},
    {"effective_from": 0},
    {"effective_from": -1},
    {"effective_from": True},
    {"effective_from": 2**63},
    {"transfer_rule": "ownership_follows_possession"},
    {"transfer_rule": "historical_claim_automatically_creates_title"},
    {"transfer_rule": None},
])
def test_invalid_or_retroactive_local_law_draft_rejected_without_mutation(scene, overrides):
    db, clock = scene
    before = db.load("v").to_dict()
    with pytest.raises(ValueError):
        proposal(db.load("v"), **overrides)
    assert db.verify("v").to_dict() == before


@pytest.mark.parametrize("authority", [
    "customary_assembly", "local_council", "lordly_authority",
])
def test_authority_is_only_a_proposed_model_not_granted_power(scene, authority):
    db, clock = scene
    item = proposal(db.load("v"), authority_model=authority)
    assert item["authority_model_proposed"] == authority
    assert item["authorized_institution_id"] is None
    assert item["jurisdiction_effective"] is False


def test_future_effective_time_is_logical_not_wall_clock(scene):
    db, clock = scene
    clock.advance("v", seconds=5, command_id="draftclock",
                  expected_revision=db.load("v").revision)
    draft = proposal(db.load("v"), effective_from=6)
    assert draft["effective_from_proposed"] == 6
    with pytest.raises(ValueError):
        proposal(db.load("v"), effective_from=5)


def test_snapshot_and_replay_parity_without_any_persistent_law(scene):
    db, clock = scene
    register(db, [origin()])
    initial = db.verify("v").to_dict()
    draft = proposal(db.load("v"))
    db.snapshot("v")
    assert proposal(db.load("v", use_snapshot=False)) == draft
    assert proposal(db.verify("v")) == draft
    assert db.verify("v").to_dict() == initial
    draft["next_prerequisites"].clear()
    assert len(proposal(db.load("v"))["next_prerequisites"]) == 4
