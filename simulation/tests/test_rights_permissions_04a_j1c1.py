"""J1c1: explicit collection permission is not current judicial/legal title."""
from __future__ import annotations
import pytest

from carlos_sim import (
    DomainEvent, NPCPermissionService, NPCPropertyService, NPCMovementService,
)
from carlos_sim.domain import WorldState
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict
from test_rights_04a_j1a import scene, origin, register


def rev(db):
    return db.load("v").revision


def permit(db, clock, *, actor="adel", who="basim", ident="g1",
           origin_id="origin-bread", quantity=1, expires_at=100):
    return NPCPermissionService(db, clock).grant(
        "v", actor, ident, origin_id, who, quantity,
        expires_at=expires_at, expected_revision=rev(db)).state


def revoke(db, clock, actor="adel", ident="g1"):
    return NPCPermissionService(db, clock).revoke(
        "v", actor, ident, expected_revision=rev(db)).state


def take(db, clock, *, actor="basim", taking_id="t1", quantity=1,
         permission_id="g1"):
    return NPCPropertyService(db, clock).take(
        "v", actor, taking_id, "bakery", "bakery", "bread", quantity,
        permission_id=permission_id, expected_revision=rev(db)).state


def initialized(db):
    register(db, [origin()])


def test_real_local_permission_can_be_redeemed_without_transferring_legal_title(scene):
    db, clock = scene
    initialized(db)
    prior = db.load("v")
    granted = permit(db, clock)
    assert granted.resources == prior.resources
    assert granted.property_permissions["g1"]["remaining"] == 1
    assert granted.property_permissions["g1"]["grantor_id"] == "adel"
    taken = take(db, clock)
    assert taken.resources["basim"]["bread"] == 1
    assert taken.property_takings["t1"]["permission_id"] == "g1"
    assert taken.property_takings["t1"]["permission_basis"] == "recorded_permission"
    assert taken.property_permissions["g1"]["status"] == "exhausted"
    assert taken.property_permissions["g1"]["remaining"] == 0
    assert taken.property_custody_lots["origin-bread"]["known_holders"] == {
        "bakery": 1, "basim": 1
    }
    assert taken.property_title_origins["origin-bread"] == prior.property_title_origins["origin-bread"]
    assert db.verify("v").to_dict() == taken.to_dict()


def test_split_permission_redeemed_only_up_to_original_quantity(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock, quantity=2)
    take(db, clock, taking_id="t1")
    after = take(db, clock, taking_id="t2")
    assert after.property_permissions["g1"]["used"] == 2
    assert after.property_permissions["g1"]["remaining"] == 0
    assert after.property_permissions["g1"]["status"] == "exhausted"
    before = after.to_dict()
    with pytest.raises(InvalidEvent):
        take(db, clock, taking_id="t3")
    assert db.load("v").to_dict() == before


def test_recorded_grant_does_not_make_uncited_physical_taking_judicial_theft(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock)
    state = NPCPropertyService(db, clock).take(
        "v", "basim", "uncited", "bakery", "bakery", "bread", 1,
        expected_revision=rev(db)).state
    assert state.property_takings["uncited"]["permission_basis"] == "no_grant_recorded"
    assert state.property_takings["uncited"]["permission_id"] is None
    assert state.property_permissions["g1"]["remaining"] == 1
    assert state.property_claims == {}
    assert db.verify("v").to_dict() == state.to_dict()


def test_oversubscribed_active_permits_rejected_atomically(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock, quantity=2)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent, match="double-reserve"):
        permit(db, clock, who="nora", ident="g2")
    assert db.load("v").to_dict() == old


def test_partial_unknown_origin_stock_cannot_grant_specific_registered_loaf(scene):
    db, clock = scene
    register(db, [origin(quantity=1)])
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent, match="unambiguous"):
        permit(db, clock)
    assert db.load("v").to_dict() == old


@pytest.mark.parametrize("actor,who,origin_id,quantity,expires_at", [
    ("nora", "basim", "origin-bread", 1, 100),
    ("omar", "basim", "origin-bread", 1, 100),
    ("adel", "omar", "origin-bread", 1, 100),
    ("adel", "basim", "bogus", 1, 100),
    ("adel", "basim", "origin-bread", 3, 100),
    ("adel", "basim", "origin-bread", 0, 100),
    ("adel", "basim", "origin-bread", True, 100),
    ("adel", "basim", "origin-bread", 1, 0),
    ("adel", "basim", "origin-bread", 1, 604801),
])
def test_forged_remote_or_unbounded_grants_rejected(scene, actor, who, origin_id,
                                                    quantity, expires_at):
    db, clock = scene
    initialized(db)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        permit(db, clock, actor=actor, who=who, origin_id=origin_id,
               quantity=quantity, expires_at=expires_at)
    assert db.load("v").to_dict() == old


