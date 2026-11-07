"""PLAY-02 offline seven-NPC living village; a disposable playable test world.

From simulation/: PYTHONPATH=src python scenarios/test_village/play_living_village.py
Player chooses Carlos's actions; NPC intentions run ONLY on explicit wait.
The temporary SQLite database disappears on exit. No canonical story import.
"""
from __future__ import annotations

import json
import shlex
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.player_handoff import player_handoff
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed
from living_player_fixture import WORLD, living_player_gateway, setup_living_market_world

HELP = ("scene | look | status | remember | handoff | move <road> "
        "| wait <seconds> | offers | supplies | purchases | buy <offer> <qty> <price> | talk <npc> <kind> <words> | quit")


def render(result) -> None:
    print(f"[t={result.time} rev={result.revision}] {result.status}")
    for key, value in result.details.items():
        print(f"  {key}: {value}")


def main() -> None:
    print("CARLOS — living disposable village (7 autonomous NPCs, non-canonical)")
    print("NPCs act and travel only when you use wait; Carlos never moves himself.")
    print(HELP)
    with TemporaryDirectory(prefix="carlos-living-") as temp:
        with SQLiteEventStore(Path(temp) / "living.sqlite") as store:
            setup_living_market_world(store)
            clock = TimeEngine(store)
            clock.open_session(WORLD)
            gateway = living_player_gateway(store, clock)
            count = 0
            render(gateway.inspect())
            while True:
                try:
                    raw = input("carlos> ")
                except EOFError:
                    break
                try:
                    parts = shlex.split(raw)
                except ValueError as exc:
                    print(f"Invalid command: {exc}")
                    continue
                if not parts:
                    continue
                verb, *args = parts
                if verb in ("quit", "exit"):
                    break
                if verb == "help":
                    print(HELP)
                    continue
                try:
                    if verb == "scene" and not args:
                        result = gateway.inspect()
                    elif verb == "handoff" and not args:
                        print(json.dumps(player_handoff(gateway),
                                         ensure_ascii=False, sort_keys=True))
                        continue
                    elif verb == "remember" and not args:
                        result = gateway.recall()
                    elif verb == "status" and not args:
                        result = gateway.status()
                    elif verb == "supplies" and not args:
                        result = gateway.supplies()
                    elif verb == "offers" and not args:
                        result = gateway.offers()
                    elif verb == "purchases" and not args:
                        result = gateway.purchases()
                    elif verb in ("look", "move", "wait", "talk", "buy"):
                        if (verb == "look" and args or
                            verb == "move" and len(args) != 1 or
                            verb == "wait" and len(args) != 1 or
                            verb == "talk" and len(args) < 3 or
                            verb == "buy" and len(args) != 3):
                            print("Invalid command arguments. Type help.")
                            continue
                        count += 1
                        cid = f"living-{count}"
                        revision = store.load(WORLD).revision
                        if verb == "look":
                            result = gateway.observe(
                                command_id=cid, expected_revision=revision)
                        elif verb == "move":
                            result = gateway.move(args[0], command_id=cid,
                                                  expected_revision=revision)
                        elif verb == "wait":
                            result = gateway.wait(int(args[0]), command_id=cid,
                                                  expected_revision=revision)
                        elif verb == "buy":
                            result = gateway.buy(args[0], int(args[1]), int(args[2]),
                                                 command_id=cid,
                                                 expected_revision=revision)
                        else:
                            result = gateway.interact(
                                args[0], kind=args[1], text=" ".join(args[2:]),
                                command_id=cid, expected_revision=revision)
                    else:
                        print("Unknown command. Type help.")
                        continue
                    render(result)
                except (InvalidEvent, ValueError, DuplicateCommand,
                        RevisionConflict, SessionClosed, AdvanceLimitExceeded,
                        PermissionError) as exc:
                    print(f"Rejected: {exc}")
            clock.close_session(WORLD)
    print("Temporary world discarded; no story or production save was modified.")


if __name__ == "__main__":
    main()
