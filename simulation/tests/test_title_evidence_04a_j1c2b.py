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


def test_origin_packet_separates_holder_from_historical_claimant(scene):
    from carlos_sim.title_evidence import origin_evidence_packet
    db, clock = scene
    register(db, [origin()])
    NPCPropertyService(db, clock).take(
        "v", "basim", "t1", "bakery", "bakery", "bread", 1,
        expected_revision=_rev(db))
    packet = origin_evidence_packet(db.verify("v"), "origin-bread")
    assert packet["historical_claim_evidence"]["current_recorded_claim_balances"] == {"bakery": 2}
    assert packet["physical_custody_evidence"]["known_holders"] == {"bakery": 1, "basim": 1}
    assert packet["physical_custody_evidence"]["unresolved_quantity"] == 0
    assert packet["physical_custody_evidence"]["physical_movements"][0]["event_kind"] == "PropertyTaken"
    assert packet["legally_enforceable_owner"] is None
    assert packet["audience"] == "trusted_internal_audit_only"


def test_origin_packet_marks_mixed_unresolved_goods_without_assigning_title(scene):
    from carlos_sim.title_evidence import origin_evidence_packet
    db, clock = scene
    register(db, [origin(quantity=1)])
    NPCPropertyService(db, clock).take(
        "v", "basim", "t1", "bakery", "bakery", "bread", 1,
        expected_revision=_rev(db))
    packet = origin_evidence_packet(db.verify("v"), "origin-bread")
    physical = packet["physical_custody_evidence"]
    assert physical["known_holders"] == {}
    assert physical["unresolved_quantity"] == 1
    assert physical["provenance_certainty"] == "partial_or_unknown"
    assert physical["physical_movements"][0]["kind"] == "unresolved"
    assert packet["legally_enforceable_owner"] is None


def test_origin_packet_is_read_only_and_replay_equivalent(scene):
    from carlos_sim.title_evidence import origin_evidence_packet
    db, clock = scene
    register(db, [origin()])
    before = db.load("v").to_dict()
    expected = origin_evidence_packet(db.load("v"), "origin-bread")
    db.snapshot("v")
    assert origin_evidence_packet(db.verify("v"), "origin-bread") == expected
    assert db.verify("v").to_dict() == before
    assert origin_evidence_packet(db.load("v", use_snapshot=False), "origin-bread") == expected


def test_expired_historical_offer_is_not_presented_as_active(scene):
    db, clock = scene
    register(db, [origin()])
    service = NPCRegisteredClaimService(db, clock)
    service.offer("v", "adel", "short", "origin-bread", "bakery",
                  "salma", 1, expires_at=5, expected_revision=_rev(db))
    assert len(historical_title_evidence(db.load("v"), "origin-bread")[
        "open_historical_assignment_offers"]) == 1
    clock.advance("v", seconds=5, command_id="expire-evidence",
                  expected_revision=_rev(db))
    evidence = historical_title_evidence(db.verify("v"), "origin-bread")
    assert evidence["open_historical_assignment_offers"] == []
    assert evidence["current_recorded_claim_balances"] == {"bakery": 2}
    assert evidence["legal_title_status"] == "undetermined"


def test_evidence_results_are_detached_from_world_state(scene):
    db, clock = scene
    register(db, [origin()])
    service = NPCRegisteredClaimService(db, clock)
    service.offer("v", "adel", "offer-1", "origin-bread", "bakery",
                  "salma", 1, expires_at=100, expected_revision=_rev(db))
    before = db.verify("v").to_dict()
    evidence = historical_title_evidence(db.load("v"), "origin-bread")
    evidence["current_recorded_claim_balances"]["bakery"] = 999
    evidence["open_historical_assignment_offers"][0]["quantity"] = 999
    assert db.verify("v").to_dict() == before
    fresh = historical_title_evidence(db.load("v"), "origin-bread")
    assert fresh["current_recorded_claim_balances"]["bakery"] == 2
    assert fresh["open_historical_assignment_offers"][0]["quantity"] == 1


def test_two_separate_origins_do_not_mix_evidence(scene):
    db, clock = scene
    register(db, [origin("origin-bread-a", quantity=1),
                  origin("origin-bread-b", quantity=1)])
    first = historical_title_evidence(db.verify("v"), "origin-bread-a")
    second = historical_title_evidence(db.verify("v"), "origin-bread-b")
    assert first["registered_quantity"] == second["registered_quantity"] == 1
    assert first["origin_id"] != second["origin_id"]
    assert first["accepted_historical_assignments"] == []
    assert second["accepted_historical_assignments"] == []
    assert first["legally_enforceable_owner"] is None
    assert second["legally_enforceable_owner"] is None


def test_expired_offer_still_visible_in_historical_audit(scene):
    db, clock = scene
    register(db, [origin()])
    service = NPCRegisteredClaimService(db, clock)
    service.offer("v", "adel", "expiring", "origin-bread", "bakery",
                  "salma", 1, expires_at=5, expected_revision=_rev(db))
    clock.advance("v", seconds=5, command_id="advance-expiring",
                  expected_revision=_rev(db))
    evidence = historical_title_evidence(db.verify("v"), "origin-bread")
    assert evidence["open_historical_assignment_offers"] == []
    history = evidence["historical_assignment_offer_history"]
    assert len(history) == 1
    assert history[0]["recorded_status"] == "open"
    assert history[0]["effective_status"] == "expired"
    assert history[0]["resolved_at"] is None
    assert evidence["legally_enforceable_owner"] is None


