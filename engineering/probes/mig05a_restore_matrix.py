"""MIG-05a: bounded 41/56 -> 42/57 acceptance/rejection/restore matrix.

Research-only, authentic two-world predecessor SQLite fixture, NEVER a production
migration tool. The pinned GitHub Actions workflow creates this fixture afresh.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.backup import (
    BackupError, create_backup_bundle, restore_backup_bundle, verify_backup_bundle,
)
from carlos_sim.domain import canonical_hash, SCHEMA_VERSION, RULES_VERSION
from carlos_sim.store import DuplicateCommand, IntegrityError, InvalidEvent, UnsupportedVersion
import mig04_adversarial_probe as migration

SOURCE = Path("fixture-old-41-56.sqlite").resolve()
TARGET_SHA = "38ef0049478e4d62fd465dadc7c1eaf406b9b4d2"
WORLD_ID = "secondary-41-56"
assert (SCHEMA_VERSION, RULES_VERSION) == (42, 57)


def reject(exc, op, name: str) -> None:
    try:
        op()
    except exc:
        print("MIG05A_REJECTED " + name, flush=True)
    else:
        raise AssertionError("fail-closed rejection missing: " + name)


def expected_target(state: dict) -> dict:
    copied = dict(state)
    copied.update(schema_version=42, rules_version=57)
    return copied


def check_restored_state(path: Path, expected: dict) -> None:
    with SQLiteEventStore(path) as store:
        assert store.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert store.db.execute("PRAGMA foreign_key_check").fetchall() == []
        for world_id, legacy_state in expected.items():
            desired = expected_target(legacy_state)
            assert store.verify(world_id).to_dict() == desired
            assert store.load(world_id).to_dict() == desired


def check_old_refusal(source: Path, root: Path) -> None:
    copy = root / "old-version-refusal.sqlite"
    shutil.copy2(source, copy)
    source_before = migration.fingerprint(source)
    copied_before = migration.fingerprint(copy)
    with SQLiteEventStore(copy) as store:
        reject(UnsupportedVersion, lambda: store.load(WORLD_ID), "old_schema_rules_load")
    assert migration.fingerprint(copy) == copied_before
    assert migration.fingerprint(source) == source_before


def check_unknown_semantic_event(source: Path, expected: dict, root: Path) -> None:
    """Build a hash-consistent forged event and command; reject by reducer semantics."""
    forged = root / "unknown-event-source.sqlite"
    shutil.copy2(source, forged)
    valid_plan = migration.preflight(forged)
    groups = valid_plan[WORLD_ID]["groups"]
    assert len(groups) == 1
    command_id, revision, events, flags, _, receipts = groups[0]
    assert revision == 0 and len(events) == 2
    changed = [event.to_dict() for event in events]
    changed[0]["event_type"] = "MIG05A_UnknownEventMustBeRejected"
    request = {"events": changed, "expected_revision": revision}
    request.update(flags)
    event_hash = canonical_hash(changed[0])
    command_hash = canonical_hash(request)
    with closing(sqlite3.connect(forged)) as conn:
        with conn:
            conn.execute(
                "UPDATE events SET payload=?,hash=? WHERE world_id=? AND command_id=? AND seq=?",
                (json.dumps(changed[0], ensure_ascii=False, sort_keys=True),
                 event_hash, WORLD_ID, command_id, receipts[0][0]),
            )
            conn.execute(
                "UPDATE commands SET request_hash=? WHERE world_id=? AND command_id=?",
                (command_hash, WORLD_ID, command_id),
            )
    assert len(migration.preflight(forged)[WORLD_ID]["groups"]) == 1, (
        "forged receipts must pass basic digest preflight, then fail semantic replay"
    )
    dest = root / "unknown-event-must-not-publish.sqlite"
    reject((ValueError, InvalidEvent, IntegrityError),
           lambda: migration.create_destination(forged, dest, expected),
           "hash_consistent_unsupported_event")
    assert not dest.exists(), "invalid semantic history published"


def check_version_and_target_protection(source: Path, expected: dict, root: Path) -> None:
    wrong = root / "wrong-source-version.sqlite"
    shutil.copy2(source, wrong)
    with closing(sqlite3.connect(wrong)) as conn:
        with conn:
            conn.execute("UPDATE worlds SET rules_version=58 WHERE id=?", (WORLD_ID,))
    reject(ValueError, lambda: migration.preflight(wrong), "wrong_source_rules")
    refuse = root / "wrong-version-target.sqlite"
    reject(ValueError, lambda: migration.create_destination(wrong, refuse, expected),
           "wrong_version_publish")
    assert not refuse.exists()


def check_bundle_recovery(target: Path, expected: dict, root: Path) -> dict:
    bundle = root / "test-only-target-bundle"
    restored = root / "restored42-57.sqlite"
    with SQLiteEventStore(target) as store:
        before = {key: store.verify(key).to_dict() for key in expected}
        manifest = create_backup_bundle(store, WORLD_ID, bundle, code_commit=TARGET_SHA)
        assert {row["world_id"] for row in manifest["worlds"]} == set(expected)
        assert manifest["schema"] == 42 and manifest["rules"] == 57
    checked = verify_backup_bundle(bundle)
    assert checked == manifest
    restored_manifest = restore_backup_bundle(bundle, restored)
    assert restored_manifest == manifest
    check_restored_state(restored, expected)
    before_digest = migration.fingerprint(restored)
    reject(FileExistsError, lambda: restore_backup_bundle(bundle, restored),
           "existing_restore_target")
    assert migration.fingerprint(restored) == before_digest, "restore clobbered target"
    damaged = root / "tampered-manifest"
    shutil.copytree(bundle, damaged)
    manifest_file = damaged / "manifest.json"
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    payload["database_sha256"] = "0" * 64
    manifest_file.write_text(json.dumps(payload), encoding="utf-8")
    invalid_target = root / "tampered-restore.sqlite"
    reject(BackupError, lambda: restore_backup_bundle(damaged, invalid_target),
           "tampered_backup_manifest")
    assert not invalid_target.exists(), "bad manifest got published"

    with SQLiteEventStore(restored) as recovered:
        secondary_before = recovered.verify(WORLD_ID)
        clock = TimeEngine(recovered)
        clock.open_session(WORLD_ID)
        try:
            committed = clock.advance(
                WORLD_ID, seconds=1, command_id="mig05a:continuation",
                expected_revision=secondary_before.revision,
            ).state
            assert committed.time == secondary_before.time + 1
            assert committed.revision == secondary_before.revision + 1
            assert committed.resources == secondary_before.resources, "copper minted"
            assert committed.entities == secondary_before.entities
            assert committed.locations == secondary_before.locations
            reject(DuplicateCommand, lambda: clock.advance(
                WORLD_ID, seconds=1, command_id="mig05a:continuation",
                expected_revision=committed.revision,
            ), "duplicate_continuation")
            assert recovered.verify(WORLD_ID).to_dict() == committed.to_dict()
            assert recovered.verify("village").to_dict() == before["village"]
        finally:
            clock.close_session(WORLD_ID)
    with SQLiteEventStore(restored) as reopened:
        assert reopened.verify(WORLD_ID).to_dict() == committed.to_dict()
        assert reopened.verify("village").to_dict() == before["village"]
    # The target (pre-restore) is left untouched by playing on the restored copy.
    check_restored_state(target, expected)
    return {"bundle_world_count": len(checked["worlds"]), "restore_world_count": 2,
            "continuation_events": 1, "manifest_tamper_rejected": True,
            "duplicate_command_rejected": True, "no_resource_mint": True}


def main() -> None:
    source_sha = migration.fingerprint(SOURCE)
    expected = json.loads(Path("fixture-expected.json").read_text(encoding="utf-8"))
    assert set(expected) == set(migration.WORLD_IDS)
    pre = migration.preflight(SOURCE)
    assert len(pre) == 2
    assert sum(x["event_count"] for x in pre.values()) == 53
    assert sum(len(x["groups"]) for x in pre.values()) == 7
    with tempfile.TemporaryDirectory(prefix="mig05a-restore-matrix-") as root_name:
        root = Path(root_name)
        check_old_refusal(SOURCE, root)
        check_unknown_semantic_event(SOURCE, expected, root)
        check_version_and_target_protection(SOURCE, expected, root)
        target = root / "isolated-migrated42-57.sqlite"
        migration.create_destination(SOURCE, target, expected)
        check_restored_state(target, expected)
        recovery = check_bundle_recovery(target, expected, root)
    assert migration.fingerprint(SOURCE) == source_sha, "source bytes changed"
    result = {
        "disposable_only": True, "source_version": [41, 56],
        "target_version": [42, 57], "world_count": 2,
        "authentic_events": 53, "authentic_commands": 7,
        "old_version_rejected": True, "unsupported_event_rejected": True,
        "wrong_source_version_rejected": True, "source_unchanged": True,
        "full_replay_and_restore_verified": True,
        "production_migration_approved": False, **recovery,
    }
    print("MIG05A_ACCEPTANCE_MATRIX " + json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
