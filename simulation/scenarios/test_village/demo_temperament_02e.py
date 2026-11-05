"""Seven NPCs, two distinct dispositions and memories of actual action."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCService,
    NPCActionService, choose_action,
)

NAMES = ("basim", "nora", "salma", "adel", "huda", "omar", "layla")
WORKER = {"ambition": 100, "curiosity": 0, "caution": 100, "discipline": 100}
EXPLORER = {"ambition": 0, "curiosity": 100, "caution": 0, "discipline": 0}


def E(k, d):
    return DomainEvent(k, None, "02-E disposable personality trial", 0, d)


def run() -> dict:
    with TemporaryDirectory() as d, SQLiteEventStore(Path(d) / "village.sqlite") as db:
        db.create_world("world")
        events = [E("LocationCreated", {"id": "square", "name": "Square"})]
        for who in NAMES:
            events.extend([
                E("EntityCreated", {"id": who, "name": who,
                                    "location_id": "square", "controller": "npc"}),
                E("NPCConfigured", {"npc_id": who, "role": "resident",
                                    "needs": {"fatigue": 10, "hunger": 5, "safety": 0},
                                    "goals": {"earn": 40, "explore": 45, "survive": 30}}),
            ])
            for k in ("labor_units", "investigation_attempts"):
                events.append(E("ResourceChanged", {
                    "owner_id": who, "resource": k, "previous": None,
                    "current": 0, "source": "initialization",
                }))
        for npc_id, traits in (("basim", WORKER), ("nora", EXPLORER)):
            events.append(E("NPCTemperamentConfigured", {
                "npc_id": npc_id, "traits": traits,
            }))
        db.append("world", "setup", 0, events, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("world")
        state = db.load("world")
        a, b = choose_action(state, "basim"), choose_action(state, "nora")
        assert a.action == "work"
        assert b.action == "investigate"
        assert state.npcs["basim"]["needs"] == state.npcs["nora"]["needs"]
        for who in ("basim", "nora"):
            NPCService(db, clock).decide(
                "world", who, command_id="choose-" + who,
                expected_revision=db.load("world").revision)
            NPCActionService(db, clock).start(
                "world", who, "real-" + who,
                expected_revision=db.load("world").revision)
        before = db.load("world")
        assert not before.npc_temperaments["basim"]["memories"]
        assert not before.npc_temperaments["nora"]["memories"]
        after = clock.advance(
            "world", seconds=180, command_id="live-180",
            expected_revision=before.revision,
        ).state
        assert len(after.npc_temperaments["basim"]["memories"]) == 1
        assert len(after.npc_temperaments["nora"]["memories"]) == 1
        assert after.resources["basim"]["labor_units"] == 1
        assert after.resources["nora"]["investigation_attempts"] == 1
        assert db.verify("world").to_dict() == after.to_dict()
        return {
            "npc_count": len(after.npcs),
            "basim_action": a.action, "nora_action": b.action,
            "same_initial_goals_and_needs": True,
            "basim_reason": a.reason, "nora_reason": b.reason,
            "work_counter": after.resources["basim"]["labor_units"],
            "exploration_counter": after.resources["nora"]["investigation_attempts"],
            "memory_count": sum(len(p["memories"]) for p in after.npc_temperaments.values()),
            "unconfigured_npcs": 5,
            "replay_verified": True,
        }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
