"""01-Y disposable offline play demo; NEVER imports real Carlos story data.

From simulation/:
    PYTHONPATH=src python scenarios/test_village/play_local.py

This script creates a temporary SQLite world and deletes it on exit.
Long-lived saves are forbidden while P0 backup/restore is open.
"""
from __future__ import annotations

import shlex
import json

from carlos_sim.player_handoff import player_handoff
from tempfile import TemporaryDirectory
from pathlib import Path

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, PlayerGateway
from carlos_sim.rpg_state import unknown_profile
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded


def event(kind, data):
    return DomainEvent(kind, None, "temporary local game fixture", 0, data)


def setup(db):
    db.create_world("demo")
    events = [
        event("LocationCreated", {"id": "square", "name": "Town Square"}),
        event("LocationCreated", {"id": "woods", "name": "Woods"}),
        event("LocationCreated", {"id": "camp", "name": "Camp"}),
        event("RouteCreated", {
            "id": "square-woods", "a": "square", "b": "woods", "seconds": 50,
        }),
        event("RouteCreated", {
            "id": "woods-camp", "a": "woods", "b": "camp", "seconds": 30,
        }),
        event("EntityCreated", {
            "id": "carlos", "name": "Carlos", "controller": "player",
            "location_id": "square",
        }),
    ]
    # Non-canon disposable fixture; never import Carlos story statistics.
    sample = unknown_profile()
    sample["vitals"]["hp"] = {"current": 12, "max": 12}
    sample["vitals"]["st"] = {"current": 8, "max": 8}
    events.append(event("PlayerRPGInitialized", {
        "player_id": "carlos", "profile": sample,
    }))
    for npc, place in (("basim", "square"), ("nora", "woods")):
        events.extend([
            event("EntityCreated", {
                "id": npc, "name": npc, "controller": "npc",
                "location_id": place,
            }),
            event("NPCConfigured", {
                "npc_id": npc, "role": "resident",
                "needs": {"fatigue": 5, "hunger": 20, "safety": 0},
                "goals": {"earn": 15, "explore": 0, "survive": 15},
            }),
        ])
        for counter in ("labor_units", "investigation_attempts"):
            events.append(event("ResourceChanged", {
                "owner_id": npc, "resource": counter,
                "previous": None, "current": 0, "source": "initialization",
            }))
    db.append("demo", "bootstrap", 0, events, bootstrap=True)


def render(result):
    print(f"[t={result.time} rev={result.revision}] {result.status}")
    for key, val in result.details.items():
        print(f"  {key}: {val}")


def main():
    print("CARLOS / 01-Y local disposable world — fictional sample HP/ST; no permanent save")
    print("Commands: scene | look | remember | status | handoff | move <route-id> | wait <seconds> | talk <npc> <kind> <words> | quit")
    print("Talk kinds: greeting, offer_help, request_help, threat")
    with TemporaryDirectory(prefix="carlos-01w-") as folder:
        with SQLiteEventStore(Path(folder) / "world.sqlite") as db:
            setup(db)
            clock = TimeEngine(db)
            clock.open_session("demo")
            gateway = PlayerGateway(
                db, clock, world_id="demo", player_id="carlos")
            counter = 0
            render(gateway.inspect())
            while True:
                try:
                    raw = input("carlos> ")
                except EOFError:
                    break
                try:
                    words = shlex.split(raw)
                except ValueError as exc:
                    print(f"Invalid command: {exc}")
                    continue
                if not words:
                    continue
                verb, *args = words
                if verb in ("quit", "exit"):
                    break
                if verb == "help":
                    print("scene | look | remember | status | handoff | move <route-id> | wait <seconds> | talk <npc> <kind> <words> | quit")
                    continue
                try:
                    if verb == "scene" and not args:
                        result = gateway.inspect()
                    elif verb == "handoff" and not args:
                        print(json.dumps(player_handoff(gateway),
                                         ensure_ascii=False, sort_keys=True))
                        continue
                    elif verb == "look" and not args:
                        counter += 1
                        result = gateway.observe(
                            command_id=f"cmd-{counter}",
                            expected_revision=db.load("demo").revision)
                    elif verb == "remember" and not args:
                        result = gateway.recall()
                    elif verb == "status" and not args:
                        result = gateway.status()
                    elif verb == "move" and len(args) == 1:
                        counter += 1
                        result = gateway.move(
                            args[0], command_id=f"cmd-{counter}",
                            expected_revision=db.load("demo").revision)
                    elif verb == "wait" and len(args) == 1:
                        counter += 1
                        seconds = int(args[0])
                        result = gateway.wait(
                            seconds, command_id=f"cmd-{counter}",
                            expected_revision=db.load("demo").revision)
                    elif verb == "talk" and len(args) >= 3:
                        counter += 1
                        result = gateway.interact(
                            args[0], kind=args[1],
                            text=" ".join(args[2:]),
                            command_id=f"cmd-{counter}",
                            expected_revision=db.load("demo").revision)
                    else:
                        print("Unknown command. Type help.")
                        continue
                    render(result)
                except (InvalidEvent, ValueError, RevisionConflict,
                        DuplicateCommand, SessionClosed, AdvanceLimitExceeded,
                        PermissionError) as exc:
                    print(f"Rejected: {exc}")
            clock.close_session("demo")
    print("Session ended; disposable world discarded.")


if __name__ == "__main__":
    main()
