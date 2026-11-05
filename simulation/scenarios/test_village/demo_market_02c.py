"""02-C disposable 7-NPC market: baked bread -> buyers for actual copper.

Site-owned bread sells from the site ledger, site receives copper.
Steward does not become bread owner merely by representing a workshop.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine,
    NPCProductionService, NPCMarketService,
)

PEOPLE = ("basim", "nora", "adel", "salma", "huda", "omar", "layla")


def E(kind, payload):
    return DomainEvent(kind, None, "disposable 02-C village", 0, payload)


def run() -> dict:
    with TemporaryDirectory() as root, SQLiteEventStore(Path(root) / "market.sqlite") as db:
        db.create_world("market")
        events = [E("LocationCreated", {"id": "bakery", "name": "Bakery"})]
        for item, qty in (("grain", 4), ("oven", 2), ("bread", 0), ("coin_copper", 0)):
            events.append(E("ResourceChanged", {
                "owner_id": "bakery", "resource": item, "previous": None,
                "current": qty, "source": "initialization",
            }))
        for npc in PEOPLE:
            events.extend([
                E("EntityCreated", {
                    "id": npc, "name": npc, "location_id": "bakery",
                    "controller": "npc",
                }),
                E("NPCConfigured", {
                    "npc_id": npc,
                    "role": "baker" if npc in ("basim", "nora") else "steward" if npc == "adel" else "resident",
                    "needs": {"fatigue": 5, "hunger": 20, "safety": 0},
                    "goals": {"earn": 50, "explore": 10, "survive": 30},
                }),
            ])
            for item, qty in (
                ("bread", 0),
                ("coin_copper", 10 if npc in ("salma", "huda") else 0),
            ):
                events.append(E("ResourceChanged", {
                    "owner_id": npc, "resource": item, "previous": None,
                    "current": qty, "source": "initialization",
                }))
        events.extend([
            E("ProductionRecipeConfigured", {
                "id": "bread", "site_id": "bakery", "role": "baker",
                "input_resource": "grain", "input_amount": 2,
                "output_resource": "bread", "output_amount": 1,
                "tool_resource": "oven", "duration_seconds": 90,
            }),
            E("MarketStallConfigured", {
                "site_id": "bakery", "keeper_id": "adel",
            }),
        ])
        db.append("market", "genesis", 0, events, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("market")
        bakery = NPCProductionService(db, clock)
        for npc in ("basim", "nora"):
            bakery.start("market", npc, "bread", f"job-{npc}",
                         expected_revision=db.load("market").revision)
        before = db.load("market")
        assert before.resources["bakery"]["bread"] == 0
        baked = clock.advance(
            "market", seconds=90, command_id="bake-real-bread",
            expected_revision=before.revision,
        ).state
        assert baked.resources["bakery"]["bread"] == 2
        market = NPCMarketService(db, clock)
        market.post(
            "market", "adel", "bakery", "bakery", "offer",
            "bread", 2, "coin_copper", 3,
            expected_revision=db.load("market").revision,
        )
        quote = market.local_quotes("market", "salma")
        assert quote and quote[0]["unit_price"] == 3
        for buyer in ("salma", "huda"):
            market.buy(
                "market", buyer, f"sale-{buyer}", "offer", 1, 3,
                expected_revision=db.load("market").revision,
            )
        end = db.verify("market")
        assert end.resources["bakery"] == {
            "grain": 0, "oven": 2, "bread": 0, "coin_copper": 6,
        }
        assert all(end.resources[buyer]["bread"] == 1 for buyer in ("salma", "huda"))
        assert all(end.resources[buyer]["coin_copper"] == 7 for buyer in ("salma", "huda"))
        assert end.resources["adel"]["coin_copper"] == 0
        assert end.market_offers["offer"]["status"] == "filled"
        assert len(end.market_trades) == 2
        return {
            "npc_count": 7,
            "bakers": 2,
            "simulated_work_seconds": 90,
            "grain_start": 4,
            "grain_end": 0,
            "bread_created_by_bakers": 2,
            "bread_remaining_at_bakery": 0,
            "buyers_loaves": {"salma": 1, "huda": 1},
            "buyers_copper_left": {"salma": 7, "huda": 7},
            "bakery_copper_received": 6,
            "steward_personal_copper_received": 0,
            "verified_events": end.revision,
            "replay_verified": True,
            "price_source": "on-site NPC steward's explicit quoted ask, 3 copper/loaf",
        }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
