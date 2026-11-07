"""PLAY-18: local NPC speaking is witnessed, not omnisciently overheard."""
from __future__ import annotations

import json

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCSocialService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.movement import _visible
from carlos_sim.player_handoff import player_handoff
from carlos_sim.store import InvalidEvent
from test_social_autonomy import make_world


def scene(tmp_path, *, separate=False, social=True):
    db = SQLiteEventStore(tmp_path / "talk.sqlite")
    make_world(db, separate=separate)
    clock = TimeEngine(db)
    clock.open_session("village")
    gw = PlayerGateway(
        db, clock, world_id="village", player_id="carlos",
        engine=LivingWorldEngine(db, clock, social_enabled=social),
    )
    return db, clock, gw


def tick(db, gw, command="advance"):
    return gw.wait(1, command_id=command,
                   expected_revision=db.load("village").revision)


def test_real_local_npc_speech_visible_as_talking_but_no_private_words(tmp_path):
    db, _, gw = scene(tmp_path)
    with db:
        initial = db.load("village").to_dict()
        assert gw.recall().details == {"observations": (), "hearsay": ()}
        assert db.load("village").to_dict() == initial
        result = tick(db, gw)
        assert result.details["nearby_conversations"] == ({
            "sender_id": "aaron", "recipient_id": "zora",
            "activity": "talking", "at": 0,
        },)
        witnessed = gw.recall().details["witnessed_events"]
        assert witnessed == ({
            "actor_id": "aaron", "recipient_id": "zora",
            "activity": "talking", "location_id": "square", "at": 0,
        },)
        snapshot = db.load("village")
        assert tuple(snapshot.social_messages) == ("auto-social:aaron:0",)
        assert snapshot.social_messages["auto-social:aaron:0"]["status"] == "received"
        public = player_handoff(gw)
        assert public["player_memory"]["witnessed_events"] == witnessed
        envelope = json.dumps(public)
        for private in ("social_messages", "relations", "trust_before",
                        "trust_after", '"kind"', '"text"', "first_contact"):
            assert private not in envelope
        assert db.verify("village").to_dict() == snapshot.to_dict()


def test_distant_actors_remain_invisible_and_no_social_event_occurs(tmp_path):
    db, _, gw = scene(tmp_path, separate=True)
    with db:
        result = tick(db, gw)
        assert "nearby_conversations" not in result.details
        assert "witnessed_events" not in gw.recall().details
        assert db.load("village").social_messages == {}
        assert db.verify("village").to_dict() == db.load("village").to_dict()


def test_player_in_transit_cannot_overhear_npc_speech(tmp_path):
    db, _, gw = scene(tmp_path)
    with db:
        gw.move("path", command_id="travelling",
                expected_revision=db.load("village").revision)
        result = tick(db, gw)
        assert "nearby_conversations" not in result.details
        assert "witnessed_events" not in gw.recall().details
        assert len(db.load("village").social_messages) == 1
        assert db.verify("village").to_dict() == db.load("village").to_dict()


def test_unobserved_manual_social_interaction_is_not_retroactive_memory(tmp_path):
    db, clock, gw = scene(tmp_path)
    with db:
        NPCSocialService(db, clock).interact(
            "village", "aaron", "zora", kind="greeting", text="Private words",
            message_id="direct", expected_revision=db.load("village").revision)
        assert "witnessed_events" not in gw.recall().details
        assert "Private words" not in json.dumps(player_handoff(gw))
        assert db.verify("village").to_dict() == db.load("village").to_dict()


def test_other_player_cannot_read_carlos_witnessed_conversation(tmp_path):
    db, clock, gw = scene(tmp_path)
    with db:
        prior = db.load("village")
        db.append("village", "add-second-player", prior.revision, [
            DomainEvent("EntityCreated", None, "second local player", 0, {
                "id": "other", "name": "Other", "controller": "player",
                "location_id": "square",
            }),
        ], bootstrap=True)
        other = PlayerGateway(db, clock, world_id="village", player_id="other")
        tick(db, gw)
        assert gw.recall().details["witnessed_events"][0]["activity"] == "talking"
        assert "witnessed_events" not in other.recall().details
        assert "aaron" not in json.dumps(other.recall().details)
        assert db.verify("village").to_dict() == db.load("village").to_dict()


def test_forged_remote_social_observation_rolls_back_entire_command(tmp_path):
    db, clock, gw = scene(tmp_path, separate=True)
    with db:
        prior = db.load("village")
        observed = DomainEvent(
            "PlayerObserved", "carlos",
            "player witnessed nearby NPCs speaking", 0, {
                "location_id": "square",
                "occupants": _visible(prior.to_dict(), "square"),
            })
        fake_message = DomainEvent(
            "SocialMessageSent", "aaron", "forged remote conversation", 0, {
                "id": "forged", "recipient": "zora",
                "kind": "greeting", "text": "Secret that was never spoken",
            })
        with pytest.raises(InvalidEvent):
            db.append("village", "player-wait:forged", prior.revision,
                      [observed, fake_message],
                      movement_authorized=True, social_authorized=True)
        assert db.verify("village").to_dict() == prior.to_dict()
        assert "witnessed_events" not in gw.recall().details


def test_social_mode_off_retains_default_npc_actions_without_witness(tmp_path):
    db, _, gw = scene(tmp_path, social=False)
    with db:
        result = tick(db, gw)
        assert "nearby_conversations" not in result.details
        assert "witnessed_events" not in gw.recall().details
        assert not db.load("village").social_messages
        assert db.verify("village").to_dict() == db.load("village").to_dict()


def test_social_memory_snapshot_reopen_and_read_only_recall(tmp_path):
    filename = tmp_path / "talk.sqlite"
    db, clock, gw = scene(tmp_path)
    with db:
        tick(db, gw)
        remembered = gw.recall().details
        snapshot = db.snapshot("village").to_dict()
        assert db.verify("village").to_dict() == snapshot
    with SQLiteEventStore(filename) as reopened:
        new_clock = TimeEngine(reopened)
        new_clock.open_session("village")
        resumed = PlayerGateway(
            reopened, new_clock, world_id="village", player_id="carlos",
            engine=LivingWorldEngine(reopened, new_clock, social_enabled=True),
        )
        for _ in range(3):
            assert resumed.recall().details == remembered
            assert player_handoff(resumed)["player_memory"] == remembered
        assert reopened.load("village").to_dict() == snapshot
        assert reopened.verify("village").to_dict() == snapshot
        assert reopened.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
