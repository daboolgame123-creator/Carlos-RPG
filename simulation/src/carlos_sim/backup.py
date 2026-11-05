"""01-Z P0 *candidate*: isolated, consistent SQLite backup and recovery.

Use only from trusted offline Python; this is not network authentication.
P0 stays OPEN until independent restore/recovery review. Bundles are NOT
migration tools, and an existing target is never overwritten.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp, mkstemp
import json
import os
import re
import shutil
import sqlite3

from .domain import SCHEMA_VERSION, RULES_VERSION, canonical_hash
from .store import SQLiteEventStore


class BackupError(ValueError):
    """A backup/restore request failed closed; source remains unchanged."""


_BUNDLE_DB = 'world.sqlite'
_MANIFEST = 'manifest.json'
_COMMIT_RE = re.compile(r'[0-9a-f]{40}')


def _digest(path: Path) -> str:
    result = sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def _audit(path: Path) -> list[dict]:
    """Audit ALL included worlds, not just the requested player world."""
    with SQLiteEventStore(path) as store:
        integrity = store.db.execute('PRAGMA integrity_check').fetchall()
        if integrity != [('ok',)]:
            raise BackupError('SQLite integrity_check failed')
        ids = [v[0] for v in store.db.execute('SELECT id FROM worlds ORDER BY id')]
        if not ids:
            raise BackupError('backup contains no world')
        data = []
        for world_id in ids:
            state = store.verify(world_id)
            rows = store.db.execute(
                'SELECT schema_version, rules_version, revision, sim_time '
                'FROM worlds WHERE id=?', (world_id,)).fetchone()
            if rows != (SCHEMA_VERSION, RULES_VERSION, state.revision, state.time):
                raise BackupError('world metadata differs from its replay')
            data.append({
                'world_id': world_id,
                'schema': rows[0], 'rules': rows[1],
                'revision': state.revision, 'time': state.time,
                'state_sha256': canonical_hash(state.to_dict()),
                'events': store.db.execute(
                    'SELECT count(*) FROM events WHERE world_id=?',
                    (world_id,)).fetchone()[0],
                'commands': store.db.execute(
                    'SELECT count(*) FROM commands WHERE world_id=?',
                    (world_id,)).fetchone()[0],
                'snapshots': store.db.execute(
                    'SELECT count(*) FROM snapshots WHERE world_id=?',
                    (world_id,)).fetchone()[0],
            })
        return data


def _require_new_path(path: Path) -> None:
    if not path.name or not path.parent.is_dir():
        raise BackupError('parent directory must exist')
    if os.path.lexists(path):
        raise FileExistsError('destination already exists; refusing to overwrite')


def _manifest_checked(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != {
        'format', 'created_utc', 'code_commit', 'source_world',
        'schema', 'rules', 'database_sha256', 'database_bytes', 'worlds',
    }:
        raise BackupError('invalid backup manifest fields')
    if (payload['format'] != 1
            or not isinstance(payload['created_utc'], str)
            or not payload['created_utc'].endswith('+00:00')
            or not isinstance(payload['code_commit'], str)
            or _COMMIT_RE.fullmatch(payload['code_commit']) is None
            or type(payload['schema']) is not int
            or type(payload['rules']) is not int
            or payload['schema'] != SCHEMA_VERSION
            or payload['rules'] != RULES_VERSION
            or not isinstance(payload['source_world'], str)
            or not payload['source_world']
            or not isinstance(payload['database_sha256'], str)
            or re.fullmatch(r'[0-9a-f]{64}', payload['database_sha256']) is None
            or type(payload['database_bytes']) is not int
            or payload['database_bytes'] <= 0
            or not isinstance(payload['worlds'], list)
            or not payload['worlds']):
        raise BackupError('backup manifest malformed or incompatible')
    return payload


def _validate_database_against_manifest(db_path: Path, payload: dict) -> None:
    if (db_path.stat().st_size != payload['database_bytes']
            or _digest(db_path) != payload['database_sha256']):
        raise BackupError('backup database digest/size mismatch')
    observed = _audit(db_path)
    if observed != payload['worlds'] or payload['source_world'] not in {
        x['world_id'] for x in observed
    }:
        raise BackupError('backup world replay/manifest mismatch')


def create_backup_bundle(store: SQLiteEventStore, world_id: str,
                         bundle_dir: str | Path, *,
                         code_commit: str) -> dict:
    """Publish a complete independent backup folder or publish nothing.

    sqlite3.backup() captures one consistent database instant, including WAL.
    The source may change *after* capture; manifest describes the BACKUP state.
    """
    if (not isinstance(world_id, str) or not world_id
            or not isinstance(code_commit, str)
            or _COMMIT_RE.fullmatch(code_commit) is None):
        raise BackupError('world ID and full Git commit SHA required')
    target = Path(bundle_dir)
    _require_new_path(target)
    # Refuse a corrupt or mismatched source without touching a destination.
    store.verify(world_id)
    scratch = Path(mkdtemp(prefix='.carlos-backup-staging-', dir=target.parent))
    published = False
    try:
        db_copy = scratch / _BUNDLE_DB
        with closing(sqlite3.connect(str(db_copy))) as connection:
            store.db.backup(connection)
        worlds = _audit(db_copy)
        if world_id not in {x['world_id'] for x in worlds}:
            raise BackupError('requested world was not captured')
        manifest = {
            'format': 1,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'code_commit': code_commit,
            'source_world': world_id,
            'schema': SCHEMA_VERSION, 'rules': RULES_VERSION,
            'database_sha256': _digest(db_copy),
            'database_bytes': db_copy.stat().st_size,
            'worlds': worlds,
        }
        with (scratch / _MANIFEST).open('x', encoding='utf-8') as out:
            json.dump(manifest, out, sort_keys=True, indent=2, ensure_ascii=False)
            out.write('\n')
        _manifest_checked(manifest)
        _require_new_path(target)
        os.rename(scratch, target)
        published = True
        return manifest
    finally:
        if not published:
            shutil.rmtree(scratch, ignore_errors=True)


def verify_backup_bundle(bundle_dir: str | Path) -> dict:
    """Verify checksum, version, SQLite integrity and every replay on a COPY."""
    folder = Path(bundle_dir)
    if (not folder.is_dir() or folder.is_symlink()
            or {p.name for p in folder.iterdir()} != {_BUNDLE_DB, _MANIFEST}):
        raise BackupError('not a complete backup bundle')
    database, manifest_file = folder / _BUNDLE_DB, folder / _MANIFEST
    if (database.is_symlink() or not database.is_file()
            or manifest_file.is_symlink() or not manifest_file.is_file()):
        raise BackupError('backup content must be regular files, not links')
    try:
        with manifest_file.open('r', encoding='utf-8') as stream:
            manifest = _manifest_checked(json.load(stream))
    except (UnicodeError, json.JSONDecodeError, OSError) as exc:
        raise BackupError('cannot parse backup manifest') from exc
    # Keep verification away from immutable bundle bytes; SQLiteEventStore's
    # CREATE TABLE IF NOT EXISTS is not guaranteed to be read-only.
    with TemporaryDirectory(prefix='carlos-backup-audit-') as root:
        copy_path = Path(root) / _BUNDLE_DB
        shutil.copyfile(database, copy_path)
        _validate_database_against_manifest(copy_path, manifest)
    return manifest


def restore_backup_bundle(bundle_dir: str | Path, target_db: str | Path) -> dict:
    """Verify before publication; never modify a pre-existing destination."""
    target = Path(target_db)
    _require_new_path(target)
    manifest = verify_backup_bundle(bundle_dir)
    handle, name = mkstemp(prefix='.carlos-restore-', suffix='.sqlite',
                           dir=target.parent)
    os.close(handle)
    staging = Path(name)
    published = False
    try:
        shutil.copyfile(Path(bundle_dir) / _BUNDLE_DB, staging)
        _validate_database_against_manifest(staging, manifest)
        # Atomic create-if-absent: unlike os.replace/rename, an existing save
        # (including a symlink) is never clobbered. Same parent => same FS.
        os.link(staging, target)
        published = True
        return manifest
    finally:
        staging.unlink(missing_ok=True)
