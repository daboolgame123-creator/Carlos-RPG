"""Seven-person hunger-driven foraging demo; disposable test world only."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine

PROFILES = (
    # name, site, hunger, initial owned food
    ("adel", "grove", 70, 0),
    ("basim", "grove", 70, 0),
    ("huda", "grove", 30, 0),
    ("layla", "grove", 70, 2),
    ("nora", "grove", 70, 0),
    ("omar", "square", 70, 0),
    ("salma", "grove", 70, 0),
)


def event(kind, data, actor=None):
    return DomainEvent(kind, actor, "synthetic 7-NPC gathering demo", 0, data)


def run() -> dict:
    with TemporaryDirectory() as tmp, SQLiteEventStore(Path(tmp) / "test.sqlite") as db:
        db.create_world("village")
        setup = [
            event("LocationCreated", {"id": "grove", "name": "Grove"}),
            event("LocationCreated", {"id": "square", "name": "Square"}),
            event("ResourceChanged", {"owner_id": "grove", "resource": "wild_food",
                                       "previous": None, "current": 2, "source": "initialization"}),
            event("ResourceChanged", {"owner_id": "square", "resource": "wild_food",
                                       "previous": None, "current": 0, "source": "initialization"}),
        ]
        for name, site, hunger, food in PROFILES:
            setup.extend([
                event("EntityCreated", {"id": name, "name": name,
                                        "location_id": site, "controller": "npc"}),
                event("NPCConfigured", {"npc_id": name, "role": "explorer",
                                        "needs": {"fatigue": 5, "hunger": hunger, "safety": 0},
                                        "goals": {"earn": 0, "explore": 95, "survive": 30}}),
            ])
            for resource, stock in (("food", food), ("labor_units", 0),
                                    ("investigation_attempts", 0)):
                setup.append(event("ResourceChanged", {
                    "owner_id": name, "resource": resource,
                    "previous": None, "current": stock,
                    "source": "initialization",
                }))
        db.append("village", "bootstrap", 0, setup, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("village")
        outcome = LivingWorldEngine(db, clock, foraging_enabled=True).advance(
            "village", seconds=120, command_id="120-second-foraging",
            expected_revision=db.load("village").revision)
        state = outcome.state
        assert db.verify("village").to_dict() == state.to_dict()
        assert len(state.npcs) == 7
        assert len(state.foraging_attempts) == 4
        assert state.resources["grove"]["wild_food"] == 0
        assert sum(r["quantity"] for r in state.foraging_attempts.values()) == 2
        assert sum(r["outcome"] == "depleted" for r in state.foraging_attempts.values()) == 2
        assert state.gatherings == {}
        return {
            "npcs": len(state.npcs),
            "simulated_seconds": state.time,
            "advance_event_count": outcome.event_count,
            "wild_food_initial": 2,
            "wild_food_remaining": state.resources["grove"]["wild_food"],
            "foraging_attempts": {k: dict(v) for k,v in state.foraging_attempts.items()},
            "foraging_successes": sum(r["quantity"] for r in state.foraging_attempts.values()),
            "foraging_failures": sum(r["outcome"] == "depleted" for r in state.foraging_attempts.values()),
            "food_inventory": {name: state.resources[name]["food"] for name, *_ in PROFILES},
            "replay_verified": True,
            "note": "NPCs chose a 120-second forage action because of local, visible food and personal hunger; failure due to competition is recorded.",
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
