"""MIG-04b proof-only Linux SIGKILL and live WAL refusal checks.

Run only on the intentionally disposable fixture generated in GitHub Actions.
This script does NOT produce a general-purpose file migration mechanism.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile

import mig04_adversarial_probe as migration
from carlos_sim import SQLiteEventStore

assert sys.platform.startswith("linux"), "this probe is Linux-only"


def test_killed_child(mode: str, source: Path, expected: dict, root: Path) -> None:
    destination = root / (mode + ".sqlite")
    command = [sys.executable, str(Path(__file__).resolve()),
               "--child", mode, str(source), str(destination),
               str(root / "fixture-expected.json")]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, check=False)
    if result.returncode != -signal.SIGKILL:
        raise AssertionError(
            "child must be terminated by real SIGKILL for " + mode +
            " returncode=" + str(result.returncode) +
            " stderr=" + result.stderr[-1200:])
    if mode == "after_link":
        if not destination.exists():
            raise AssertionError("link must have completed before SIGKILL")
        with SQLiteEventStore(destination) as store:
            for world_id, source_state in expected.items():
                current = store.verify(world_id).to_dict()
                gold = dict(source_state)
                gold["schema_version"] = 42
                gold["rules_version"] = 57
                assert current == gold
    else:
        assert not destination.exists(), "unpublished destination after SIGKILL"
    assert migration.fingerprint(source) == SOURCE_SHA
    # SIGKILL leaves private unlinked stage files, not published targets.
    for folder in root.glob(".mig04-stage-*"):
        shutil.rmtree(folder)
    print("MIG04B_PROCESS_SIGKILL",json.dumps({
        "stage":mode, "true_sigkill":True,
        "target_published":destination.exists(),
        "target_valid_if_published":True,
        "source_unchanged":True},sort_keys=True),flush=True)


def child(mode: str, source: Path, dest: Path, expected: dict) -> None:
    if mode == "after_first_append":
        old = SQLiteEventStore.append
        triggered = [False]
        def append_then_kill(store, *args, **kwargs):
            state = old(store, *args, **kwargs)
            if not triggered[0]:
                triggered[0] = True
                os.kill(os.getpid(), signal.SIGKILL)
            return state
        SQLiteEventStore.append = append_then_kill
    else:
        original_link = os.link
        def fatal_link(staging, destination):
            if mode == "before_link":
                os.kill(os.getpid(), signal.SIGKILL)
            original_link(staging, destination)
            if mode == "after_link":
                os.kill(os.getpid(), signal.SIGKILL)
        os.link = fatal_link
    migration.create_destination(source, dest, expected)
    raise AssertionError("fatal SIGKILL injection failed to terminate process")


def main() -> None:
    global SOURCE_SHA
    if len(sys.argv) >= 2 and sys.argv[1] == "--child":
        assert len(sys.argv) == 6
        _, _, mode, src, target, manifest = sys.argv
        assert mode in {"after_first_append","before_link","after_link"}
        child(mode,Path(src),Path(target),json.loads(Path(manifest).read_text()))
        return
    source = Path("fixture-old-41-56.sqlite").resolve()
    expected = json.loads(Path("fixture-expected.json").read_text())
    assert len(expected) == 2
    SOURCE_SHA = migration.fingerprint(source)
    with tempfile.TemporaryDirectory(prefix="mig04b-live-") as temp:
        root = Path(temp)
        shutil.copy2("fixture-expected.json",root/"fixture-expected.json")
        for mode in ("after_first_append","before_link","after_link"):
            test_killed_child(mode,source,expected,root)

        # WAL with an actual pending WAL journal and an open writer. We refuse
        # the disposable copy; this does not solve multi-connection consistency.
        live_copy=root/"active-wal-source.sqlite"
        shutil.copy2(source,live_copy)
        with sqlite3.connect(live_copy) as conn:
            assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower()=="wal"
            conn.execute("CREATE TABLE mig04_wal_probe (n INTEGER NOT NULL)")
            conn.execute("INSERT INTO mig04_wal_probe VALUES (1)")
            conn.commit()
            assert Path(str(live_copy)+"-wal").exists()
            dest=root/"rejected-wal-target.sqlite"
            migration.require_raises(ValueError,
                 lambda:migration.create_destination(live_copy,dest,expected),
                 "active WAL sidecar refused until consistent backup")
            assert not dest.exists()
        assert migration.fingerprint(source)==SOURCE_SHA
        print("MIG04B_LIVE_WAL_REJECTED",json.dumps({
             "writer_wal_verified":True,"target_unpublished":True,
             "real_source_unchanged":True,
             "concurrent_backup_approved":False},sort_keys=True),flush=True)

    print("MIG04B_SUCCESS",json.dumps({
         "real_sigkill_points":3,
         "pre_publish_sigkill_no_target":2,
         "post_link_sigkill_complete_target":1,
         "active_wal_refused":True,
         "actual_power_outage_tested":False,
         "windows_tested":False},sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
