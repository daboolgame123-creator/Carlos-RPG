"""OpenCode review T-1/T-2: bounded knowledge exchange and hostile history IDs."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCMovementService, SQLiteEventStore,
    TimeEngine,
)
from carlos_sim.knowledge import choose_food_sharing_round


def ev(kind, data, actor=None):
    return DomainEvent(kind, actor, "01-T independent review regressions", 0, data)


def setup_community(db, count=25):
    """Disposable 25-NPC village with one initialized, physical food site."""
    db.create_world("scale")
    events = [
        ev("LocationCreated", {"id": "grove", "name": "Grove"}),
        ev("ResourceChanged", {
            "owner_id": "grove", "resource": "wild_food",
            "previous": None, "current": 1, "source": "initialization",
        }),
    ]
    for n in range(count):
        who = f"npc{n:02d}"
        events.extend([
            ev("EntityCreated", {
                "id": who, "name": who,
                "controller": "npc", "location_id": "grove",
            }),
            ev("NPCConfigured", {
                "npc_id": who, "role": "resident",
                "needs": {"hunger": 20, "fatigue": 5, "safety": 0},
                "goals": {"earn": 0, "explore": 0, "survive": 10},
            }),
        ])
        for resource in ("food", "labor_units", "investigation_attempts"):
            events.append(ev("ResourceChanged", {
                "owner_id": who, "resource": resource,
                "previous": None, "current": 0,
                "source": "initialization",
            }))
    db.append("scale", "bootstrap", 0, events, bootstrap=True)


def observe(db, clock, who):
    NPCMovementService(db, clock).observe(
        "scale", who, command_id="see-" + who,
        expected_revision=db.load("scale").revision, knowledge_enabled=True,
    )


@pytest.mark.parametrize("initial_observers", [1, 25])
def test_25_co_located_npcs_no_quadratic_gossip_or_budget_deadlock(
        tmp_path, initial_observers):
    with SQLiteEventStore(tmp_path / "25-npc.sqlite") as db:
        setup_community(db)
        clock = TimeEngine(db)
        clock.open_session("scale")
        for n in range(initial_observers):
            observe(db, clock, f"npc{n:02d}")
        before = db.load("scale")
        proposal = choose_food_sharing_round(before)
        delivered = [e for e in proposal if e.event_type == "NPCInformationDelivered"]
        # O(N) for this one site, not 25*24=600 deliveries.
        assert len(delivered) == 24 if initial_observers == 1 else 25
        assert len(delivered) == len({
            (e.data["npc_id"], e.data["key"]) for e in delivered
        })
        assert len(proposal) == len(delivered) * 2
        if initial_observers == 1:
            # No person can immediately relay something learned in this pass.
            assert {e.actor_id for e in delivered} == {"npc00"}
        outcome = LivingWorldEngine(
            db, clock, knowledge_enabled=True
        ).advance("scale", seconds=1, command_id="progress-25",
                  expected_revision=before.revision)
        assert outcome.event_count < 1000
        assert len(outcome.knowledge_shares) == len(delivered)
        assert len(outcome.knowledge_shares) == len(set(outcome.knowledge_shares))
        assert db.verify("scale").to_dict() == outcome.state.to_dict()


def test_no_relay_of_newly_received_hearsay_on_same_tick(tmp_path):
    with SQLiteEventStore(tmp_path / "no-instant-relay.sqlite") as db:
        setup_community(db, count=3)
        clock = TimeEngine(db)
        clock.open_session("scale")
        observe(db, clock, "npc00")
        state = db.load("scale")
        db.append("scale", "tell-npc01", state.revision, [
            ev("NPCInformationDelivered", {
                "npc_id": "npc01", "delivery_id": "manual-npc00-to-npc01",
                "key": "food:grove",
                "claim": {
                    "text": "food-state:present; observed_at=0",
                    "source": "npc00", "received_at": 0, "confidence": 45,
                },
                "sender_id": "npc00", "location_id": "grove",
                "method": "message",
            }, actor="npc00"),
            ev("NPCBeliefReceived", {
                "npc_id": "npc01", "key": "food:grove",
                "delivery_id": "manual-npc00-to-npc01",
            }, actor="npc01"),
        ], npc_authorized=True)
        planned = choose_food_sharing_round(db.load("scale"))
        senders = {e.actor_id for e in planned
                   if e.event_type == "NPCInformationDelivered"}
        assert senders == {"npc00"}
        clock.advance("scale", seconds=1, command_id="next-tick",
                      expected_revision=db.load("scale").revision)
        planned_next = choose_food_sharing_round(db.load("scale"))
        assert any(e.actor_id == "npc01" for e in planned_next
                   if e.event_type == "NPCInformationDelivered")


def test_forged_5000_digit_history_suffix_does_not_lock_world(tmp_path):
    with SQLiteEventStore(tmp_path / "hostile-id.sqlite") as db:
        setup_community(db, count=2)
        clock = TimeEngine(db)
        clock.open_session("scale")
        observe(db, clock, "npc00")
        history_id = "food-share:npc00:npc01:grove:" + "9" * 5000
        state = db.load("scale")
        # The historical reducer boundary accepts this unusual delivery ID.
        # The sharing policy must bound its numeric parser regardless.
        db.append("scale", "inject-weird-history", state.revision, [
            ev("NPCInformationDelivered", {
                "npc_id": "npc01", "delivery_id": history_id,
                "key": "food:grove",
                "claim": {
                    "text": "food-state:present; observed_at=0",
                    "source": "npc00", "received_at": 0, "confidence": 45,
                },
                "sender_id": "npc00", "location_id": "grove",
                "method": "message",
            }, actor="npc00"),
            ev("NPCBeliefReceived", {
                "npc_id": "npc01", "key": "food:grove",
                "delivery_id": history_id,
            }, actor="npc01"),
        ], npc_authorized=True)
        before = db.load("scale")
        event_pairs = choose_food_sharing_round(before)
        assert any(e.data["delivery_id"] == "food-share:npc00:npc01:grove:0"
                   for e in event_pairs
                   if e.event_type == "NPCInformationDelivered")
        result = LivingWorldEngine(
            db, clock, knowledge_enabled=True
        ).advance("scale", seconds=1, command_id="survive-huge-id",
                  expected_revision=before.revision)
        assert result.state.time == 1
        assert db.verify("scale").to_dict() == result.state.to_dict()
