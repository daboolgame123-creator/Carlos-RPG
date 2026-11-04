"""Run a disposable two-person gathering demonstration (not Carlos canon)."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, NPCService,
                        NPCActionService, NPCGatheringService, NPCConsumptionService)


def event(kind, fields, actor=None):
    return DomainEvent(kind, actor, "synthetic finite-resource scenario", 0, fields)


def run() -> dict:
    with TemporaryDirectory() as root, SQLiteEventStore(Path(root) / "gather.sqlite") as db:
        db.create_world("grove-test")
        setup = [event("LocationCreated", {"id": "grove", "name": "Grove"}),
                 event("ResourceChanged", {"owner_id": "grove", "resource": "wild_food",
                                           "previous": None, "current": 2,
                                           "source": "initialization"})]
        for who in ("nora", "basim"):
            setup.extend([
                event("EntityCreated", {"id": who, "name": who,
                                        "location_id": "grove", "controller": "npc"}),
                event("NPCConfigured", {"npc_id": who, "role": "explorer",
                                        "needs": {"fatigue": 5, "hunger": 40, "safety": 0},
                                        "goals": {"earn": 0, "explore": 95, "survive": 30}}),
            ])
            for resource in ("food", "labor_units", "investigation_attempts"):
                setup.append(event("ResourceChanged", {"owner_id": who,
                                                      "resource": resource,
                                                      "previous": None, "current": 0,
                                                      "source": "initialization"}))
        db.append("grove-test", "setup", 0, setup, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("grove-test")
        planner, actions = NPCService(db, clock), NPCActionService(db, clock)
        for who in ("nora", "basim"):
            decision = planner.decide("grove-test", who, command_id="decide-" + who,
                                      expected_revision=db.load("grove-test").revision)
            assert decision.action == "investigate"
            actions.start("grove-test", who, "inspect-" + who,
                          expected_revision=db.load("grove-test").revision)
        current = db.load("grove-test")
        completed = clock.advance("grove-test", seconds=90, command_id="complete-searches",
                                   expected_revision=current.revision).state
        assert completed.resources["grove"]["wild_food"] == 2
        gatherer = NPCGatheringService(db, clock)
        for who in ("nora", "basim"):
            gatherer.collect("grove-test", who, "inspect-" + who,
                             command_id="gather-" + who,
                             expected_revision=db.load("grove-test").revision)
        recovered = db.load("grove-test")
        assert recovered.resources["grove"]["wild_food"] == 0
        assert recovered.resources["nora"]["food"] == 1
        assert recovered.resources["basim"]["food"] == 1
        eaten = NPCConsumptionService(db, clock).eat(
            "grove-test", "nora", 1, command_id="meal",
            expected_revision=recovered.revision).state
        assert db.verify("grove-test").to_dict() == eaten.to_dict()
        return {
            "simulated_seconds": eaten.time,
            "investigation_actions_completed": 2,
            "natural_stock_initial": 2,
            "natural_stock_remaining": eaten.resources["grove"]["wild_food"],
            "gathered_units": len(eaten.gatherings),
            "nora_owned_food_after_eating": eaten.resources["nora"]["food"],
            "basim_owned_food": eaten.resources["basim"]["food"],
            "nora_hunger_after_eating": eaten.npcs["nora"]["needs"]["hunger"],
            "event_replay_verified": True,
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
