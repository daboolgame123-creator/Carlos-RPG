"""Phase 02-B: seven NPCs in a disposable bakery; no economy minting."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCProductionService

WORKERS = ("basim", "nora", "salma", "adel", "huda", "omar", "layla")


def ev(kind, data):
    return DomainEvent(kind, None, "02-B non-canon training village", 0, data)


def run() -> dict:
    with TemporaryDirectory() as root, SQLiteEventStore(Path(root) / "bakery.sqlite") as db:
        db.create_world("village")
        setup = [ev("LocationCreated", {"id": "bakery", "name": "Bakery"})]
        for resource, amount in (("grain", 4), ("oven", 2), ("bread", 0)):
            setup.append(ev("ResourceChanged", {
                "owner_id": "bakery", "resource": resource,
                "previous": None, "current": amount, "source": "initialization",
            }))
        for person in WORKERS:
            setup.extend([
                ev("EntityCreated", {
                    "id": person, "name": person, "location_id": "bakery",
                    "controller": "npc",
                }),
                ev("NPCConfigured", {
                    "npc_id": person,
                    "role": "baker" if person in ("basim", "nora") else "resident",
                    "needs": {"hunger": 20, "fatigue": 5, "safety": 0},
                    "goals": {"earn": 50, "explore": 10, "survive": 30},
                }),
            ])
        setup.append(ev("ProductionRecipeConfigured", {
            "id": "bread", "site_id": "bakery", "role": "baker",
            "input_resource": "grain", "input_amount": 2,
            "output_resource": "bread", "output_amount": 1,
            "tool_resource": "oven", "duration_seconds": 90,
        }))
        db.append("village", "bootstrap", 0, setup, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("village")
        prod = NPCProductionService(db, clock)
        for worker in ("basim", "nora"):
            prod.start("village", worker, "bread", "batch-" + worker,
                       expected_revision=db.load("village").revision)
        initial = db.load("village")
        assert initial.resources["bakery"] == {"grain": 0, "oven": 2, "bread": 0}
        completed = clock.advance(
            "village", seconds=90, command_id="two-bread-ready",
            expected_revision=initial.revision,
        ).state
        assert completed.resources["bakery"] == {
            "grain": 0, "oven": 2, "bread": 2,
        }
        assert len(completed.npcs) == 7
        assert all(job["status"] == "completed" for job in completed.production_jobs.values())
        assert db.verify("village").to_dict() == completed.to_dict()
        return {
            "npc_count": len(completed.npcs),
            "bakers": ["basim", "nora"],
            "work_seconds": completed.time,
            "grain_before": 4, "grain_after": 0,
            "ovens_before": 2, "ovens_after": 2,
            "bread_before": 0, "bread_after": 2,
            "production_jobs_completed": 2,
            "event_replay_verified": True,
            "note": "No free inputs, workers must be present and properly equipped site with finite materials.",
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
