"""MIG-04c: test-only consistent SQLite Online Backup API with an active WAL writer.

Fixture: generated under pinned real Schema 41 / Rules 56 runtime in CI.
Destination: disposable 42 / 57 reconstruction. NEVER a player-save migrator.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import time

import mig04_adversarial_probe as migration
from carlos_sim import SQLiteEventStore

WRITE_COUNT = 30
SOURCE_NAME = "fixture-old-41-56.sqlite"


def domain_ledger_digest(connection: sqlite3.Connection) -> str:
    """The writer may add probe records but may never alter game-domain receipts."""
    digest = hashlib.sha256()
    for table in ("worlds", "commands", "events", "snapshots"):
        rows = connection.execute("SELECT * FROM " + table + " ORDER BY rowid").fetchall()
        digest.update(repr((table, rows)).encode("utf-8"))
    return digest.hexdigest()


def check_sqlite(path: Path) -> None:
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def prove_active_backup(source: Path, expected: dict, root: Path) -> dict:
    live = root / "active-legacy-wal.sqlite"
    snapshot = root / "isolated-backup.sqlite"
    destination = root / "migrated-disposable.sqlite"
    shutil.copy2(source, live)

    with closing(sqlite3.connect(live, timeout=15)) as anchor:
        assert anchor.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
        anchor.execute("CREATE TABLE migration_probe_bulk (id INTEGER PRIMARY KEY, bytes TEXT NOT NULL)")
        anchor.executemany(
            "INSERT INTO migration_probe_bulk VALUES (?, ?)",
            ((n, "x" * 1000) for n in range(7000)),
        )
        anchor.execute("CREATE TABLE migration_probe_ledger (n INTEGER PRIMARY KEY, amount INTEGER NOT NULL)")
        anchor.execute(
            "CREATE TABLE migration_probe_counter "
            "(id INTEGER PRIMARY KEY CHECK(id=1), n INTEGER NOT NULL, total INTEGER NOT NULL)"
        )
        anchor.execute("INSERT INTO migration_probe_counter VALUES (1,0,0)")
        anchor.commit()
        assert Path(str(live) + "-wal").exists(), "source must have active WAL"
        original_game_digest = domain_ledger_digest(anchor)
        first_backup_page = threading.Event()
        first_writer_commit = threading.Event()
        errors: list[BaseException] = []
        progress_calls = [0]
        write_commits = [0]

        def write_during_backup() -> None:
            try:
                if not first_backup_page.wait(10):
                    raise AssertionError("backup did not begin before writer timeout")
                with closing(sqlite3.connect(live, timeout=15)) as writer:
                    for n in range(1, WRITE_COUNT + 1):
                        with writer:
                            writer.execute(
                                "INSERT INTO migration_probe_ledger (n,amount) VALUES (?,?)", (n, n)
                            )
                            writer.execute(
                                "UPDATE migration_probe_counter SET n=?,total=total+? WHERE id=1", (n, n)
                            )
                        write_commits[0] = n
                        first_writer_commit.set()
                        time.sleep(0.001)
            except BaseException as exc:
                errors.append(exc)
                first_writer_commit.set()

        def progress(status: int, remaining: int, total: int) -> None:
            progress_calls[0] += 1
            if progress_calls[0] == 1:
                first_backup_page.set()
                if not first_writer_commit.wait(10):
                    raise AssertionError("no concurrent WAL commit during backup")
                if errors:
                    raise AssertionError("WAL writer failed during backup") from errors[0]

        thread = threading.Thread(target=write_during_backup, daemon=True)
        thread.start()
        # Read-only connection still observes a coherent WAL snapshot; .backup()
        # is the essential step that physical shutil.copy2 cannot replace.
        try:
            with closing(sqlite3.connect(live.as_uri() + "?mode=ro", uri=True, timeout=15)) as reader:
                with closing(sqlite3.connect(snapshot)) as target:
                    reader.backup(target, pages=5, sleep=0.001, progress=progress)
        finally:
            first_backup_page.set()
            thread.join(timeout=20)
        # Backup API can preserve the *source* WAL journal_mode in the copied
        # database header. Normalize ONLY this isolated, fully closed copy,
        # otherwise a strict read-only preflight can leave WAL/SHM sidecars.
        with closing(sqlite3.connect(snapshot, timeout=15)) as normalized:
            normalized.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            assert normalized.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower() == "delete"
        assert not any(
            Path(str(snapshot) + suffix).exists() for suffix in ("-wal", "-shm")
        ), "offline backup must have no sidecars"
        assert not thread.is_alive(), "writer did not finish"
        assert not errors, f"writer errors: {errors!r}"
        assert write_commits[0] == WRITE_COUNT
        assert progress_calls[0] > 1, "must have multi-step Backup API"
        assert Path(str(live) + "-wal").exists(), "open WAL source must remain active"
        assert domain_ledger_digest(anchor) == original_game_digest
        with closing(sqlite3.connect(snapshot)) as backed:
            snap_digest = domain_ledger_digest(backed)
            count, total = backed.execute(
                "SELECT COUNT(*),COALESCE(SUM(amount),0) FROM migration_probe_ledger"
            ).fetchone()
            n, recorded_total = backed.execute(
                "SELECT n,total FROM migration_probe_counter WHERE id=1"
            ).fetchone()
            assert count == n and total == recorded_total, "torn WAL snapshot"
            assert total == n * (n + 1) // 2, "non-atomic writer transfer"
            assert 1 <= n <= WRITE_COUNT, "backup missed concurrent writer"
            assert backed.execute(
                "SELECT COALESCE(MIN(n),0),COALESCE(MAX(n),0) FROM migration_probe_ledger"
            ).fetchone() == (1, n)
            assert snap_digest == original_game_digest, "game ledger changed while backing up"
        check_sqlite(snapshot)

        # Reuse existing strict historical provenance validation, NOT a header
        # rewrite. No live WAL source is passed to the test-only migrator.
        plan = migration.preflight(snapshot)
        assert set(plan) == set(migration.WORLD_IDS)
        migration.create_destination(snapshot, destination, expected)
        with SQLiteEventStore(destination) as migrated:
            for world_id, historical in expected.items():
                expected_state = dict(historical)
                expected_state.update(schema_version=42, rules_version=57)
                assert migrated.verify(world_id).to_dict() == expected_state

        previous_target = migration.fingerprint(destination)
        migration.require_raises(
            FileExistsError,
            lambda: migration.create_destination(snapshot, destination, expected),
            "refuse to replace reconstructed target",
        )
        assert migration.fingerprint(destination) == previous_target
        assert domain_ledger_digest(anchor) == original_game_digest
        return {
            "active_wal": True,
            "live_writer_commits": write_commits[0],
            "snapshot_committed_prefix": n,
            "backup_progress_calls": progress_calls[0],
            "no_torn_transactions": True,
            "all_historical_game_receipts_unchanged": True,
            "old_source_live_copy_not_replaced": True,
            "new_target_verified": True,
            "no_overwrite": True,
        }


def main() -> None:
    old = Path(SOURCE_NAME).resolve()
    expected = json.loads(Path("fixture-expected.json").read_text(encoding="utf-8"))
    assert set(expected) == set(migration.WORLD_IDS)
    old_file_sha = migration.fingerprint(old)
    with tempfile.TemporaryDirectory(prefix="mig04c-online-backup-") as temp:
        proof = prove_active_backup(old, expected, Path(temp))
    assert migration.fingerprint(old) == old_file_sha, "immutable old fixture changed"
    proof.update({
        "source_unchanged": True,
        "test_only": True,
        "power_loss_tested": False,
        "windows_tested": False,
        "production_migration_approved": False,
    })
    print("MIG04C_SUCCESS " + json.dumps(proof, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
