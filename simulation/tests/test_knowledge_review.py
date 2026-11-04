"""Independent 01-T probes for verified knowledge boundaries and emission paths."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine
from carlos_sim.knowledge import choose_food_sharing
from carlos_sim.movement import NPCMovementService
from carlos_sim.store import InvalidEvent
from test_gathering_autonomy import make_world


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / "review.sqlite") as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session("r")
        yield db, clock


def claim(status="present", observed_at=0, source="observation:grove", received_at=0, confidence=90):
    return {"text": f"food-state:{status}; observed_at={observed_at}",
            "source": source, "received_at": received_at,
            "confidence": confidence}


def deliver(db, *, sender, recipient, site, status, observed_at, method, delivery_id):
    state = db.load("r")
    return db.append("r", "probe:" + delivery_id, state.revision, [
        DomainEvent("NPCInformationDelivered", sender, "review probe", state.time,
                    {"npc_id": recipient, "delivery_id": delivery_id,
                     "key": "food:" + site,
                     "claim": claim(status, observed_at,
                                    ("observation:" + site) if method == "observation" else sender,
                                    state.time, 90 if method == "observation" else 60),
                     "sender_id": sender, "location_id": "grove", "method": method}),
    ], npc_authorized=True)


def test_direct_observation_cannot_claim_past_time_using_current_stock(world):
    db, clock = world
    clock.advance("r", seconds=100, command_id="tick100",
                  expected_revision=db.load("r").revision)
    original = db.load("r").to_dict()
    count = db.db.execute("SELECT count(*) FROM events WHERE world_id='r'").fetchone()[0]
    with pytest.raises(InvalidEvent, match="direct observation must be made"):
        deliver(db, sender="adel", recipient="adel", site="grove",
                status="present", observed_at=0, method="observation",
                delivery_id="past-observation")
    assert db.load("r").to_dict() == original
    assert db.db.execute("SELECT count(*) FROM events WHERE world_id='r'").fetchone()[0] == count


def test_hearsay_cannot_reference_nonexistent_food_site(world):
    db, clock = world
    original = db.load("r").to_dict()
    with pytest.raises(InvalidEvent, match="existing site"):
        deliver(db, sender="basim", recipient="adel", site="imaginary",
                status="present", observed_at=0, method="message",
                delivery_id="invented-site")
    assert db.load("r").to_dict() == original


def share_state(*, time=100, status="present", history=None, two_sites=False):
    beliefs = {"food:grove": claim(status, 0)}
    if two_sites:
        beliefs["food:square"] = claim("present", 0, "basim", 0, 60)
    return {"entities": {"adel": {"location_id": "grove"},
                          "basim": {"location_id": "grove"}},
            "npcs": {"adel": {"beliefs": beliefs, "delivery_history": []},
                     "basim": {"beliefs": {}, "delivery_history": list(history or [])}},
            "time": time, "travels": {}, "actions": {}}


def test_empty_food_memory_is_shared_as_a_belief():
    events = choose_food_sharing(share_state(status="empty"), "adel")
    assert len(events) == 2
    assert events[0].data["claim"]["text"] == "food-state:empty; observed_at=0"


def test_cooldown_is_based_on_recipient_history_and_exact_site():
    history = ["food-share:adel:basim:grove:100"]
    assert choose_food_sharing(share_state(time=150, history=history), "adel") == []
    events = choose_food_sharing(share_state(time=700, history=history), "adel")
    assert len(events) == 2
    assert events[0].data["delivery_id"] == "food-share:adel:basim:grove:700"


def test_at_most_one_food_delivery_per_sender_recipient_pair_per_tick():
    events = choose_food_sharing(share_state(two_sites=True), "adel")
    assert len(events) == 2
    assert events[0].event_type == "NPCInformationDelivered"
    assert events[1].event_type == "NPCBeliefReceived"


def test_real_living_world_shares_before_npcs_become_busy(world):
    db, clock = world
    s = db.load("r")
    db.append("r", "direct0", s.revision, [
        DomainEvent("NPCInformationDelivered", "adel", "observe", 0,
                    {"npc_id": "adel", "delivery_id": "obs-review", "key": "food:grove",
                     "claim": claim(), "sender_id": "adel",
                     "location_id": "grove", "method": "observation"}),
        DomainEvent("NPCBeliefReceived", "adel", "ack", 0,
                    {"npc_id": "adel", "delivery_id": "obs-review",
                     "key": "food:grove"}),
    ], npc_authorized=True)
    result = LivingWorldEngine(db, clock, knowledge_enabled=True,
                               foraging_enabled=True).advance(
        "r", seconds=1, command_id="auto-share",
        expected_revision=db.load("r").revision)
    assert result.state.npcs["basim"]["beliefs"]["food:grove"]["source"] == "adel"
    assert "food:grove" not in result.state.npcs["omar"]["beliefs"]
    # Public result IDs describe deliveries, not the separate acknowledgement
    # events that consume them; every delivery is reported only once.
    assert result.knowledge_shares
    assert len(result.knowledge_shares) == len(set(result.knowledge_shares))
    db.verify("r")


def test_explicit_observe_opt_in_records_food_without_changing_legacy_path(world):
    db, clock = world
    before = db.load("r").revision
    s = NPCMovementService(db, clock).observe(
        "r", "adel", command_id="explicit-food", expected_revision=before,
        knowledge_enabled=True)
    assert s.npcs["adel"]["beliefs"]["food:grove"]["text"] == "food-state:present; observed_at=0"
    assert s.revision == before + 3
    db.verify("r")
