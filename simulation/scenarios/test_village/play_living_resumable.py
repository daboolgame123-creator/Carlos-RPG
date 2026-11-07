"""PLAY-03: explicitly disposable saved seven-NPC living village.

Use --new to create only a new test world; --resume refuses incompatible,
unknown or malformed files. This is not Carlos's canonical story or an
approved production save (P0 remains unapproved).

From simulation/:
  PYTHONPATH=src python scenarios/test_village/play_living_resumable.py \
    --db ./living-test.sqlite --backups ./living-backups --new \
    --code-commit FULL_40_HEX_SHA --disposable-test
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex

from carlos_sim import canonical_hash
from carlos_sim.backup import verify_backup_bundle
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed

from living_player_fixture import (
    WORLD, PLAYER, setup_living_market_world, living_player_gateway,
)

HELP = ("scene | look | remember | status | handoff | move <road> "
        "| wait <seconds> | offers | supplies | purchases | gifts | buy <offer> <qty> <price> | give <npc> <item> <qty> | talk <npc> <kind> <words> | quit")


def render(result) -> None:
    print(f"[t={result.time} rev={result.revision}] {result.status}")
    for name, value in result.details.items():
        print(f"  {name}: {value}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Carlos living seven-NPC disposable saved test")
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--backups", type=Path, required=True)
    ap.add_argument("--code-commit", required=True, help="actual full 40-character Git SHA")
    selection = ap.add_mutually_exclusive_group(required=True)
    selection.add_argument("--new", action="store_true")
    selection.add_argument("--resume", action="store_true")
    ap.add_argument("--disposable-test", action="store_true")
    args = ap.parse_args()
    if not args.disposable_test:
        ap.error("experimental disposable-test acknowledgement is required")
    if not re.fullmatch(r"[0-9a-f]{40}", args.code_commit):
        ap.error("code-commit must be a genuine full lowercase 40-hex Git SHA")
    if not args.backups.is_dir() or args.backups.is_symlink():
        ap.error("pre-existing non-symlink backups directory is required")
    if args.new and any(args.backups.glob("living-test-rev-*")):
        ap.error("--new requires an empty dedicated living-test checkpoint directory")

    session = (
        ResumableTestSession.create(
            args.db, WORLD, PLAYER, setup_living_market_world,
            disposable_test=True)
        if args.new else ResumableTestSession.resume(
            args.db, WORLD, PLAYER, disposable_test=True)
    )

    def checkpoint(*, initial: bool = False) -> None:
        current = session.store.verify(WORLD)
        target = args.backups / f"living-test-rev-{current.revision:010d}"
        if target.exists():
            manifest = verify_backup_bundle(target)
            world = next((row for row in manifest["worlds"]
                          if row["world_id"] == WORLD), None)
            if (manifest["code_commit"] != args.code_commit
                    or world is None
                    or world["revision"] != current.revision
                    or world["state_sha256"] != canonical_hash(current.to_dict())):
                raise RuntimeError("existing checkpoint does not match this world/revision")
        else:
            if initial and args.resume:
                raise RuntimeError(
                    "resume requires an existing verified checkpoint for the saved revision")
            session.checkpoint(target, code_commit=args.code_commit)
        print(f"checkpoint: {target.name}, revision={current.revision}")

    with session:
        # Only a gateway bound to the exact verified store/clock/player is accepted.
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        # A resumed world must match any existing checkpoint at the same revision
        # before the player is offered a mutating command.
        checkpoint(initial=True)
        print("CARLOS — seven-NPC LIVING TEST WORLD, not canonical, P0 OPEN")
        print("Only explicit wait advances NPC autonomy and simulation time.")
        print(HELP)
        print("Use: id <request-id> <mutating command> to preserve a request ID")
        render(session.gateway.inspect())
        while True:
            try:
                raw = input("carlos> ")
            except EOFError:
                break
            try:
                tokens = shlex.split(raw)
            except ValueError as exc:
                print(f"Invalid command: {exc}")
                continue
            if not tokens:
                continue
            verb, *rest = tokens
            if verb in ("quit", "exit") and not rest:
                break
            if verb == "help" and not rest:
                print(HELP)
                continue
            if verb == "id" and len(rest) >= 2:
                cid, verb, *rest = rest
            else:
                cid = "living-cli-" + str(session.store.load(WORLD).revision)
            try:
                changed = False
                gateway = session.gateway
                rev = session.store.load(WORLD).revision
                if verb == "scene" and not rest:
                    result = gateway.inspect()
                elif verb == "handoff" and not rest:
                    print(json.dumps(session.handoff(),
                                     ensure_ascii=False, sort_keys=True))
                    continue
                elif verb == "remember" and not rest:
                    result = gateway.recall()
                elif verb == "status" and not rest:
                    result = gateway.status()
                elif verb == "supplies" and not rest:
                    result = gateway.supplies()
                elif verb == "offers" and not rest:
                    result = gateway.offers()
                elif verb == "purchases" and not rest:
                    result = gateway.purchases()
                elif verb == "gifts" and not rest:
                    result = gateway.gifts()
                elif verb == "look" and not rest:
                    result = gateway.observe(command_id=cid, expected_revision=rev)
                    changed = True
                elif verb == "move" and len(rest) == 1:
                    result = gateway.move(rest[0], command_id=cid,
                                          expected_revision=rev)
                    changed = True
                elif verb == "wait" and len(rest) == 1:
                    result = gateway.wait(int(rest[0]), command_id=cid,
                                          expected_revision=rev)
                    changed = True
                elif verb == "buy" and len(rest) == 3:
                    result = gateway.buy(
                        rest[0], int(rest[1]), int(rest[2]),
                        command_id=cid, expected_revision=rev)
                    changed = True
                elif verb == "give" and len(rest) == 3:
                    result = gateway.give(
                        rest[0], rest[1], int(rest[2]),
                        command_id=cid, expected_revision=rev)
                    changed = True
                elif verb == "talk" and len(rest) >= 3:
                    result = gateway.interact(
                        rest[0], kind=rest[1], text=" ".join(rest[2:]),
                        command_id=cid, expected_revision=rev)
                    changed = True
                else:
                    print("Unknown command; try help.")
                    continue
                render(result)
                if changed:
                    checkpoint()
            except (InvalidEvent, ValueError, DuplicateCommand, RevisionConflict,
                    SessionClosed, AdvanceLimitExceeded, PermissionError) as exc:
                print(f"Rejected: {exc}")
    print("Session closed; test SQLite persists. Use --resume to continue.")


if __name__ == "__main__":
    main()
