"""Independent-from-implementation focused audit probes for J1c2a.

These probes do not imply an external reviewer signed off.
"""
import pytest
from carlos_sim import NPCRegisteredClaimService, NPCPropertyService
from carlos_sim.store import InvalidEvent
from test_rights_04a_j1a import scene, origin, register


def rev(db):
    return db.load("v").revision


def agreement(db, clock, id, seller, account, buyer, qty=1):
    svc = NPCRegisteredClaimService(db, clock)
    svc.offer("v", seller, id, "origin-bread", account, buyer, qty,
              expires_at=100, expected_revision=rev(db))
    return svc.accept("v", buyer, id, expected_revision=rev(db)).state


def test_out_of_lexical_order_multi_hop_claim_not_physical_possession(scene):
    db, clock = scene
    register(db, [origin()])
    original = db.load("v")
    agreement(db, clock, "z-first", "adel", "bakery", "salma")
    agreement(db, clock, "a-second", "salma", "salma", "huda")
    final = agreement(db, clock, "b-third", "huda", "huda", "nora")
    assert final.registered_claim_balances["origin-bread"] == {"bakery": 1, "nora": 1}
    assert final.resources == original.resources
    assert final.property_custody_lots == original.property_custody_lots
    assert final.property_title_origins == original.property_title_origins
    assert db.verify("v").to_dict() == final.to_dict()


def test_invalid_direct_actor_cannot_accept_or_cancel_mismatched_open_offer(scene):
    db, clock = scene
    register(db, [origin()])
    svc = NPCRegisteredClaimService(db, clock)
    svc.offer("v", "adel", "open-o", "origin-bread", "bakery", "salma", 2,
              expires_at=100, expected_revision=rev(db))
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        svc.accept("v", "nora", "open-o", expected_revision=rev(db))
    with pytest.raises(InvalidEvent):
        svc.cancel("v", "basim", "open-o", expected_revision=rev(db))
    assert db.load("v").to_dict() == before


def test_physically_depleted_bakery_can_still_assign_historical_claim(scene):
    db, clock = scene
    register(db, [origin()])
    NPCPropertyService(db, clock).take("v", "basim", "deplete",
        "bakery", "bakery", "bread", 2, expected_revision=rev(db))
    before = db.load("v")
    final = agreement(db, clock, "claim-after-taking", "adel", "bakery", "salma", 1)
    assert final.resources == before.resources
    assert final.registered_claim_balances["origin-bread"] == {"bakery": 1, "salma": 1}
    assert final.property_custody_lots == before.property_custody_lots
    assert db.verify("v").to_dict() == final.to_dict()


def test_same_tick_acceptance_then_second_acceptance_never_spends_reserved_twice(scene):
    db, clock = scene
    register(db, [origin()])
    svc = NPCRegisteredClaimService(db, clock)
    svc.offer("v", "adel", "first", "origin-bread", "bakery", "salma", 1,
              expires_at=100, expected_revision=rev(db))
    svc.offer("v", "adel", "second", "origin-bread", "bakery", "nora", 1,
              expires_at=100, expected_revision=rev(db))
    accepted = svc.accept("v", "nora", "second", expected_revision=rev(db)).state
    assert accepted.registered_claim_balances["origin-bread"] == {"bakery": 1, "nora": 1}
    before = accepted.to_dict()
    with pytest.raises(InvalidEvent):
        svc.offer("v", "adel", "third", "origin-bread", "bakery", "huda", 1,
                  expires_at=100, expected_revision=rev(db))
    assert db.load("v").to_dict() == before
    final = svc.accept("v", "salma", "first", expected_revision=rev(db)).state
    assert final.registered_claim_balances["origin-bread"] == {"nora": 1, "salma": 1}
    assert final.time == 0
    assert db.verify("v").to_dict() == final.to_dict()


def test_same_tick_cancel_then_accept_cannot_resurrect_offer(scene):
    db, clock = scene
    register(db, [origin()])
    svc = NPCRegisteredClaimService(db, clock)
    svc.offer("v", "adel", "offer-to-cancel", "origin-bread", "bakery",
              "salma", 2, expires_at=100, expected_revision=rev(db))
    cancelled = svc.cancel("v", "adel", "offer-to-cancel",
                           expected_revision=rev(db)).state
    before = cancelled.to_dict()
    with pytest.raises(InvalidEvent):
        svc.accept("v", "salma", "offer-to-cancel", expected_revision=rev(db))
    assert db.load("v").to_dict() == before
    svc.offer("v", "adel", "new-after-cancel", "origin-bread", "bakery",
              "nora", 2, expires_at=100, expected_revision=rev(db))
    final = svc.accept("v", "nora", "new-after-cancel", expected_revision=rev(db)).state
    assert final.registered_claim_balances["origin-bread"] == {"nora": 2}
    assert final.registered_claim_offers["offer-to-cancel"]["status"] == "cancelled"
    assert db.verify("v").to_dict() == final.to_dict()
