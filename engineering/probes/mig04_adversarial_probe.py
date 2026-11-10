"""MIG-04 test-only adversarial harness. NEVER a production save migrator.

Only operates on two disposable worlds produced by the pinned historical
runtime inside a temporary CI workspace. It does not offer a user-file CLI.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, canonical_hash
from carlos_sim.store import DuplicateCommand

OLD_VERSION = (41, 56)
TARGET_VERSION = (42, 57)
WORLD_IDS = ("village", "secondary-41-56")
assert (SCHEMA_VERSION, RULES_VERSION) == TARGET_VERSION
FLAGS = tuple(k for k in inspect.signature(SQLiteEventStore.append).parameters
              if k == "bootstrap" or k.endswith("_authorized"))


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_raises(exc_types, action, label: str) -> None:
    try:
        action()
    except exc_types:
        print("MIG04_REJECTED " + label)
        return
    raise AssertionError("unexpected acceptance: " + label)


def preflight(source: Path) -> dict:
    """Read-only integrity and provenance verification before creating target."""
    if not source.is_file() or source.is_symlink():
        raise ValueError("missing, unsafe or symlink source")
    # Test-only fail-closed policy. A real migrator must use an atomic SQLite
    # Backup API snapshot of a live WAL database; this probe is not that tool.
    if any(Path(str(source) + suffix).exists() for suffix in ("-wal", "-shm")):
        raise ValueError("live WAL/SHM requires consistent snapshot before migration")
    url = source.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(url, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("sqlite integrity failure")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("foreign key failure")
        worlds = list(conn.execute("SELECT * FROM worlds ORDER BY id"))
        if tuple(x["id"] for x in worlds) != tuple(sorted(WORLD_IDS)):
            raise ValueError("fixture worlds mismatch")
        plan = {}
        for world in worlds:
            world_id = world["id"]
            if (world["schema_version"], world["rules_version"]) != OLD_VERSION:
                raise ValueError("unsupported source version")
            genesis = json.loads(world["initial_state"])
            if canonical_hash(genesis) != world["initial_hash"]:
                raise ValueError("initial hash mismatch")
            if (genesis["schema_version"], genesis["rules_version"]) != OLD_VERSION:
                raise ValueError("source genesis version mismatch")
            if genesis["world_id"] != world_id or genesis["revision"] != 0:
                raise ValueError("invalid genesis")
            snaps = list(conn.execute(
                "SELECT revision,state,hash FROM snapshots WHERE world_id=?",
                (world_id,)))
            for snap in snaps:
                state = json.loads(snap["state"])
                if (canonical_hash(state) != snap["hash"] or
                        state["revision"] != snap["revision"] or
                        state["world_id"] != world_id or
                        (state["schema_version"], state["rules_version"]) != OLD_VERSION or
                        state["revision"] > world["revision"]):
                    raise ValueError("snapshot mismatch")
            cmds = list(conn.execute(
                "SELECT * FROM commands WHERE world_id=? ORDER BY first_revision",
                (world_id,)))
            events = list(conn.execute(
                "SELECT * FROM events WHERE world_id=? ORDER BY seq",
                (world_id,)))
            if not cmds or len(events) != world["revision"]:
                raise ValueError("empty or incomplete command/event history")
            if [e["seq"] for e in events] != list(range(1, len(events) + 1)):
                raise ValueError("event sequence gap")
            seq_cursor = 1
            groups = []
            for cmd in cmds:
                if cmd["first_revision"] != seq_cursor or cmd["last_revision"] < seq_cursor:
                    raise ValueError("command revision gap")
                group = [event for event in events
                         if event["command_id"] == cmd["command_id"]]
                if [e["seq"] for e in group] != list(
                        range(cmd["first_revision"], cmd["last_revision"] + 1)):
                    raise ValueError("command/event provenance mismatch")
                if any(c not in cmd.keys() for c in FLAGS):
                    raise ValueError("unknown historical capability")
                typed = []
                for event in group:
                    payload = json.loads(event["payload"])
                    if canonical_hash(payload) != event["hash"]:
                        raise ValueError("event hash mismatch")
                    typed.append(DomainEvent.from_dict(payload))
                capability = {name: bool(cmd[name]) for name in FLAGS}
                all_flags = {name: bool(cmd[name]) for name in FLAGS}
                request = {"events": [e.to_dict() for e in typed],
                           "expected_revision": seq_cursor - 1}
                request.update(all_flags)
                if canonical_hash(request) != cmd["request_hash"]:
                    raise ValueError("command request hash mismatch")
                groups.append((cmd["command_id"], seq_cursor - 1, typed,
                               capability, cmd["request_hash"],
                               [(e["seq"], e["command_id"], e["hash"]) for e in group]))
                seq_cursor += len(group)
            if seq_cursor - 1 != world["revision"]:
                raise ValueError("head revision mismatch")
            plan[world_id] = {
                "groups": groups, "event_count": len(events),
                "revision": world["revision"], "time": world["sim_time"]}
        return plan
    finally:
        conn.close()


def create_destination(source: Path, destination: Path, expected: dict,
                       inject: str | None = None) -> None:
    """Proof-only exclusive publish. Never accepts arbitrary user files."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("destination already exists")
    plan = preflight(source)
    assert set(plan) == set(WORLD_IDS)
    stage_dir = Path(tempfile.mkdtemp(prefix=".mig04-stage-", dir=destination.parent))
    staging = stage_dir / "unpublished.sqlite"
    try:
        if inject == "before_rebuild":
            raise RuntimeError("simulated crash before rebuild")
        with SQLiteEventStore(staging) as target:
            for world_id in WORLD_IDS:
                world = plan[world_id]
                target.create_world(world_id)
                clock = TimeEngine(target)
                clock.open_session(world_id)
                try:
                    state = target.load(world_id)
                    for idx, (command_id, revision, events, flags, request_hash, receipts) in enumerate(world["groups"]):
                        assert state.revision == revision
                        state = target.append(world_id, command_id, state.revision,
                                              events, **flags)
                        if inject == "after_first_command" and idx == 0:
                            raise RuntimeError("simulated crash mid conversion")
                        actual_req = target.db.execute(
                            "SELECT request_hash FROM commands WHERE world_id=? AND command_id=?",
                            (world_id, command_id)).fetchone()[0]
                        assert actual_req == request_hash
                        actual_receipts = target.db.execute(
                            "SELECT seq,command_id,hash FROM events WHERE world_id=? AND command_id=? ORDER BY seq",
                            (world_id, command_id)).fetchall()
                        assert actual_receipts == receipts
                    assert state.revision == world["revision"]
                    assert state.time == world["time"]
                    assert target.verify(world_id).to_dict() == state.to_dict()
                    assert target.snapshot(world_id).to_dict() == state.to_dict()
                    historical_expected = dict(expected[world_id])
                    historical_expected["schema_version"] = 42
                    historical_expected["rules_version"] = 57
                    assert state.to_dict() == historical_expected
                    if world_id == "village" and inject is None:
                        duplicate = DomainEvent(
                            "TimeAdvanced", None, "deliberately different payload",
                            state.time, {"from": 0, "to": 1})
                        require_raises(DuplicateCommand,
                            lambda: target.append(world_id, world["groups"][0][0],
                                                  state.revision, [duplicate],
                                                  clock_authorized=True),
                            "duplicate command with different request hash")
                        assert target.verify(world_id).to_dict() == state.to_dict()
                finally:
                    clock.close_session(world_id)
            assert target.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert target.db.execute("PRAGMA foreign_key_check").fetchall() == []
        if inject == "before_publish":
            raise RuntimeError("simulated crash before publish")
        # Linux CI: same-filesystem hard-link creation is exclusive and atomic.
        # Existing target/symlink cannot be overwritten by os.link().
        os.link(staging, destination)
        parent_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        with SQLiteEventStore(destination) as reopened:
            for world_id in WORLD_IDS:
                actual = reopened.verify(world_id).to_dict()
                old = dict(expected[world_id])
                old.update(schema_version=42, rules_version=57)
                assert actual == old
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)


