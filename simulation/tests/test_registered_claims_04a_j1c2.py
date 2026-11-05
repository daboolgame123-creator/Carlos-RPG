"""04-A/J1c2a — two-sided transfer of historical *claims*, NOT legal title."""
import pytest

from carlos_sim import (DomainEvent, NPCRegisteredClaimService,
                        NPCPropertyService, NPCMarketService, SQLiteEventStore,
                        TimeEngine)
from carlos_sim.domain import WorldState
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict
from test_rights_04a_j1a import scene, origin, register
from test_property_02h1 import village


def _rev(db):
    return db.load("v").revision


def _offer(db, clock, *, issuer="adel", ident="o1", source="bakery",
           recipient="salma", amount=1, expires=100):
    return NPCRegisteredClaimService(db, clock).offer(
        "v", issuer, ident, "origin-bread", source, recipient, amount,
        expires_at=expires, expected_revision=_rev(db)).state


def _accept(db, clock, *, recipient="salma", ident="o1"):
    return NPCRegisteredClaimService(db, clock).accept(
        "v", recipient, ident, expected_revision=_rev(db)).state


def _cancel(db, clock, *, issuer="adel", ident="o1"):
    return NPCRegisteredClaimService(db, clock).cancel(
        "v", issuer, ident, expected_revision=_rev(db)).state


def _register(db):
    return register(db, [origin()])


def test_offer_alone_does_not_assign_title_or_move_goods(scene):
    db, clock = scene
    initial = _register(db)
    offered = _offer(db, clock)
    assert offered.registered_claim_balances == {"origin-bread": {"bakery": 2}}
    assert offered.resources == initial.resources
    assert offered.property_custody_lots == initial.property_custody_lots
    assert offered.registered_claim_offers["o1"]["status"] == "open"
    assert offered.registered_claim_transfers == {}
    assert db.verify("v").to_dict() == offered.to_dict()


def test_actual_recipient_accepts_local_bounded_historical_claim(scene):
    db, clock = scene
    initial = _register(db)
    _offer(db, clock)
    result = _accept(db, clock)
    assert result.registered_claim_balances["origin-bread"] == {
        "bakery": 1, "salma": 1
    }
    assert result.registered_claim_offers["o1"]["status"] == "accepted"
    assert result.registered_claim_transfers["o1"]["quantity"] == 1
    assert result.resources == initial.resources
    assert result.property_custody_lots == initial.property_custody_lots
    assert result.property_title_origins == initial.property_title_origins
    assert db.verify("v").to_dict() == result.to_dict()


def test_two_offers_cannot_reserve_more_registered_claim_than_exists(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock, amount=2)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent, match="double-assign"):
        _offer(db, clock, ident="o2", recipient="nora", amount=1)
    assert db.load("v").to_dict() == old