def test_nora_cannot_redeem_permission_granted_to_basim(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        take(db, clock, actor="nora", taking_id="wrong-recipient")
    assert db.load("v").to_dict() == old


def test_revocation_requires_grantor_and_blocks_future_citation(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        revoke(db, clock, actor="nora")
    assert db.load("v").to_dict() == old
    revoked = revoke(db, clock)
    assert revoked.property_permissions["g1"]["status"] == "revoked"
    assert revoked.property_permissions["g1"]["revoked_at"] == 0
    with pytest.raises(InvalidEvent):
        take(db, clock)
    assert db.load("v").to_dict() == revoked.to_dict()


def test_expired_permission_does_not_move_stock_or_reset_history(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock, expires_at=5)
    clock.advance("v", seconds=5, command_id="to-expiry",
                  expected_revision=rev(db))
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent, match="unexpired"):
        take(db, clock)
    assert db.load("v").to_dict() == old
    assert old["property_permissions"]["g1"]["status"] == "open"


def test_unpermitted_taking_can_exhaust_physical_supply_but_not_invent_grant_stock(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock, who="nora", quantity=2)
    svc = NPCPropertyService(db, clock)
    svc.take("v", "basim", "uncited", "bakery", "bakery", "bread", 2,
             expected_revision=rev(db))
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        take(db, clock, actor="nora", taking_id="no-stock")
    assert db.load("v").to_dict() == old
    assert db.verify("v").to_dict() == old


def test_original_grant_can_be_used_twice_only_if_stock_remains_exclusive(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock, quantity=2)
    take(db, clock, taking_id="first")
    mid = db.load("v")
    assert mid.property_permissions["g1"]["remaining"] == 1
    assert mid.property_custody_lots["origin-bread"]["known_holders"]["bakery"] == 1
    later = take(db, clock, taking_id="second")
    assert later.property_permissions["g1"]["used"] == 2
    assert db.verify("v").to_dict() == later.to_dict()


def test_untrusted_direct_permission_event_is_never_authorized(scene):
    db, clock = scene
    initialized(db)
    e = DomainEvent("PropertyPermissionGranted", "adel", "forged bypass", 0, {
        "id": "fake", "origin_id": "origin-bread",
        "grantee_id": "basim", "quantity": 1, "expires_at": 100
    })
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent, match="trusted"):
        db.append("v", "untrusted-permit", rev(db), [e])
    assert db.load("v").to_dict() == old


def test_snapshot_rejects_wrong_grant_use_and_wrong_cited_taking(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock)
    take(db, clock)
    good = db.load("v")
    forged = good.to_dict()
    forged["property_permissions"]["g1"]["used"] = 0
    with pytest.raises(ValueError, match="inconsistent"):
        WorldState.from_dict(forged)
    forged = good.to_dict()
    forged["property_takings"]["t1"]["actor_id"] = "nora"
    with pytest.raises(ValueError, match="contradicts"):
        WorldState.from_dict(forged)
    assert db.verify("v").to_dict() == good.to_dict()


def test_duplicate_permission_grant_and_stale_revisions_do_not_commit(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock)
    old = db.load("v").to_dict()
    with pytest.raises(DuplicateCommand):
        permit(db, clock)
    with pytest.raises(RevisionConflict):
        NPCPermissionService(db, clock).grant(
            "v", "adel", "new", "origin-bread", "nora", 1,
            expires_at=100, expected_revision=rev(db)-1)
    assert db.load("v").to_dict() == old


def test_held_stock_grant_can_be_revoked_only_with_recipient_local(scene):
    db, clock = scene
    initialized(db)
    permit(db, clock)
    db.append("v", "road", rev(db), [DomainEvent(
        "RouteCreated", None, "test route", 0,
        {"id": "road-bakery-square", "a": "bakery", "b": "square", "seconds": 50}
    )], bootstrap=True)
    NPCMovementService(db, clock).start(
        "v", "basim", "road-bakery-square", "go-away",
        expected_revision=rev(db))
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent, match="meeting"):
        revoke(db, clock)
    assert db.load("v").to_dict() == old