def test_cancelled_offer_retains_reasonably_precise_history(scene):
    db, clock = scene
    register(db, [origin()])
    service = NPCRegisteredClaimService(db, clock)
    service.offer("v", "adel", "withdrawn", "origin-bread", "bakery",
                  "salma", 1, expires_at=100, expected_revision=_rev(db))
    service.cancel("v", "adel", "withdrawn", expected_revision=_rev(db))
    evidence = historical_title_evidence(db.verify("v"), "origin-bread")
    assert evidence["open_historical_assignment_offers"] == []
    assert evidence["accepted_historical_assignments"] == []
    assert evidence["historical_assignment_offer_history"][0]["recorded_status"] == "cancelled"
    assert evidence["historical_assignment_offer_history"][0]["effective_status"] == "cancelled"
    assert evidence["historical_assignment_offer_history"][0]["resolved_at"] == 0
    assert evidence["current_recorded_claim_balances"] == {"bakery": 2}


def test_accepted_offer_history_is_not_lost_or_reclassified_as_expired(scene):
    db, clock = scene
    register(db, [origin()])
    service = NPCRegisteredClaimService(db, clock)
    service.offer("v", "adel", "accepted-1", "origin-bread", "bakery",
                  "salma", 1, expires_at=5, expected_revision=_rev(db))
    service.accept("v", "salma", "accepted-1", expected_revision=_rev(db))
    clock.advance("v", seconds=5, command_id="advance-after-accept",
                  expected_revision=_rev(db))
    evidence = historical_title_evidence(db.verify("v"), "origin-bread")
    assert evidence["historical_assignment_offer_history"][0]["effective_status"] == "accepted"
    assert evidence["accepted_historical_assignments"][0]["offer_id"] == "accepted-1"
    assert evidence["legally_enforceable_owner"] is None


def test_offer_history_is_detached_and_matches_full_replay(scene):
    db, clock = scene
    register(db, [origin()])
    NPCRegisteredClaimService(db, clock).offer(
        "v", "adel", "pending", "origin-bread", "bakery",
        "salma", 1, expires_at=100, expected_revision=_rev(db))
    db.snapshot("v")
    expected = historical_title_evidence(db.verify("v"), "origin-bread")
    assert historical_title_evidence(db.load("v", use_snapshot=False), "origin-bread") == expected
    expected["historical_assignment_offer_history"][0]["quantity"] = 99
    assert historical_title_evidence(db.load("v"), "origin-bread")[
        "historical_assignment_offer_history"][0]["quantity"] == 1


def test_claim_packet_does_not_turn_false_accusation_into_legal_truth(scene):
    from carlos_sim.title_evidence import property_claim_audit_packet
    db, clock = scene
    register(db, [origin()])
    service = NPCPropertyService(db, clock)
    service.take("v", "basim", "taken", "bakery", "bakery", "bread", 1,
                 witnessed_by=("salma",), expected_revision=_rev(db))
    service.claim("v", "nora", "false", "accusation", "bakery",
                  "bread", 1, subject_id="adel", taking_id=None,
                  expected_revision=_rev(db))
    packet = property_claim_audit_packet(db.verify("v"), "false")
    assert packet["basis"] == "unverified_statement"
    assert packet["alleged_subject_id"] == "adel"
    assert packet["cited_physical_taking"] is None
    assert packet["registered_origin_id"] is None
    assert packet["origin_linkage"] == "not_established"
    assert packet["legally_enforceable_owner"] is None
    assert not packet["guilt_determined"]


def test_firsthand_sighting_corroborates_action_only_not_title(scene):
    from carlos_sim.title_evidence import property_claim_audit_packet
    db, clock = scene
    register(db, [origin()])
    service = NPCPropertyService(db, clock)
    service.take("v", "basim", "observed", "bakery", "bakery", "bread", 1,
                 witnessed_by=("salma",), expected_revision=_rev(db))
    service.claim("v", "salma", "eyewitness", "accusation", "bakery",
                  "bread", 1, subject_id="basim", taking_id="observed",
                  expected_revision=_rev(db))
    packet = property_claim_audit_packet(db.verify("v"), "eyewitness")
    assert packet["basis"] == "direct_sighting"
    assert packet["cited_physical_taking"]["actor_id"] == "basim"
    assert packet["cited_physical_taking"]["evidence_scope"] == "recorded_physical_action_only"
    assert packet["origin_linkage"] == "not_established"
    assert packet["legal_title_status"] == "undetermined"
    assert packet["legally_enforceable_owner"] is None


def test_claim_audit_rejects_unknown_id_without_state_change(scene):
    from carlos_sim.title_evidence import property_claim_audit_packet
    db, clock = scene
    old = db.load("v").to_dict()
    for invalid in ("", None, 12):
        with pytest.raises(ValueError, match="nonempty"):
            property_claim_audit_packet(db.load("v"), invalid)
    with pytest.raises(ValueError, match="not found"):
        property_claim_audit_packet(db.load("v"), "fabricated")
    assert db.verify("v").to_dict() == old


def test_claim_audit_read_only_snapshot_and_full_replay(scene):
    from carlos_sim.title_evidence import property_claim_audit_packet
    db, clock = scene
    register(db, [origin()])
    NPCPropertyService(db, clock).claim(
        "v", "nora", "statement", "ownership", "bakery", "bread", 1,
        subject_id=None, taking_id=None, expected_revision=_rev(db))
    packet = property_claim_audit_packet(db.load("v"), "statement")
    db.snapshot("v")
    assert property_claim_audit_packet(db.verify("v"), "statement") == packet
    assert property_claim_audit_packet(db.load("v", use_snapshot=False), "statement") == packet
    packet["claimant_id"] = "fraud"
    assert property_claim_audit_packet(db.verify("v"), "statement")["claimant_id"] == "nora"
