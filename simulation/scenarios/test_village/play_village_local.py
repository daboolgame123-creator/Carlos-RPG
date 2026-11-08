"""PLAY-31: actual offline seven-NPC village that Carlos can navigate.

Quick start (from simulation/):
    PYTHONPATH=src python scenarios/test_village/play_village_local.py

The entire session is a disposable, private SQLite world. No internet, no
network authentication, no autosave, no canonical Carlos story import.
"""
from __future__ import annotations

import json
import shlex
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine, PlayerGateway
from carlos_sim.player_handoff import player_handoff
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed
from play_physical_supply import WORLD, PLAYER, seed_physical_supply

HELP = (
    "scene | look | remember | status | supplies | needs | offers | food | "
    "purchases | meals | gifts | conversations | handoff | "
    "move <route-id> | wait <1-21600 seconds> | "
    "talk <npc-id> <greeting|offer_help|request_help|threat> <words> | "
    "buy <offer-id> <quantity> <unit-price> | "
    "eat | give <npc-id> <resource> <quantity> | "
    "forage | askfood <npc-id> <site-id> | help | quit"
)
MAX_WAIT = 21600


def create_session(db: SQLiteEventStore, clock: TimeEngine) -> PlayerGateway:
    """One real, physically bounded 7-NPC village; player controls only Carlos."""
    seed_physical_supply(
        db, personal_food=2, harvest_yield=3,
        initial_market_food=2, playable_demo=True,
    )
    clock.open_session(WORLD)
    return PlayerGateway(
        db, clock, world_id=WORLD, player_id=PLAYER,
        engine=LivingWorldEngine(
            db, clock, max_events_per_advance=5000, decision_cooldown=3600,
            navigation_enabled=True, routines_enabled=True,
            survival_enabled=True, consumption_enabled=True,
            supply_enabled=True, economic_enabled=True,
            agriculture_enabled=True, economy_only_enabled=False,
        ),
    )


def execute(gateway: PlayerGateway, line: str, serial: int):
    """Return a player-scoped gateway projection; never reveal WorldState."""
    words = shlex.split(line)
    if not words:
        return None
    verb, *args = words
    readonly = {
        "scene": gateway.inspect, "remember": gateway.recall,
        "status": gateway.status, "supplies": gateway.supplies,
        "needs": gateway.needs, "offers": gateway.offers,
        "food": gateway.check_food, "purchases": gateway.purchases,
        "meals": gateway.meals, "gifts": gateway.gifts,
        "conversations": gateway.conversations,
    }
    if verb in readonly and not args:
        return readonly[verb]()
    if verb == "handoff" and not args:
        return player_handoff(gateway)
    if verb == "help" and not args:
        return HELP
    if verb in ("quit", "exit") and not args:
        return "quit"

    # Every actual command is a fresh, explicitly player-originated action.
    kwargs = {
        "command_id": f"village-{serial}",
        "expected_revision": gateway.store.load(WORLD).revision,
    }
    if verb == "look" and not args:
        return gateway.observe(**kwargs)
    if verb == "move" and len(args) == 1:
        return gateway.move(args[0], **kwargs)
    if verb == "wait" and len(args) == 1:
        seconds = int(args[0])
        if not 1 <= seconds <= MAX_WAIT:
            raise ValueError("wait must be from 1 to 21600 seconds")
        return gateway.wait(seconds, **kwargs)
    if verb == "talk" and len(args) >= 3:
        return gateway.interact(args[0], kind=args[1], text=" ".join(args[2:]), **kwargs)
    if verb == "buy" and len(args) == 3:
        return gateway.buy(args[0], int(args[1]), int(args[2]), **kwargs)
    if verb == "eat" and not args:
        return gateway.eat("food", **kwargs)
    if verb == "give" and len(args) == 3:
        return gateway.give(args[0], args[1], int(args[2]), **kwargs)
    if verb == "forage" and not args:
        return gateway.forage(**kwargs)
    if verb == "askfood" and len(args) == 2:
        return gateway.ask_food(args[0], args[1], **kwargs)
    raise ValueError("unknown command or arguments; type help")


def render(message):
    if message is None:
        return
    if isinstance(message, str):
        print(message)
    elif isinstance(message, dict):
        print(json.dumps(message, ensure_ascii=False, sort_keys=True))
    else:
        print(f"[t={message.time} rev={message.revision}] {message.status}")
        for name, detail in message.details.items():
            print(f"  {name}: {detail}")


def main():
    print("CARLOS / PLAY-31 — 7 autonomous NPCs, 5 places, real roads and finite resources")
    print("Offline disposable world: all events discarded on exit; NOT the canonical story.")
    print("Try: scene | move home-market | wait 90 | scene | offers | talk salma greeting Hello")
    print(HELP)
    with TemporaryDirectory(prefix="carlos-play31-") as folder:
        with SQLiteEventStore(Path(folder) / "demo.sqlite") as db:
            clock = TimeEngine(db)
            gateway = create_session(db, clock)
            serial = 0
            try:
                render(gateway.inspect())
                while True:
                    try:
                        line = input("carlos> ")
                    except (EOFError, KeyboardInterrupt):
                        break
                    if line.strip() in ("quit", "exit"):
                        break
                    try:
                        serial += 1
                        render(execute(gateway, line, serial))
                    except (ValueError, InvalidEvent, RevisionConflict,
                            DuplicateCommand, AdvanceLimitExceeded,
                            SessionClosed, PermissionError) as error:
                        print(f"Rejected: {error}")
            finally:
                clock.close_session(WORLD)
    print("Session ended. Temporary world destroyed; the story was never modified.")


if __name__ == "__main__":
    main()
