"""One-shot offline recovery drill, intentionally outside the pytest test runner.

Runs against a disposable local world in a temporary directory. No user saves.
Successful execution prints evidence; it does NOT grant independent P0 sign-off.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_property_02h1 import village  # noqa: E402
from test_rights_04a_j1a import origin, register  # noqa: E402
from carlos_sim import SQLiteEventStore, TimeEngine, NPCRegisteredClaimService, DomainEvent  # noqa: E402
from carlos_sim.local_institutions import institution_record  # noqa: E402
from carlos_sim.backup import (  # noqa: E402
    BackupError, create_backup_bundle, verify_backup_bundle, restore_backup_bundle,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revision(db: SQLiteEventStore) -> int:
    return db.load("v").revision


def offer(service, db, identifier: str, recipient: str):
    service.offer("v", "adel", identifier, "origin-bread", "bakery",
                  recipient, 1, expires_at=100,
                  expected_revision=revision(db))


def main() -> None:
    commit = os.environ.get("GITHUB_SHA", "")
    if len(commit) != 40 or any(x not in "0123456789abcdef" for x in commit):
        raise RuntimeError("requires exact GITHUB_SHA from GitHub Actions")
    with TemporaryDirectory(prefix="carlos-j1c2a-drill-") as directory:
        root = Path(directory)
        source, restored = root / "source.sqlite", root / "restored.sqlite"
        bundle = root / "backup"
        with SQLiteEventStore(source) as db:
            village(db)
            db.append("v", "founding-institution", revision(db), [DomainEvent(
                "LocalInstitutionRegistered", None, "trusted founding record", 0, {
                    "id": "council-bakery", "site_id": "bakery",
                    "representative_id": "adel", "model": "local_council",
                })], bootstrap=True)
            clock = TimeEngine(db)
            clock.open_session("v")
            register(db, [origin()])
            claims = NPCRegisteredClaimService(db, clock)
            offer(claims, db, "accepted", "salma")
            claims.accept("v", "salma", "accepted", expected_revision=revision(db))
            offer(claims, db, "pending", "nora")
            db.snapshot("v")
            before = db.verify("v").to_dict()
            assert institution_record(db.load("v"), "council-bakery")["can_decide_title"] is False
            assert before["registered_claim_balances"]["origin-bread"] == {"bakery": 1, "salma": 1}
            assert before["registered_claim_offers"]["pending"]["status"] == "open"
            db.db.execute("PRAGMA journal_mode=WAL")
            manifest = create_backup_bundle(db, "v", bundle, code_commit=commit)
            assert verify_backup_bundle(bundle) == manifest
            assert manifest["database_sha256"] == sha256(bundle / "world.sqlite")
            claims.cancel("v", "adel", "pending", expected_revision=revision(db))
            changed = db.verify("v").to_dict()
            assert changed != before
        restored_manifest = restore_backup_bundle(bundle, restored)
        assert manifest == restored_manifest
        with SQLiteEventStore(restored) as db:
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.verify("v").to_dict() == before
            assert institution_record(db.load("v"), "council-bakery")["mandate"] == "existence_record_only"
            assert db.db.execute("SELECT count(*) FROM events WHERE world_id='v'").fetchone()[0] == manifest["worlds"][0]["events"]
            assert db.db.execute("SELECT count(*) FROM snapshots WHERE world_id='v'").fetchone()[0] == manifest["worlds"][0]["snapshots"]
            clock = TimeEngine(db)
            clock.open_session("v")
            NPCRegisteredClaimService(db, clock).accept("v", "nora", "pending", expected_revision=revision(db))
            resumed = db.verify("v")
            assert resumed.registered_claim_balances["origin-bread"] == {"salma": 1, "nora": 1}
            assert resumed.resources == before["resources"]
            assert resumed.property_custody_lots == before["property_custody_lots"]
        with SQLiteEventStore(source) as db:
            assert db.verify("v").to_dict() == changed

        existing = root / "existing.sqlite"
        existing.write_bytes(b"DO NOT OVERWRITE")
        try:
            restore_backup_bundle(bundle, existing)
            raise AssertionError("existing target unexpectedly overwritten")
        except FileExistsError:
            assert existing.read_bytes() == b"DO NOT OVERWRITE"

        corrupt = root / "corrupt"
        corrupt.mkdir()
        (corrupt / "world.sqlite").write_bytes(b"corrupt sqlite")
        (corrupt / "manifest.json").write_bytes((bundle / "manifest.json").read_bytes())
        rejected = root / "rejected.sqlite"
        try:
            restore_backup_bundle(corrupt, rejected)
            raise AssertionError("corruption unexpectedly accepted")
        except BackupError:
            assert not rejected.exists()

        print("J1C2A_DISPOSABLE_RECOVERY_DRILL_SUCCESS")
        print(json.dumps({
            "commit": commit,
            "schema": manifest["schema"], "rules": manifest["rules"],
            "world_id": "v",
            "actors": 7,
            "bundle_sha256": manifest["database_sha256"],
            "bundle_bytes": manifest["database_bytes"],
            "state_sha256": manifest["worlds"][0]["state_sha256"],
            "events": manifest["worlds"][0]["events"],
            "snapshots": manifest["worlds"][0]["snapshots"],
            "restore_integrity": "ok",
            "replay_matches_backup": True,
            "resume_after_restore": True,
            "original_source_untouched_by_restore": True,
            "existing_target_protected": True,
            "corrupted_backup_rejected": True,
            "operational_independent_signoff": False,
        }, sort_keys=True))


if __name__ == "__main__":
    main()