def run() -> None:
    source = Path("fixture-old-41-56.sqlite").resolve()
    expected = json.loads(Path("fixture-expected.json").read_text())
    if set(expected) != set(WORLD_IDS):
        raise AssertionError("unexpected fixture worlds")
    source_hash = fingerprint(source)
    with tempfile.TemporaryDirectory(prefix="mig04-adversarial-") as work:
        root = Path(work)
        old = preflight(source)
        assert len(old["village"]["groups"]) == 6
        assert old["village"]["event_count"] == 51
        assert old["secondary-41-56"]["event_count"] == 2
        assert preflight(source)["village"]["event_count"] == 51
        assert fingerprint(source) == source_hash
        print("MIG04_DRY_RUN", json.dumps({
            "worlds": len(old), "commands": sum(len(x["groups"]) for x in old.values()),
            "events": sum(x["event_count"] for x in old.values()),
            "source_unchanged": True}, sort_keys=True), flush=True)

        for mutation in ("event_hash", "event_gap", "missing_command",
                         "snapshot_hash", "wrong_version", "command_capability"):
            damaged = root / (mutation + ".sqlite")
            shutil.copy2(source, damaged)
            with sqlite3.connect(damaged) as db:
                if mutation == "event_hash":
                    db.execute("UPDATE events SET hash='00' WHERE world_id='village' AND seq=2")
                elif mutation == "event_gap":
                    db.execute("DELETE FROM events WHERE world_id='village' AND seq=2")
                elif mutation == "missing_command":
                    db.execute("PRAGMA foreign_keys=OFF")
                    db.execute("DELETE FROM commands WHERE world_id='village' AND command_id='setup'")
                elif mutation == "snapshot_hash":
                    db.execute("UPDATE snapshots SET hash='00' WHERE world_id='village'")
                elif mutation == "wrong_version":
                    db.execute("UPDATE worlds SET schema_version=42 WHERE id='village'")
                elif mutation == "command_capability":
                    db.execute("UPDATE commands SET bootstrap=0 WHERE world_id='village' AND command_id='setup'")
            dest = root / (mutation + "-dest.sqlite")
            require_raises((ValueError, sqlite3.DatabaseError),
                           lambda: create_destination(damaged, dest, expected),
                           mutation)
            assert not dest.exists(), mutation
        print("MIG04_CORRUPTION_REJECTION", 6, flush=True)

        for stage in ("before_rebuild", "after_first_command", "before_publish"):
            dest = root / (stage + ".sqlite")
            require_raises(RuntimeError,
                           lambda: create_destination(source, dest, expected, inject=stage),
                           stage)
            assert not dest.exists()
            assert fingerprint(source) == source_hash
        print("MIG04_INTERRUPTION_SIMULATED", 3, flush=True)

        for use_symlink in (False, True):
            dest = root / ("symlink-target.sqlite" if use_symlink else "existing-target.sqlite")
            sentinel = root / "sentinel"
            sentinel.write_bytes(b"DO_NOT_OVERWRITE")
            if use_symlink:
                dest.symlink_to(sentinel)
            else:
                dest.write_bytes(sentinel.read_bytes())
            require_raises(FileExistsError,
                           lambda: create_destination(source, dest, expected),
                           "exclusive target" + (" symlink" if use_symlink else " regular"))
            assert dest.read_bytes() == b"DO_NOT_OVERWRITE"
            assert sentinel.read_bytes() == b"DO_NOT_OVERWRITE"

        destination = root / "new-target.sqlite"
        create_destination(source, destination, expected)
        before = fingerprint(destination)
        require_raises(FileExistsError,
                       lambda: create_destination(source, destination, expected),
                       "repeat target publication")
        assert fingerprint(destination) == before
        assert fingerprint(source) == source_hash
        assert not list(root.glob(".mig04-stage-*"))
        print("MIG04_SUCCESS", json.dumps({
            "source": [41, 56], "target": [42, 57],
            "worlds": 2, "events": 53, "commands": 7,
            "corrupt_variants_rejected": 6, "simulated_interruptions": 3,
            "exclusive_collision_and_symlink_refusal": True,
            "repeated_publication_refused": True,
            "successful_isolated_publish_and_replay": True,
            "original_sha256_unchanged": True,
            "actual_power_loss_or_Windows_tested": False,
            "production_migrator_approved": False}, sort_keys=True), flush=True)


if __name__ == "__main__":
    run()
