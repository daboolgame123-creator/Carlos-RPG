"""J1c2b first slice: evidence is not current legal title."""
import pytest

from carlos_sim import NPCPropertyService, NPCMarketService, NPCRegisteredClaimService
from carlos_sim.title_evidence import historical_title_evidence
from test_rights_04a_j1a import scene, origin, register


def _rev(db):
    return db.load("v").revision


def test_original_registered_provenance_does_not_mint_legal_title(scene):
    db, clock = scene
    register(db, [origin()])
    before = db.load("v").to_dict()
    evidence = historical_title_evidence(db.load("v"), "origin-bread")
    assert evidence["current_recorded_claim_balances"] == {"bakery": 2}
    assert evidence["legal_title_status"] == "undetermined"
    assert evidence["legally_enforceable_owner"] is None
    assert evidence["legal_rule_applied"] is None
    assert db.load("v").to_dict() == before


def test_mutual_historical_assignment_does_not_grant_legal_title(scene):
    db, clock = scene
    register(db, [origin()])
    service = NPCRegisteredClaimService(db, clock)
    service.offer("v", "adel", "transfer", "origin-bread", "bakery", "salma",
                  1, expires_at=100, expected_revision=_rev(db))
    pending = historical_title_evidence(db.load("v"), "origin-bread")
    assert pending["current_recorded_claim_balances"] == {"bakery": 2}
    assert len(pending["open_historical_assignment_offers"]) == 1
    service.accept("v", "salma", "transfer", expected_revision=_rev(db))
    final = historical_title_evidence(db.verify("v"), "origin-bread")
    assert final["current_recorded_claim_balances"] == {"bakery": 1, "salma": 1}
    assert len(final["accepted_historical_assignments"]) == 1
    assert final["open_historical_assignment_offers"] == []
    assert final["legally_enforceable_owner"] is None
    assert final["legal_title_status"] == "undetermined"


def test_physical_taking_and_resale_do_not_change_legal_evidence(scene):
    db, clock = scene
    register(db, [origin()])
    before = historical_title_evidence(db.load("v"), "origin-bread")
    NPCPropertyService(db, clock).take(
        "v", "basim", "taking", "bakery", "bakery", "bread", 1,
        expected_revision=_rev(db))
    market = NPCMarketService(db, clock)
    market.post("v", "basim", "basim", "bakery", "sale", "bread",
                1, "coin_copper", 2, expected_revision=_rev(db))
    market.buy("v", "nora", "purchase", "sale", 1, 2,
               expected_revision=_rev(db))
    after = historical_title_evidence(db.verify("v"), "origin-bread")
    assert after == before
    assert after["legally_enforceable_owner"] is None


def test_unknown_origin_fails_closed_and_never_creates_state(scene):
    db, clock = scene
    old = db.load("v").to_dict()
    with pytest.raises(ValueError, match="not found"):
        historical_title_evidence(db.load("v"), "fabricated")
    with pytest.raises(ValueError, match="nonempty"):
        historical_title_evidence(db.load("v"), "")
    with pytest.raises(ValueError, match="nonempty"):
        historical_title_evidence(db.load("v"), None)
    assert db.load("v").to_dict() == old


def test_snapshot_replay_evidence_consistent(scene):
    db, clock = scene
    register(db, [origin()])
    expected = historical_title_evidence(db.load("v"), "origin-bread")
    db.snapshot("v")
    assert historical_title_evidence(db.verify("v"), "origin-bread") == expected
    assert historical_title_evidence(db.load("v", use_snapshot=False), "origin-bread") == expected
