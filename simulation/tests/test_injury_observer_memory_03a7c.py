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
