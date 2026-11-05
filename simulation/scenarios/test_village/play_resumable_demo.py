"""Explicit disposable 01-Z player demo, checkpointed with independent SQLite backups.

The fixture is NOT Carlos's canonical story. P0 independent review is OPEN.

From simulation/:
    PYTHONPATH=src python scenarios/test_village/play_resumable_demo.py \
        --db ./test-carlos.sqlite --backups ./test-backups --new \
        --code-commit FULL_40_HEX_SHA --disposable-test

On later launch replace --new with --resume. The folder in --backups
must already exist; each changing command creates a distinct checkpoint.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shlex

from carlos_sim import canonical_hash
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.backup import verify_backup_bundle
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed
from play_local import setup


def render(result):
    print(f"[t={result.time} rev={result.revision}] {result.status}")
    for key, val in result.details.items():
        print(f"  {key}: {val}")


def main():
    ap = argparse.ArgumentParser(description="Carlos disposable resumed-play proof")
    ap.add_argument('--db', type=Path, required=True)
    ap.add_argument('--backups', type=Path, required=True)
    ap.add_argument('--code-commit', required=True,
                    help='actual full 40-character Git revision')
    selection = ap.add_mutually_exclusive_group(required=True)
    selection.add_argument('--new', action='store_true')
    selection.add_argument('--resume', action='store_true')
    ap.add_argument('--disposable-test', action='store_true')
    args = ap.parse_args()
    if not args.disposable_test:
        ap.error('experimental disposable-test acknowledgement required')
    if not args.backups.is_dir() or args.backups.is_symlink():
        ap.error('pre-existing regular backups directory required')
    session = (ResumableTestSession.create(
        args.db, 'demo', 'carlos', setup, disposable_test=True)
        if args.new else ResumableTestSession.resume(
            args.db, 'demo', 'carlos', disposable_test=True))

    def checkpoint():
        st = session.store.verify('demo')
        target = args.backups / f"test-carlos-rev-{st.revision:010d}"
        if target.exists():
            manifest = verify_backup_bundle(target)
            record = next((x for x in manifest['worlds']
                           if x['world_id'] == 'demo'), None)
            if (manifest['code_commit'] != args.code_commit or record is None
                    or record['revision'] != st.revision
                    or record['state_sha256'] != canonical_hash(st.to_dict())):
                raise RuntimeError('checkpoint name collision/mismatch')
        else:
            manifest = session.checkpoint(target, code_commit=args.code_commit)
        print(f"checkpoint: {target.name}, revision={st.revision}")
        return manifest

    with session:
        checkpoint()  # backup the verified starting/resumed position
        print("01-Z TEST WORLD (not canonical Carlos, P0 independent review OPEN)")
        print("Commands: look | remember | status | move <road> | wait <seconds> "
              "| talk <npc> <kind> <words> | quit")
        print("Prefix mutating command with: id <request-id> <command> ...")
        render(session.gateway.inspect())
        while True:
            try:
                raw = input('carlos> ')
            except EOFError:
                break
            try:
                words = shlex.split(raw)
            except ValueError as exc:
                print(f"Invalid command: {exc}")
                continue
            if not words:
                continue
            verb, *args_ = words
            if verb in ('quit', 'exit'):
                break
            if verb == 'help':
                print("look | remember | status | move <road> | wait <seconds> "
                      "| talk <npc> <kind> <words> | quit")
                continue
            if verb == 'id' and len(args_) >= 2:
                explicit, verb, *args_ = args_
                cid = explicit
            else:
                cid = 'cli-' + str(session.store.load('demo').revision)
            try:
                changed = False
                if verb == 'look' and not args_:
                    print('request_id:', cid)
                    result = session.gateway.observe(
                        command_id=cid,
                        expected_revision=session.store.load('demo').revision)
                    changed = True
                elif verb == 'remember' and not args_:
                    result = session.gateway.recall()
                elif verb == 'status' and not args_:
                    result = session.gateway.status()
                elif verb == 'move' and len(args_) == 1:
                    print('request_id:', cid)
                    result = session.gateway.move(
                        args_[0], command_id=cid,
                        expected_revision=session.store.load('demo').revision)
                    changed = True
                elif verb == 'wait' and len(args_) == 1:
                    print('request_id:', cid)
                    result = session.gateway.wait(
                        int(args_[0]), command_id=cid,
                        expected_revision=session.store.load('demo').revision)
                    changed = True
                elif verb == 'talk' and len(args_) >= 3:
                    print('request_id:', cid)
                    result = session.gateway.interact(
                        args_[0], kind=args_[1], text=' '.join(args_[2:]),
                        command_id=cid,
                        expected_revision=session.store.load('demo').revision)
                    changed = True
                else:
                    print("Unknown command; try help.")
                    continue
                render(result)
                if changed:
                    checkpoint()
            except (InvalidEvent, ValueError, RevisionConflict,
                    DuplicateCommand, SessionClosed, AdvanceLimitExceeded,
                    PermissionError) as exc:
                print(f"Rejected: {exc}")
    print("Session closed. Test database remains; run --resume to reopen.")


if __name__ == '__main__':
    main()