def test_wrong_person_cannot_accept_another_receivers_contract(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        _accept(db, clock, recipient="nora")
    assert db.load("v").to_dict() == old


@pytest.mark.parametrize("issuer,source,recipient,amount,expires", [
    ("nora", "bakery", "salma", 1, 100),
    ("omar", "bakery", "salma", 1, 100),
    ("adel", "basim", "salma", 1, 100),
    ("adel", "bakery", "omar", 1, 100),
    ("adel", "bakery", "salma", 3, 100),
    ("adel", "bakery", "salma", 0, 100),
    ("adel", "bakery", "salma", True, 100),
    ("adel", "bakery", "salma", 1, 0),
    ("adel", "bakery", "salma", 1, 604801),
])
def test_fake_issuer_remote_transfer_invalid_quantities_and_time_fail_closed(
        scene, issuer, source, recipient, amount, expires):
    db, clock = scene
    _register(db)
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        _offer(db, clock, issuer=issuer, source=source,
               recipient=recipient, amount=amount, expires=expires)
    assert db.load("v").to_dict() == before


def test_cancel_open_offer_is_local_and_releases_quantity(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock, amount=2)
    cancelled = _cancel(db, clock)
    assert cancelled.registered_claim_offers["o1"]["status"] == "cancelled"
    assert cancelled.registered_claim_balances["origin-bread"] == {"bakery": 2}
    _offer(db, clock, ident="o2", amount=2, recipient="nora")
    with pytest.raises(InvalidEvent):
        _accept(db, clock, ident="o1")
    assert db.verify("v").to_dict() == db.load("v").to_dict()


def test_expired_open_offer_never_moves_claim_but_releases_reservation(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock, amount=2, expires=5)
    clock.advance("v", seconds=5, command_id="expire", expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        _accept(db, clock)
    valid = _offer(db, clock, ident="o2", amount=2, recipient="nora", expires=50)
    assert valid.registered_claim_balances["origin-bread"] == {"bakery": 2}
    assert valid.registered_claim_offers["o1"]["status"] == "open"


def test_recipient_may_resell_only_its_registered_claim_after_new_consent(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock)
    _accept(db, clock)
    claimed = NPCRegisteredClaimService(db, clock)
    claimed.offer("v", "salma", "o2", "origin-bread", "salma", "huda", 1,
                  expires_at=100, expected_revision=_rev(db))
    accepted = claimed.accept("v", "huda", "o2",
                              expected_revision=_rev(db)).state
    assert accepted.registered_claim_balances["origin-bread"] == {
        "bakery": 1, "huda": 1,
    }
    assert accepted.property_title_origins["origin-bread"]["recorded_beneficiary_id"] == "bakery"
    assert accepted.resources["huda"]["bread"] == 0
    assert db.verify("v").to_dict() == accepted.to_dict()


def test_physically_taking_or_selling_unconnected_bread_never_auto_assigns_claim(scene):
    db, clock = scene
    _register(db)
    prior = db.load("v")
    after_take = NPCPropertyService(db, clock).take(
        "v", "basim", "t1", "bakery", "bakery", "bread", 1,
        expected_revision=_rev(db)).state
    assert after_take.registered_claim_balances == prior.registered_claim_balances
    market = NPCMarketService(db, clock)
    market.post("v", "basim", "basim", "bakery", "offer1", "bread", 1,
                "coin_copper", 2, expected_revision=_rev(db))
    after_sale = market.buy("v", "salma", "trade1", "offer1", 1, 2,
                            expected_revision=_rev(db)).state
    assert after_sale.registered_claim_balances == prior.registered_claim_balances
    assert db.verify("v").to_dict() == after_sale.to_dict()


def test_untrusted_direct_event_cannot_write_registered_claim_offer(scene):
    db, clock = scene
    _register(db)
    e = DomainEvent("RegisteredClaimTransferOffered", "adel", "forgery", 0, {
        "id": "bogus", "origin_id": "origin-bread", "from_account": "bakery",
        "recipient_id": "salma", "quantity": 1, "expires_at": 100
    })
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent, match="independent local capability"):
        db.append("v", "fake-untrusted", _rev(db), [e])
    assert db.load("v").to_dict() == old


def test_detached_snapshot_forged_quantities_and_receipt_are_rejected(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock)
    accepted = _accept(db, clock)
    fake = accepted.to_dict()
    fake["registered_claim_balances"]["origin-bread"]["salma"] = 2
    with pytest.raises(ValueError):
        WorldState.from_dict(fake)
    fake = accepted.to_dict()
    fake["registered_claim_transfers"]["o1"]["quantity"] = 2
    with pytest.raises(ValueError, match="contradicts"):
        WorldState.from_dict(fake)
    fake = accepted.to_dict()
    fake["registered_claim_offers"]["o1"]["status"] = "cancelled"
    with pytest.raises(ValueError):
        WorldState.from_dict(fake)


def test_idempotency_and_stale_revision_do_not_duplicate_transfers(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock)
    _accept(db, clock)
    old = db.load("v").to_dict()
    with pytest.raises(DuplicateCommand):
        _accept(db, clock)
    with pytest.raises(RevisionConflict):
        NPCRegisteredClaimService(db, clock).offer(
            "v", "adel", "o2", "origin-bread", "bakery", "nora", 1,
            expires_at=100, expected_revision=_rev(db)-1)
    assert db.load("v").to_dict() == old


def test_snapshot_reopen_replay_agrees_with_full_event_history(tmp_path):
    with SQLiteEventStore(tmp_path/"claim-contract.sqlite") as db:
        village(db)
        clock = TimeEngine(db); clock.open_session("v")
        _register(db)
        _offer(db, clock)
        _accept(db, clock)
        saved = db.snapshot("v").to_dict()
        assert db.verify("v").to_dict() == saved
    with SQLiteEventStore(tmp_path/"claim-contract.sqlite") as db:
        assert db.verify("v").to_dict() == saved


def test_atomic_invalid_second_event_does_not_leave_unaccepted_offer(scene):
    db, clock = scene
    _register(db)
    before = db.load("v").to_dict()
    events = [
        DomainEvent("RegisteredClaimTransferOffered", "adel", "agreement", 0, {
            "id": "batch-o1", "origin_id": "origin-bread",
            "from_account": "bakery", "recipient_id": "salma",
            "quantity": 1, "expires_at": 100}),
        DomainEvent("RegisteredClaimTransferAccepted", "nora", "forged acceptance", 0, {
            "id": "batch-o1"}),
    ]
    with pytest.raises(InvalidEvent):
        db.append("v", "claim-batch-atomic", _rev(db), events,
                  claim_transfer_authorized=True)
    assert db.load("v").to_dict() == before


def test_receiver_is_traveling_cannot_accept_or_cancel_from_faraway(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock)
    db.append("v", "route-for-claims", _rev(db), [DomainEvent(
        "RouteCreated", None, "physical road", 0, {
            "id": "road-bakery-square", "a": "bakery", "b": "square",
            "seconds": 50})], bootstrap=True)
    from carlos_sim import NPCMovementService
    NPCMovementService(db, clock).start(
        "v", "salma", "road-bakery-square", "leave",
        expected_revision=_rev(db))
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        _accept(db, clock)
    with pytest.raises(InvalidEvent):
        _cancel(db, clock)
    assert db.load("v").to_dict() == old


def test_snapshot_cannot_forge_conserved_balances_or_received_claim_without_receipt(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock)
    original = db.load("v").to_dict()
    forged = db.load("v").to_dict()
    forged["registered_claim_balances"]["origin-bread"] = {
        "bakery": 1, "salma": 1}
    with pytest.raises(ValueError, match="differs"):
        WorldState.from_dict(forged)
    forged = db.load("v").to_dict()
    forged["registered_claim_offers"]["o1"]["status"] = "accepted"
    forged["registered_claim_offers"]["o1"]["resolved_at"] = 0
    with pytest.raises(ValueError):
        WorldState.from_dict(forged)
    assert db.load("v").to_dict() == original
