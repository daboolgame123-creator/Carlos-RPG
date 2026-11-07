"""PLAY-02 offline seven-NPC living village; a disposable playable test world.

From simulation/: PYTHONPATH=src python scenarios/test_village/play_living_village.py
Player chooses Carlos's actions; NPC intentions run ONLY on explicit wait.
The temporary SQLite database disappears on exit. No canonical story import.
"""
from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.player_handoff import player_handoff
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed
from living_player_fixture import (
    WORLD, living_player_gateway, setup_living_foraging_world,
    setup_living_npc_survival_world,
)

HELP = ("scene | look | status | remember | handoff | move <road> "
        "| wait <seconds> | offers | supplies | purchases | gifts | meals | needs | conversations | checkfood | forage (60s, complete with wait) | eat <food|bread> | askfood <npc> <site> | buy <offer> <qty> <price> | give <npc> <item> <qty> | talk <npc> <kind> <words> | quit")


def render(result) -> None:
    print(f"[t={result.time} rev={result.revision}] {result.status}")
    for key, value in result.details.items():
        print(f"  {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Disposable Carlos village test")
    parser.add_argument("--npc-survival-demo", action="store_true",
                        help="opt-in finite NPC-owned food and existing NPC hunger/eating AI")
    args = parser.parse_args()
    print("CARLOS — living disposable village (7 autonomous NPCs, non-canonical)")
    if args.npc_survival_demo:
        print("TEST ONLY: independent NPC hunger/food active; player hunger is NOT modeled.")
    print("NPCs act and travel only when you use wait; Carlos never moves himself.")
    print(HELP)
    with TemporaryDirectory(prefix="carlos-living-") as temp:
        with SQLiteEventStore(Path(temp) / "living.sqlite") as store:
            (setup_living_npc_survival_world if args.npc_survival_demo
             else setup_living_foraging_world)(store)
            clock = TimeEngine(store)
            clock.open_session(WORLD)
            gateway = living_player_gateway(
                store, clock, npc_survival_demo=args.npc_survival_demo)
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
                    elif verb == "gifts" and not args:
                        result = gateway.gifts()
                    elif verb == "meals" and not args:
                        result = gateway.meals()
                    elif verb == "needs" and not args:
                        result = gateway.needs()
                    elif verb == "conversations" and not args:
                        result = gateway.conversations()
                    elif verb == "checkfood" and not args:
                        result = gateway.check_food()
                    elif verb == "askfood" and len(args) == 2:
                        count += 1
                        result = gateway.ask_food(args[0], args[1],
                                                  command_id=f"living-{count}",
                                                  expected_revision=store.load(WORLD).revision)
                    elif verb in ("look", "move", "wait", "talk", "buy", "give", "forage", "eat"):
                        if (verb == "look" and args or
                            verb == "move" and len(args) != 1 or
                            verb == "wait" and len(args) != 1 or
                            verb == "talk" and len(args) < 3 or
                            verb == "buy" and len(args) != 3 or
                            verb == "give" and len(args) != 3 or
                            verb == "forage" and args or
                            verb == "eat" and len(args) != 1):
                            print("Invalid command arguments. Type help.")
                            continue
                        count += 1
                        cid = f"living-{count}"
                        revision = store.load(WORLD).revision
                        if verb == "forage":
                            result = gateway.forage(command_id=cid, expected_revision=revision)
                        elif verb == "eat":
                            result = gateway.eat(args[0], command_id=cid, expected_revision=revision)
                        elif verb == "look":
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
                        elif verb == "give":
                            result = gateway.give(args[0], args[1], int(args[2]),
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
