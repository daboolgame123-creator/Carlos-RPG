"""Phase 01-V: verify all previous food, navigation and assistance flags.

Run the SAME script under frozen genuine 01-U and current 01-V runtimes.
The 01-V scarcity flag is absent/default-off: full event/state digests MUST
match even while food-navigation, knowledge and assistance are enabled.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from carlos_sim import (
    DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine, canonical_hash
)


def ev(kind, data, actor=None, time=0):
    return DomainEvent(kind, actor, "frozen phase parity", time, data)


def main():
    with tempfile.TemporaryDirectory() as root:
        with SQLiteEventStore(Path(root) / "parity.sqlite") as db:
            db.create_world("village")
            events = [
                ev("LocationCreated", {"id": "market", "name": "Market"}),
                ev("LocationCreated", {"id": "grove", "name": "Grove"}),
                ev("RouteCreated", {
                    "id": "market-grove", "a": "market", "b": "grove",
                    "seconds": 50,
                }),
                ev("ResourceChanged", {
                    "owner_id": "market", "resource": "wild_food",
                    "previous": None, "current": 0,
                    "source": "initialization",
                }),
                ev("ResourceChanged", {
                    "owner_id": "grove", "resource": "wild_food",
                    "previous": None, "current": 2,
                    "source": "initialization",
                }),
            ]
            for who, hunger in (("adel", 85), ("basim", 20), ("nora", 20)):
                events.extend([
                    ev("EntityCreated", {
                        "id": who, "name": who,
                        "location_id": "market", "controller": "npc",
                    }),
                    ev("NPCConfigured", {
                        "npc_id": who, "role": "explorer",
                        "needs": {"fatigue": 5, "hunger": hunger, "safety": 0},
                        "goals": {"earn": 0, "explore": 0, "survive": 30},
                    }),
                ])
                for resource in ("food", "labor_units", "investigation_attempts"):
                    events.append(ev("ResourceChanged", {
                        "owner_id": who, "resource": resource,
                        "previous": None, "current": 0,
                        "source": "initialization",
                    }))
            db.append("village", "bootstrap", 0, events, bootstrap=True)
            clock = TimeEngine(db)
            clock.open_session("village")
            state = db.load("village")
            db.append("village", "tell-adel", state.revision, [
                ev("NPCInformationDelivered", {
                    "npc_id": "adel", "delivery_id": "remote-rumor",
                    "key": "food:grove",
                    "claim": {
                        "text": "food-state:present; observed_at=0",
                        "source": "basim", "received_at": 0, "confidence": 60,
                    },
                    "sender_id": "basim", "location_id": "market",
                    "method": "message",
                }, actor="basim"),
                ev("NPCBeliefReceived", {
                    "npc_id": "adel", "key": "food:grove",
                    "delivery_id": "remote-rumor",
                }, actor="adel"),
            ], npc_authorized=True)
            outcome = LivingWorldEngine(
                db, clock, navigation_enabled=True, knowledge_enabled=True,
                foraging_enabled=True, food_navigation_enabled=True,
                assistance_enabled=True,
            ).advance("village", seconds=65, command_id="advance",
                      expected_revision=db.load("village").revision)
            snapshot = outcome.state.to_dict()
            assert db.verify("village").to_dict() == snapshot
            event_log = [
                json.loads(raw) for (raw,) in db.db.execute(
                    "SELECT payload FROM events WHERE world_id='village' "
                    "ORDER BY seq"
                )
            ]
            return {
                "npcs": len(outcome.state.npcs),
                "time": outcome.state.time,
                "revision": outcome.state.revision,
                "events_count": len(event_log),
                "events_digest": canonical_hash(event_log),
                # Full digest continues to include Rules version. The next
                # digest excludes versions and new empty opt-in RPG collection to compare behavior
                # across the explicit 18-to-19 rules boundary.
                "rules_version": snapshot["rules_version"],
                "state_digest": canonical_hash(snapshot),
                "state_semantic_digest": canonical_hash({
                    k: v for k, v in snapshot.items() if k not in ("schema_version", "rules_version", "rpg_profiles", "environment_cycles", "production_recipes", "production_jobs", "market_stalls", "market_offers", "market_trades", "loan_contracts", "loan_repayments", "npc_temperaments", "npc_routines", "rumor_deliveries", "property_takings", "property_sightings", "property_claims", "complaint_desks", "property_complaints", "property_title_origins", "property_custody_lots", "property_custody_moves")
                }),
                "replay_equal": True,
            }


if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
