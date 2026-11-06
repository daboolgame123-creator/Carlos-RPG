"""03-A7c: persisted observer-only visible-rest memory, not medical knowledge."""
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCService
from carlos_sim.actions import NPCActionService
from carlos_sim.movement import NPCMovementService
from carlos_sim.injury_observation import recall_rest_activity
from carlos_sim.store import InvalidEvent
from test_actions import setup as actions_world


def start_world(db, *, injury):
    actions_world(db, fatigue=90 if not injury else 5)
    if injury:
        now = db.load("world")
        db.append("world", "injury-bootstrap", now.revision, [
            DomainEvent("InjuryRecorded", None, "trusted setup", now.time, {
                "injury_id": "nora-hidden", "subject_id": "nora",
                "severity": 65, "source": "trusted_test_bootstrap"
            })], bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session("world")
    NPCService(db, clock).decide(
        "world", "nora", command_id="choose",
        expected_revision=db.load("world").revision,
    )
    started = NPCActionService(db, clock).start(
        "world", "nora", "nora-rest",
        expected_revision=db.load("world").revision,
    )
    return clock, NPCMovementService(db, clock), started.state


@pytest.mark.parametrize("injury", [False, True])
def test_first_hand_memory_is_bounded_private_and_persistent(tmp_path, injury):
    path = tmp_path / "remember.sqlite"
    with SQLiteEventStore(path) as db:
        clock, movement, pre = start_world(db, injury=injury)
        assert recall_rest_activity(pre, "basim") == ()
        observed = movement.observe(
            "world", "basim", command_id="look",
            expected_revision=pre.revision, activity_enabled=True,
        )
        expected = ({
            "subject_id": "nora", "sign": "visible_resting",
            "observed_at": 0, "source": "observation:square",
            "interpretation": "cause_unknown",
        },)
        assert recall_rest_activity(observed, "basim") == expected
        assert recall_rest_activity(observed, "nora") == ()
        assert all("nora-hidden" not in repr(b)
                   for b in observed.npcs["basim"]["beliefs"].values())
        assert "severity" not in repr(expected)
        assert observed.injuries == pre.injuries
        assert observed.resources == pre.resources
        assert observed.treatments == pre.treatments
        assert db.verify("world").to_dict() == observed.to_dict()
        db.snapshot("world")
        original = observed.to_dict()
    with SQLiteEventStore(path) as reopened:
        loaded = reopened.load("world")
        assert loaded.to_dict() == original
        assert reopened.verify("world").to_dict() == original
        assert recall_rest_activity(loaded, "basim") == expected
        assert recall_rest_activity(loaded, "nora") == ()
        clock = TimeEngine(reopened)
        clock.open_session("world")
        later = clock.advance("world", seconds=121, command_id="later",
                              expected_revision=loaded.revision).state
        assert recall_rest_activity(later, "basim") == expected
        assert reopened.verify("world").to_dict() == later.to_dict()


def test_no_passive_memory_or_knowledge_leak(tmp_path):
    with SQLiteEventStore(tmp_path / "passive.sqlite") as db:
        _clock, movement, before = start_world(db, injury=True)
        without_opt_in = movement.observe(
            "world", "basim", command_id="normal",
            expected_revision=before.revision,
        )
        assert recall_rest_activity(without_opt_in, "basim") == ()
        assert recall_rest_activity(without_opt_in, "nora") == ()
        after = movement.observe(
            "world", "basim", command_id="explicit",
            expected_revision=without_opt_in.revision, activity_enabled=True,
        )
        assert len(recall_rest_activity(after, "basim")) == 1
        # A distinct NPC has to independently observe the same behavior.
        assert recall_rest_activity(after, "nora") == ()
        assert db.verify("world").to_dict() == after.to_dict()


@pytest.mark.parametrize("alter", [
    "fake_actor", "fake_site", "fake_time", "fake_sign",
    "fake_subject", "hearsay", "fake_confidence",
])
def test_forged_restatement_fails_atomically(tmp_path, alter):
    with SQLiteEventStore(tmp_path / ("forgery-" + alter + ".sqlite")) as db:
        clock, movement, before = start_world(db, injury=True)
        observed = movement.observe(
            "world", "basim", command_id="ordinary",
            expected_revision=before.revision,
        )
        payload = {
            "npc_id": "basim", "delivery_id": "forged-" + alter,
            "key": "visible-rest:nora:0",
            "claim": {
                "text": "visible-resting; observed_at=0",
                "source": "observation:square",
                "received_at": 0, "confidence": 90,
            },
            "sender_id": "basim", "location_id": "square",
            "method": "observation",
        }
        actor = "basim"
        if alter == "fake_actor":
            actor = "nora"
        elif alter == "fake_site":
            payload["location_id"] = "unknown"
        elif alter == "fake_time":
            payload["key"] = "visible-rest:nora:1"
        elif alter == "fake_sign":
            payload["claim"]["text"] = "limping; observed_at=0"
        elif alter == "fake_subject":
            payload["key"] = "visible-rest:basim:0"
        elif alter == "hearsay":
            payload["method"] = "message"
            payload["sender_id"] = "nora"
            actor = "nora"
            payload["claim"]["source"] = "nora"
        elif alter == "fake_confidence":
            payload["claim"]["confidence"] = 100
        from carlos_sim.store import InvalidEvent
        with pytest.raises(InvalidEvent):
            db.append("world", "bad-" + alter, observed.revision, [
                DomainEvent("NPCInformationDelivered", actor,
                            "forged activity evidence", observed.time, payload),
            ], npc_authorized=True)
        assert db.load("world").to_dict() == observed.to_dict()
        assert db.verify("world").to_dict() == observed.to_dict()


def test_no_rest_cannot_mint_visible_rest_memory(tmp_path):
    with SQLiteEventStore(tmp_path / "no-rest.sqlite") as db:
        actions_world(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        state = NPCMovementService(db, clock).observe(
            "world", "basim", command_id="look",
            expected_revision=db.load("world").revision, activity_enabled=True,
        )
        assert recall_rest_activity(state, "basim") == ()
        assert db.verify("world").to_dict() == state.to_dict()


def test_seven_npc_village_each_witness_keeps_own_memory(tmp_path):
    from test_property_02h1 import village
    path = tmp_path / "seven-witnesses.sqlite"
    with SQLiteEventStore(path) as db:
        village(db)
        before = db.load("v")
        db.append("v", "injury", before.revision, [
            DomainEvent("InjuryRecorded", None, "trusted time-zero injury", 0, {
                "injury_id": "secret-nora", "subject_id": "nora",
                "severity": 65, "source": "trusted_test_bootstrap",
            })], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("v")
        NPCService(db, clock).decide(
            "v", "nora", command_id="rest-choice",
            expected_revision=db.load("v").revision)
        NPCActionService(db, clock).start(
            "v", "nora", "rest", expected_revision=db.load("v").revision)
        movement = NPCMovementService(db, clock)
        basim = movement.observe(
            "v", "basim", command_id="basimlook",
            expected_revision=db.load("v").revision,
            activity_enabled=True)
        assert len(recall_rest_activity(basim, "basim")) == 1
        for who in ("nora", "salma", "adel", "huda", "omar", "layla"):
            assert recall_rest_activity(basim, who) == ()
        salma = movement.observe(
            "v", "salma", command_id="salmalook",
            expected_revision=basim.revision,
            activity_enabled=True)
        assert recall_rest_activity(salma, "salma") == recall_rest_activity(salma, "basim")
        assert recall_rest_activity(salma, "adel") == ()
        assert recall_rest_activity(salma, "huda") == ()
        assert recall_rest_activity(salma, "omar") == ()
        assert db.verify("v").to_dict() == salma.to_dict()
        db.snapshot("v")
        original = salma.to_dict()
    with SQLiteEventStore(path) as db:
        assert db.load("v").to_dict() == original
        assert db.verify("v").to_dict() == original
        assert len(recall_rest_activity(db.load("v"), "basim")) == 1
        assert len(recall_rest_activity(db.load("v"), "salma")) == 1
        assert recall_rest_activity(db.load("v"), "omar") == ()


def test_second_explicit_look_same_tick_does_not_duplicate_memory(tmp_path):
    with SQLiteEventStore(tmp_path / "duplicate-look.sqlite") as db:
        _clock, movement, before = start_world(db, injury=True)
        first = movement.observe(
            "world", "basim", command_id="firstlook",
            expected_revision=before.revision, activity_enabled=True)
        memories = recall_rest_activity(first, "basim")
        assert len(memories) == 1
        second = movement.observe(
            "world", "basim", command_id="secondlook",
            expected_revision=first.revision, activity_enabled=True)
        assert recall_rest_activity(second, "basim") == memories
        assert len([key for key in second.npcs["basim"]["beliefs"]
                    if key.startswith("visible-rest:")]) == 1
        assert db.verify("world").to_dict() == second.to_dict()


def test_memory_at_different_ticks_is_historical_not_current_diagnosis(tmp_path):
    with SQLiteEventStore(tmp_path / "history.sqlite") as db:
        clock, movement, before = start_world(db, injury=False)
        first = movement.observe(
            "world", "basim", command_id="initiallook",
            expected_revision=before.revision, activity_enabled=True)
        advanced = clock.advance(
            "world", seconds=1, command_id="after1second",
            expected_revision=first.revision).state
        second = movement.observe(
            "world", "basim", command_id="laterlook",
            expected_revision=advanced.revision, activity_enabled=True)
        events = recall_rest_activity(second, "basim")
        assert [e["observed_at"] for e in events] == [0, 1]
        assert all(e["interpretation"] == "cause_unknown" for e in events)
        assert all(e["sign"] == "visible_resting" for e in events)
        assert db.verify("world").to_dict() == second.to_dict()


def test_no_direct_belief_mutation_without_evidenced_delivery(tmp_path):
    with SQLiteEventStore(tmp_path / "ack-injection.sqlite") as db:
        _clock, movement, before = start_world(db, injury=True)
        sight = movement.observe(
            "world", "basim", command_id="normal-look",
            expected_revision=before.revision)
        forged_ack = DomainEvent(
            "NPCBeliefReceived", "basim", "fabricated acknowledgement", 0, {
                "npc_id": "basim", "key": "visible-rest:nora:0",
                "delivery_id": "missing-delivery",
            })
        with pytest.raises(InvalidEvent):
            db.append("world", "invent-memory", sight.revision,
                      [forged_ack], npc_authorized=True)
        assert recall_rest_activity(db.load("world"), "basim") == ()
        assert db.verify("world").to_dict() == sight.to_dict()


def test_activity_memory_does_not_propagate_through_food_sharing(tmp_path):
    from carlos_sim.knowledge import choose_food_sharing_round
    with SQLiteEventStore(tmp_path / "no-sharing.sqlite") as db:
        _clock, movement, before = start_world(db, injury=True)
        witnessed = movement.observe(
            "world", "basim", command_id="witness",
            expected_revision=before.revision, activity_enabled=True)
        assert len(recall_rest_activity(witnessed, "basim")) == 1
        proposed = choose_food_sharing_round(witnessed.to_dict())
        assert not any(
            e.data.get("key", "").startswith("visible-rest:")
            for e in proposed
        )
        assert recall_rest_activity(witnessed, "nora") == ()
        assert db.verify("world").to_dict() == witnessed.to_dict()


def test_pending_first_hand_delivery_is_not_duplicated_by_next_look(tmp_path):
    with SQLiteEventStore(tmp_path / "pending-look.sqlite") as db:
        _clock, movement, before = start_world(db, injury=True)
        observed = movement.observe(
            "world", "basim", command_id="plain-look",
            expected_revision=before.revision)
        pending = DomainEvent(
            "NPCInformationDelivered", "basim", "test pending physical evidence", 0, {
                "npc_id": "basim", "delivery_id": "pending-activity",
                "key": "visible-rest:nora:0",
                "claim": {"text": "visible-resting; observed_at=0",
                          "source": "observation:square",
                          "received_at": 0, "confidence": 90},
                "sender_id": "basim", "location_id": "square",
                "method": "observation",
            })
        after_delivery = db.append(
            "world", "pending-delivery", observed.revision,
            [DomainEvent("NPCObserved", "basim", "same-command direct sighting", observed.time,
                         {"npc_id": "basim"}), pending],
            npc_authorized=True, movement_authorized=True)
        assert recall_rest_activity(after_delivery, "basim") == ()
        assert "pending-activity" in after_delivery.npcs["basim"]["inbox"]
        repeated = movement.observe(
            "world", "basim", command_id="next-look",
            expected_revision=after_delivery.revision, activity_enabled=True)
        assert recall_rest_activity(repeated, "basim") == ()
        assert set(repeated.npcs["basim"]["inbox"]) == {"pending-activity"}
        ack = DomainEvent(
            "NPCBeliefReceived", "basim", "acknowledge genuine pending observation", 0,
            {"npc_id": "basim", "key": "visible-rest:nora:0",
             "delivery_id": "pending-activity"})
        completed = db.append(
            "world", "ack-pending", repeated.revision, [ack], npc_authorized=True)
        assert len(recall_rest_activity(completed, "basim")) == 1
        assert completed.npcs["basim"]["inbox"] == {}
        assert db.verify("world").to_dict() == completed.to_dict()


def test_capacity_exhaustion_does_not_block_valid_local_look(tmp_path):
    """A character with 64 genuine memories can still look around."""
    from carlos_sim.injury_observation import MAX_REST_MEMORIES
    with SQLiteEventStore(tmp_path / "bounded-history.sqlite") as db:
        clock, movement, state = start_world(db, injury=True)
        for tick in range(MAX_REST_MEMORIES + 1):
            current = db.load("world")
            observed = movement.observe(
                "world", "basim", command_id=f"look{tick}",
                expected_revision=current.revision, activity_enabled=True)
            assert len(recall_rest_activity(observed, "basim")) == min(
                tick + 1, MAX_REST_MEMORIES)
            if tick != MAX_REST_MEMORIES:
                clock.advance("world", seconds=1, command_id=f"wait{tick}",
                              expected_revision=observed.revision)
        assert len(recall_rest_activity(db.load("world"), "basim")) == MAX_REST_MEMORIES
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_pending_evidence_cannot_bypass_finite_memory_capacity(tmp_path):
    """64 unacknowledged first-hand sightings block an illicit 65th delivery."""
    from carlos_sim.injury_observation import MAX_REST_MEMORIES
    with SQLiteEventStore(tmp_path / "pending-cap.sqlite") as db:
        clock, movement, _before = start_world(db, injury=True)
        for tick in range(MAX_REST_MEMORIES):
            observed = movement.observe(
                "world", "basim", command_id=f"look-{tick}",
                expected_revision=db.load("world").revision)
            pending = DomainEvent("NPCInformationDelivered", "basim",
                                  "legitimate pending visual evidence", tick, {
                "npc_id": "basim", "delivery_id": f"pending-{tick}",
                "key": f"visible-rest:nora:{tick}",
                "claim": {
                    "text": f"visible-resting; observed_at={tick}",
                    "source": "observation:square",
                    "received_at": tick, "confidence": 90,
                },
                "sender_id": "basim", "location_id": "square",
                "method": "observation",
            })
            db.append("world", f"delivery-{tick}", observed.revision,
                      [DomainEvent("NPCObserved", "basim", "same-command direct sighting", observed.time,
                         {"npc_id": "basim"}), pending],
            npc_authorized=True, movement_authorized=True)
            if tick != MAX_REST_MEMORIES - 1:
                clock.advance("world", seconds=1, command_id=f"tick-{tick}",
                              expected_revision=db.load("world").revision)
        state = db.load("world")
        assert len(state.npcs["basim"]["inbox"]) == MAX_REST_MEMORIES
        assert recall_rest_activity(state, "basim") == ()
        clock.advance("world", seconds=1, command_id="tick-capacity",
                      expected_revision=state.revision)
        seen = movement.observe(
            "world", "basim", command_id="look-capacity",
            expected_revision=db.load("world").revision,
            activity_enabled=True)
        assert len(seen.npcs["basim"]["inbox"]) == MAX_REST_MEMORIES
        assert recall_rest_activity(seen, "basim") == ()
        forged = DomainEvent("NPCInformationDelivered", "basim",
                              "overflow attempt", seen.time, {
            "npc_id": "basim", "delivery_id": "over-capacity",
            "key": f"visible-rest:nora:{seen.time}",
            "claim": {
                "text": f"visible-resting; observed_at={seen.time}",
                "source": "observation:square",
                "received_at": seen.time, "confidence": 90,
            },
            "sender_id": "basim", "location_id": "square",
            "method": "observation",
        })
        with pytest.raises(InvalidEvent):
            db.append("world", "overflow-forgery", seen.revision,
                      [forged], npc_authorized=True)
        assert db.load("world").to_dict() == seen.to_dict()
        assert db.verify("world").to_dict() == seen.to_dict()
