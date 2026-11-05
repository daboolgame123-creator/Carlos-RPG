"""Phase 01-Z: P0 candidate backup/restore and resumable disposable play.

A green suite is technical evidence, never independent approval of P0.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.backup import (
    BackupError, create_backup_bundle, verify_backup_bundle,
    restore_backup_bundle,
)
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, RevisionConflict
from carlos_sim.time_engine import SessionClosed
from test_player_gateway import setup_player_demo_world


COMMIT = 'a7e0e8e4d1671bc16f5a3c4f9bbd4ee3bb8c4210'


def _new(tmp_path):
    filename = tmp_path / 'test-world.sqlite'
    session = ResumableTestSession.create(
        filename, 'world', 'carlos', setup_player_demo_world,
        disposable_test=True)
    return filename, session


def _rows(store, world_id='world'):
    return {
        table: store.db.execute(
            'SELECT * FROM ' + table + ' WHERE ' +
            ('id=?' if table == 'worlds' else 'world_id=?'),
            (world_id,)).fetchall()
        for table in ('worlds', 'commands', 'events', 'snapshots')
    }


def test_disabled_without_explicit_disposable_opt_in(tmp_path):
    filename = tmp_path / 'save.sqlite'
    with pytest.raises(PermissionError):
        ResumableTestSession.create(
            filename, 'world', 'carlos', setup_player_demo_world)
    assert not filename.exists()
    with pytest.raises(PermissionError):
        ResumableTestSession.resume(filename, 'world', 'carlos')
    assert not filename.exists()


def test_reopen_mid_travel_freezes_logical_time_and_preserves_request_ids(tmp_path):
    path, session = _new(tmp_path)
    initial = session.gateway.inspect()
    assert initial.details['location_id'] == 'market'
    journey = session.gateway.move(
        'road', command_id='durable-travel',
        expected_revision=session.store.load('world').revision)
    at_departure = session.store.load('world')
    assert journey.status == 'traveling'
    assert at_departure.time == 0
    revision = at_departure.revision
    session.close()

    with ResumableTestSession.resume(
        path, 'world', 'carlos', disposable_test=True) as resumed:
        state = resumed.store.load('world')
        assert state.time == 0 and state.revision == revision
        assert resumed.gateway.inspect().status == 'traveling'
        assert resumed.gateway.inspect().details['remaining_seconds'] == 90
        with pytest.raises(ValueError):
            resumed.gateway.observe(
                command_id='look-in-transit', expected_revision=revision)
        advanced = resumed.gateway.wait(
            90, command_id='resume-wait', expected_revision=revision)
        assert advanced.status == 'ready'
        assert resumed.gateway.inspect().details['location_id'] == 'forest'
        final = resumed.store.load('world')
        assert final.time == 90
        with pytest.raises(DuplicateCommand):
            resumed.gateway.wait(
                90, command_id='resume-wait',
                expected_revision=final.revision)
        with pytest.raises(DuplicateCommand):
            resumed.gateway.move(
                'road', command_id='durable-travel',
                expected_revision=final.revision)
        assert resumed.store.load('world').to_dict() == final.to_dict()
        assert resumed.store.verify('world').to_dict() == final.to_dict()


def test_safe_view_after_restart_is_player_only(tmp_path):
    path, session = _new(tmp_path)
    session.gateway.observe(
        command_id='first-look', expected_revision=session.store.load('world').revision)
    remembered = session.gateway.recall().details
    status = session.gateway.status().details
    session.close()
    with ResumableTestSession.resume(
        path, 'world', 'carlos', disposable_test=True) as resumed:
        data = resumed.view()
        assert data['scene'].details['location_id'] == 'market'
        assert data['memory'].details == remembered
        assert data['status'].details == status
        assert 'npcs' not in repr(data)
        assert 'resources' not in repr(data)
        assert resumed.store.verify('world').to_dict() == resumed.store.load('world').to_dict()


def test_backup_live_wal_restore_frozen_state_and_resume(tmp_path):
    path, session = _new(tmp_path)
    session.store.db.execute('PRAGMA journal_mode=WAL')
    session.gateway.move(
        'road', command_id='travel',
        expected_revision=session.store.load('world').revision)
    captured = session.store.verify('world').to_dict()
    bundle = tmp_path / 'checkpoint-1'
    manifest = session.checkpoint(bundle, code_commit=COMMIT)
    assert manifest['code_commit'] == COMMIT
    assert manifest['source_world'] == 'world'
    assert manifest["schema"] == 27 and manifest["rules"] == 35
    assert manifest['worlds'][0]['revision'] == captured['revision']
    assert verify_backup_bundle(bundle) == manifest
    # The live source keeps evolving independently of this frozen checkpoint.
    session.gateway.wait(
        90, command_id='after-backup',
        expected_revision=session.store.load('world').revision)
    assert session.store.load('world').time == 90
    original = session.store.load('world').to_dict()
    session.close()

    recovered = tmp_path / 'restored.sqlite'
    assert restore_backup_bundle(bundle, recovered) == manifest
    assert recovered.exists()
    with ResumableTestSession.resume(
        recovered, 'world', 'carlos', disposable_test=True) as restored:
        assert restored.store.load('world').to_dict() == captured
        assert restored.gateway.inspect().status == 'traveling'
        assert restored.gateway.inspect().details['remaining_seconds'] == 90
        restored.gateway.wait(
            90, command_id='after-restoring',
            expected_revision=restored.store.load('world').revision)
        assert restored.gateway.inspect().details['location_id'] == 'forest'
        assert restored.store.verify('world').time == 90
    with ResumableTestSession.resume(
        path, 'world', 'carlos', disposable_test=True) as original_session:
        assert original_session.store.load('world').to_dict() == original


def test_backup_records_and_verifies_every_world(tmp_path):
    path, session = _new(tmp_path)
    session.store.create_world('second')
    bundle = tmp_path / 'two-worlds'
    manifest = session.checkpoint(bundle, code_commit=COMMIT)
    assert [x['world_id'] for x in manifest['worlds']] == ['second', 'world']
    assert verify_backup_bundle(bundle) == manifest
    restored = tmp_path / 'restore-multiple.sqlite'
    restore_backup_bundle(bundle, restored)
    with SQLiteEventStore(restored) as db:
        for ident in ('world', 'second'):
            assert db.load(ident).to_dict() == session.store.load(ident).to_dict()
            assert db.verify(ident).to_dict() == session.store.verify(ident).to_dict()
    session.close()


def test_failed_invalid_provenance_cannot_publish_bundle(tmp_path):
    path, session = _new(tmp_path)
    for invalid in ('', 'some-branch', '1' * 39, 'Z' * 40):
        bundle = tmp_path / ('refuse-' + str(len(invalid)))
        with pytest.raises(BackupError):
            session.checkpoint(bundle, code_commit=invalid)
        assert not bundle.exists()
    session.close()


def test_backup_or_restore_never_overwrites_existing_targets(tmp_path):
    path, session = _new(tmp_path)
    folder = tmp_path / 'existing'
    folder.mkdir()
    untouched = folder / 'keep'
    untouched.write_text('keep', encoding='utf-8')
    with pytest.raises(FileExistsError):
        session.checkpoint(folder, code_commit=COMMIT)
    assert untouched.read_text(encoding='utf-8') == 'keep'
    bundle = tmp_path / 'backup'
    session.checkpoint(bundle, code_commit=COMMIT)
    target = tmp_path / 'existing.sqlite'
    target.write_bytes(b'ORIGINAL SAVE')
    with pytest.raises(FileExistsError):
        restore_backup_bundle(bundle, target)
    assert target.read_bytes() == b'ORIGINAL SAVE'
    session.close()


def test_corrupt_db_bundle_fails_before_restore_and_preserves_source(tmp_path):
    path, session = _new(tmp_path)
    before = _rows(session.store)
    bundle = tmp_path / 'archive'
    session.checkpoint(bundle, code_commit=COMMIT)
    database = bundle / 'world.sqlite'
    with database.open('r+b') as f:
        f.seek(20)
        f.write(b'BAD!')
    with pytest.raises(BackupError):
        verify_backup_bundle(bundle)
    recovered = tmp_path / 'should-not-exist.sqlite'
    with pytest.raises(BackupError):
        restore_backup_bundle(bundle, recovered)
    assert not recovered.exists()
    assert _rows(session.store) == before
    session.close()


def test_tampered_manifest_wrong_version_or_missing_manifest_fails(tmp_path):
    path, session = _new(tmp_path)
    bundle = tmp_path / 'archive'
    session.checkpoint(bundle, code_commit=COMMIT)
    manifest_file = bundle / 'manifest.json'
    original = json.loads(manifest_file.read_text(encoding='utf-8'))
    for item in ('schema', 'rules', 'database_sha256', 'worlds'):
        changed = dict(original)
        changed[item] = (999 if item in ('schema', 'rules') else
                         ('0' * 64 if item == 'database_sha256' else []))
        manifest_file.write_text(json.dumps(changed), encoding='utf-8')
        with pytest.raises(BackupError):
            verify_backup_bundle(bundle)
    manifest_file.write_text('not-json', encoding='utf-8')
    with pytest.raises(BackupError):
        restore_backup_bundle(bundle, tmp_path / 'missing-target.sqlite')
    assert not (tmp_path / 'missing-target.sqlite').exists()
    assert session.store.verify('world').to_dict() == session.store.load('world').to_dict()
    session.close()


def test_bad_source_database_never_publishes_any_backup(tmp_path):
    path, session = _new(tmp_path)
    session.store.db.execute(
        "UPDATE worlds SET sim_time=100 WHERE id='world'")
    with pytest.raises(Exception):
        session.checkpoint(tmp_path / 'bad-backup', code_commit=COMMIT)
    assert not (tmp_path / 'bad-backup').exists()
    session.close()


def test_wrong_version_reopen_preflight_does_not_modify_file(tmp_path):
    path, session = _new(tmp_path)
    session.close()
    with sqlite3.connect(path) as raw:
        raw.execute("UPDATE worlds SET rules_version=20 WHERE id='world'")
    prior = path.read_bytes()
    with pytest.raises(ValueError, match='unsupported'):
        ResumableTestSession.resume(path, 'world', 'carlos', disposable_test=True)
    assert path.read_bytes() == prior
    assert path.exists()


def test_unknown_player_or_missing_existing_file_never_reset(tmp_path):
    path, session = _new(tmp_path)
    session.close()
    before = path.read_bytes()
    with pytest.raises(PermissionError):
        ResumableTestSession.resume(
            path, 'world', 'basim', disposable_test=True)
    assert path.read_bytes() == before
    with pytest.raises(FileNotFoundError):
        ResumableTestSession.resume(
            tmp_path / 'missing.sqlite', 'world', 'carlos',
            disposable_test=True)
    assert not (tmp_path / 'missing.sqlite').exists()


def test_failed_fixture_setup_cleans_its_new_file_without_touching_others(tmp_path):
    path = tmp_path / 'bad-fixture.sqlite'
    def broken(db):
        db.create_world('world')
        raise RuntimeError('test interruption before fixture complete')
    with pytest.raises(RuntimeError):
        ResumableTestSession.create(
            path, 'world', 'carlos', broken, disposable_test=True)
    assert not path.exists()


def test_closed_session_cannot_keep_advancing_or_checkpoint(tmp_path):
    path, session = _new(tmp_path)
    gateway = session.gateway
    session.close()
    with pytest.raises((SessionClosed, sqlite3.ProgrammingError)):
        gateway.wait(10, command_id='after-close', expected_revision=0)
    with pytest.raises(PermissionError):
        session.checkpoint(tmp_path / 'forbidden', code_commit=COMMIT)
    assert not (tmp_path / 'forbidden').exists()


def test_restore_failed_copy_cleans_temp_and_never_creates_target(tmp_path, monkeypatch):
    path, session = _new(tmp_path)
    bundle = tmp_path / 'archive'
    session.checkpoint(bundle, code_commit=COMMIT)
    target = tmp_path / 'restored.sqlite'
    import carlos_sim.backup as backup
    original = backup.shutil.copyfile
    count = {'n': 0}
    def fail_second_copy(src, dest):
        count['n'] += 1
        if count['n'] == 2:
            raise OSError('simulated failure while copying destination')
        return original(src, dest)
    monkeypatch.setattr(backup.shutil, 'copyfile', fail_second_copy)
    with pytest.raises(OSError):
        restore_backup_bundle(bundle, target)
    assert not target.exists()
    assert not list(tmp_path.glob('.carlos-restore-*'))
    assert session.store.verify('world').to_dict() == session.store.load('world').to_dict()
    session.close()


def test_atomic_restore_target_and_no_implicit_world_changes(tmp_path):
    path, session = _new(tmp_path)
    old = session.store.load('world').to_dict()
    bundle = tmp_path / 'archive'
    session.checkpoint(bundle, code_commit=COMMIT)
    restored = tmp_path / 'new.sqlite'
    restore_backup_bundle(bundle, restored)
    with SQLiteEventStore(restored) as db:
        assert db.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.verify('world').to_dict() == old
    with pytest.raises(FileExistsError):
        restore_backup_bundle(bundle, restored)
    assert session.store.load('world').to_dict() == old
    session.close()
