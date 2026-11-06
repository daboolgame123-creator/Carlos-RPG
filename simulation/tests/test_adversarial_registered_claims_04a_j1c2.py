"""Additional adversarial regression probes for J1c2a.

Self-authored probes; not an independent external review signoff.
"""
import json
import pytest

from carlos_sim import NPCRegisteredClaimService
from carlos_sim.domain import WorldState, canonical, canonical_hash
from carlos_sim.store import InvalidEvent, IntegrityError
from test_rights_04a_j1a import scene
from test_registered_claims_04a_j1c2 import _register, _offer, _accept, _rev


def test_two_parallel_valid_offers_accepted_in_reverse_identifier_order(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock, ident="z-first", recipient="salma", amount=1)
    _offer(db, clock, ident="a-second", recipient="nora", amount=1)
    before = db.load("v")
    assert before.registered_claim_balances["origin-bread"] == {"bakery": 2}
    _accept(db, clock, recipient="nora", ident="a-second")
    final = _accept(db, clock, recipient="salma", ident="z-first")
    assert final.registered_claim_balances["origin-bread"] == {
        "nora": 1, "salma": 1
    }
    assert db.verify("v").to_dict() == final.to_dict()


def test_unaccepted_recipient_cannot_offer_reserved_rights_as_its_own(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock, ident="first", recipient="salma", amount=1)
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        NPCRegisteredClaimService(db, clock).offer(
            "v", "salma", "second", "origin-bread", "salma",
            "huda", 1, expires_at=100, expected_revision=_rev(db)
        )
    assert db.load("v").to_dict() == old


def test_exact_expiration_second_rejects_acceptance_but_frees_reservation(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock, ident="old", amount=2, expires=5)
    clock.advance("v", seconds=5, command_id="to-expiry", expected_revision=_rev(db))
    old = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        _accept(db, clock, ident="old")
    assert db.load("v").to_dict() == old
    fresh = _offer(db, clock, ident="fresh", recipient="nora", amount=2, expires=10)
    assert fresh.registered_claim_balances["origin-bread"] == {"bakery": 2}
    assert db.verify("v").to_dict() == fresh.to_dict()


def test_rehashed_snapshot_with_fake_claim_balance_cannot_be_loaded(scene):
    db, clock = scene
    _register(db)
    _offer(db, clock)
    _accept(db, clock)
    saved = db.snapshot("v")
    forged = saved.to_dict()
    forged["registered_claim_balances"]["origin-bread"] = {"salma": 2}
    # Simulate an attacker able to recompute a plain snapshot hash. Domain
    # invariants must still fail, independently of checksum validation.
    db.db.execute(
        "UPDATE snapshots SET state=?, hash=? WHERE world_id=? AND revision=?",
        (canonical(forged), canonical_hash(forged), "v", saved.revision)
    )
    with pytest.raises(ValueError):
        WorldState.from_dict(json.loads(canonical(forged)))
    with pytest.raises(IntegrityError):
        db.load("v")
    # Genesis replay remains independent of snapshots.
    assert db.load("v", use_snapshot=False).to_dict() == saved.to_dict()
