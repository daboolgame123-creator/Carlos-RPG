"""J1c2a recovery protection probes; internal regression evidence, not P0 sign-off."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine, NPCRegisteredClaimService
from carlos_sim.backup import BackupError, create_backup_bundle, restore_backup_bundle, verify_backup_bundle
from test_property_02h1 import village
from test_rights_04a_j1a import origin, register

CODE_SHA = "318a7388bbee2d621baa0b6cbaff6863d499c207"


def _bundle(tmp_path: Path) -> Path:
    source = tmp_path / "source.sqlite"
    with SQLiteEventStore(source) as store:
        village(store)
        clock = TimeEngine(store)
        clock.open_session("v")
        register(store, [origin()])
        claims = NPCRegisteredClaimService(store, clock)
        claims.offer(
            "v", "adel", "guarded-offer", "origin-bread", "bakery",
            "nora", 1, expires_at=100, expected_revision=store.load("v").revision
        )
        bundle = tmp_path / "bundle"
        create_backup_bundle(store, "v", bundle, code_commit=CODE_SHA)
    return bundle


def test_restore_never_overwrites_existing_save(tmp_path):
    bundle = _bundle(tmp_path)
    target = tmp_path / "existing.sqlite"
    original = b"THIS IS AN EXISTING USER SAVE, NOT A RECOVERY TARGET"
    target.write_bytes(original)
    with pytest.raises(FileExistsError):
        restore_backup_bundle(bundle, target)
    assert target.read_bytes() == original
    assert verify_backup_bundle(bundle)["source_world"] == "v"


def test_restore_never_replaces_existing_symlink(tmp_path):
    bundle = _bundle(tmp_path)
    actual = tmp_path / "untouched.sqlite"
    actual.write_bytes(b"preserve")
    target = tmp_path / "linked.sqlite"
    try:
        target.symlink_to(actual)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable in this environment")
    with pytest.raises(FileExistsError):
        restore_backup_bundle(bundle, target)
    assert target.is_symlink()
    assert actual.read_bytes() == b"preserve"


def test_tampered_manifest_is_rejected_before_output_creation(tmp_path):
    bundle = _bundle(tmp_path)
    manifest_file = bundle / "manifest.json"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    data["worlds"][0]["revision"] += 1
    manifest_file.write_text(json.dumps(data), encoding="utf-8")
    target = tmp_path / "should-not-exist.sqlite"
    with pytest.raises(BackupError):
        restore_backup_bundle(bundle, target)
    assert not target.exists()


def test_concurrent_directory_creator_cannot_be_replaced(tmp_path, monkeypatch):
    """Deterministically interleave a creator after the second absence check."""
    import carlos_sim.backup as backup_module

    source = tmp_path / "source.sqlite"
    destination = tmp_path / "racing-bundle"
    original_check = backup_module._require_new_path
    checks = 0

    def racing_check(path):
        nonlocal checks
        original_check(path)
        if path == destination:
            checks += 1
            if checks == 2:
                destination.mkdir()
                (destination / "another-process.txt").write_text("preserve")

    with SQLiteEventStore(source) as store:
        village(store)
        clock = TimeEngine(store)
        clock.open_session("v")
        register(store, [origin()])
        monkeypatch.setattr(backup_module, "_require_new_path", racing_check)
        with pytest.raises(FileExistsError):
            create_backup_bundle(store, "v", destination, code_commit=CODE_SHA)

    assert (destination / "another-process.txt").read_text() == "preserve"
    assert not (destination / "manifest.json").exists()
    assert not (destination / "world.sqlite").exists()
    assert not list(tmp_path.glob(".carlos-backup-staging-*"))
