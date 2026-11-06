"""J1c2a-specific backup/restore regression evidence (not external P0 signoff)."""
from __future__ import annotations

import pytest
from carlos_sim import SQLiteEventStore, TimeEngine, NPCRegisteredClaimService
from carlos_sim.backup import create_backup_bundle, verify_backup_bundle, restore_backup_bundle, BackupError
from carlos_sim.store import InvalidEvent
from test_property_02h1 import village
from test_rights_04a_j1a import origin, register

# Real immutable commit that introduced the 04-A/J1c2a reviewed CI.
CODE_SHA = "be66bb0d4a5ad04d2badbe6eefce26ce630e0b91"


def _revision(store):
    return store.load("v").revision


def _offer(service, store, ident, recipient, qty):
    service.offer("v", "adel", ident, "origin-bread", "bakery",
                  recipient, qty, expires_at=100,
                  expected_revision=_revision(store))


def test_backup_restores_open_and_accepted_registered_claims_without_teleporting_goods(tmp_path):
    source = tmp_path / "live.sqlite"
    with SQLiteEventStore(source) as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        register(db, [origin()])
        svc = NPCRegisteredClaimService(db, clock)
        _offer(svc, db, "closed-offer", "salma", 1)
        svc.accept("v", "salma", "closed-offer", expected_revision=_revision(db))
        _offer(svc, db, "pending-offer", "nora", 1)
        db.snapshot("v")
        before = db.verify("v").to_dict()
        assert before["registered_claim_balances"]["origin-bread"] == {
            "bakery": 1, "salma": 1
        }
        assert before["registered_claim_offers"]["pending-offer"]["status"] == "open"
        assert before["registered_claim_transfers"]["closed-offer"]["recipient_id"] == "salma"
        db.db.execute("PRAGMA journal_mode=WAL")
        bundle = tmp_path / "known-good"
        manifest = create_backup_bundle(db, "v", bundle, code_commit=CODE_SHA)
        assert verify_backup_bundle(bundle) == manifest
        assert manifest["schema"] == 28 and manifest["rules"] == 36
        assert manifest["worlds"][0]["state_sha256"]
        # Source changes *after* backup; the frozen bundle must not change.
        svc.cancel("v", "adel", "pending-offer", expected_revision=_revision(db))
        later = db.verify("v").to_dict()
        assert later != before

    restored_path = tmp_path / "recovered.sqlite"
    assert restore_backup_bundle(bundle, restored_path) == manifest
    with SQLiteEventStore(restored_path) as recovered:
        restored = recovered.verify("v")
        assert restored.to_dict() == before
        assert restored.registered_claim_offers["pending-offer"]["status"] == "open"
        assert restored.registered_claim_balances["origin-bread"] == {
            "bakery": 1, "salma": 1
        }
        c = TimeEngine(recovered)
        c.open_session("v")
        NPCRegisteredClaimService(recovered, c).accept(
            "v", "nora", "pending-offer",
            expected_revision=_revision(recovered))
        final = recovered.verify("v")
        assert final.registered_claim_balances["origin-bread"] == {
            "salma": 1, "nora": 1
        }
        assert final.resources == restored.resources
        assert final.property_custody_lots == restored.property_custody_lots
    with SQLiteEventStore(source) as db:
        assert db.verify("v").to_dict() == later


def test_corrupt_claim_backup_refuses_restore_without_creating_target(tmp_path):
    source = tmp_path / "source.sqlite"
    with SQLiteEventStore(source) as db:
        village(db)
        clock = TimeEngine(db)
        clock.open_session("v")
        register(db, [origin()])
        svc = NPCRegisteredClaimService(db, clock)
        _offer(svc, db, "pending", "nora", 1)
        bundle = tmp_path / "bundle"
        create_backup_bundle(db, "v", bundle, code_commit=CODE_SHA)
    (bundle / "world.sqlite").write_bytes(b"corrupted test backup")
    output = tmp_path / "must-not-exist.sqlite"
    with pytest.raises(BackupError):
        restore_backup_bundle(bundle, output)
    assert not output.exists()
    with SQLiteEventStore(source) as db:
        assert db.verify("v").registered_claim_offers["pending"]["status"] == "open"
