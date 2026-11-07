"""PLAY-17: exactly local, authenticated physical action sightings survive replay.

All tests use disposable, synthetic worlds; never Carlos's story save.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import (
    DomainEvent, NPCService, PlayerGateway, SQLiteEventStore, TimeEngine,
    apply_event,
)
from carlos_sim.actions import NPCActionService
from carlos_sim.movement import _visible
from carlos_sim.player_handoff import player_handoff
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict
from test_player_visible_activity_batch_04 import (
    player_in_action_world, begin_action,
)
from test_production_02b import setup as setup_production, start as start_production
from living_player_fixture import (
    WORLD, living_player_gateway, setup_living_player_world,
)


def look(db, gw, cid="look-once"):
    return gw.observe(command_id=cid, expected_revision=db.load(gw.world_id).revision)


def test_work_memory_requires_explicit_look_and_survives_end_of_action(tmp_path):
    with SQLiteEventStore(tmp_path / "work.sqlite") as db:
        clock, gw = player_in_action_world(db, fatigue=5)
        action, _ = begin_action(db, clock, "basim", "working-today")
        assert action == "work"
        before = db.load("world").to_dict()
        for _ in range(3):
            assert gw.inspect().details["activities"] == (
                {"actor_id": "basim", "activity": "working"},)
            assert "witnessed_events" not in gw.recall().details
            assert "witnessed_events" not in player_handoff(gw)["player_memory"]
        assert db.load("world").to_dict() == before
        look(db, gw)
        expected = ({
            "actor_id": "basim", "activity": "working",
            "location_id": "square", "at": 0,
        },)
        assert gw.recall().details["witnessed_events"] == expected
        assert player_handoff(gw)["player_memory"]["witnessed_events"] == expected
        private = json.dumps(player_handoff(gw)["player_memory"])
        for key in ("needs", "fatigue", "action_id", "due", "injuries",
                    "resources", "goals", "salary"):
            assert key not in private
        clock.advance("world", seconds=180, command_id="finish-work",
                      expected_revision=db.load("world").revision)
        assert gw.inspect().details["activities"] == ()
        assert gw.recall().details["witnessed_events"] == expected
        look(db, gw, cid="look-later")
        assert gw.recall().details["witnessed_events"] == expected
        assert db.verify("world").to_dict() == db.load("world").to_dict()


@pytest.mark.parametrize("fatigue,injured", [(90, False), (5, True)])
def test_resting_is_a_sighting_not_diagnosis(tmp_path, fatigue, injured):
    with SQLiteEventStore(tmp_path / "rest.sqlite") as db:
        clock, gw = player_in_action_world(db, fatigue=fatigue, injury=injured)
        action, _ = begin_action(db, clock, "nora", "real-rest")
        assert action == "rest"
        look(db, gw)
        events = gw.recall().details["witnessed_events"]
        assert events == ({
            "actor_id": "nora", "activity": "resting",
            "location_id": "square", "at": 0,
        },)
        package = json.dumps(player_handoff(gw))
        assert "real-rest" not in package
        assert "nora-hidden-wound" not in package
        assert "severity" not in package
        assert "treatment" not in package
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_seven_characters_remote_actions_not_leaked_or_misattributed(tmp_path):
    with SQLiteEventStore(tmp_path / "seven.sqlite") as db:
        setup_living_player_world(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gw = living_player_gateway(db, clock)
        for who in ("basim", "nora"):
            NPCService(db, clock).decide(
                WORLD, who, command_id="decide-" + who,
                expected_revision=db.load(WORLD).revision)
            NPCActionService(db, clock).start(
                WORLD, who, "running-" + who,
                expected_revision=db.load(WORLD).revision)
        assert gw.inspect().details["activities"] == (
            {"actor_id": "basim", "activity": "working"},)
        look(db, gw)
        local = gw.recall().details["witnessed_events"]
        assert local == ({
            "actor_id": "basim", "activity": "working",
            "location_id": "square", "at": 0,
        },)
        assert "nora" not in json.dumps(player_handoff(gw))
        gw.move("square-bakery", command_id="go-bakery",
                expected_revision=db.load(WORLD).revision)
        with pytest.raises(ValueError, match="travelling"):
            look(db, gw, cid="fake-in-transit")
        assert gw.recall().details["witnessed_events"] == local
        gw.wait(40, command_id="arrive-bakery",
                expected_revision=db.load(WORLD).revision)
        assert gw.inspect().details["activities"] == (
            {"actor_id": "nora", "activity": "resting"},)
        look(db, gw, cid="bakery-look")
        both = gw.recall().details["witnessed_events"]
        assert both == local + ({
            "actor_id": "nora", "activity": "resting",
            "location_id": "bakery", "at": 40,
        },)
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_production_is_qualitative_and_durable_not_recipe_or_stock(tmp_path):
    with SQLiteEventStore(tmp_path / "bakery.sqlite") as db:
        setup_production(db, routes=True)
        db.append("test", "add-player", db.load("test").revision, [
            DomainEvent("EntityCreated", None, "test fixture", 0, {
                "id": "carlos", "name": "Carlos", "controller": "player",
                "location_id": "square",
            }),
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("test")
        gw = PlayerGateway(db, clock, world_id="test", player_id="carlos")
        start_production(db, clock, "basim", "baking-job")
        gw.move("bakery-square", command_id="go-bakery",
                expected_revision=db.load("test").revision)
        clock.advance("test", seconds=50, command_id="arrive",
                      expected_revision=db.load("test").revision)
        look(db, gw)
        memories = gw.recall().details["witnessed_events"]
        assert memories == ({
            "actor_id": "basim", "activity": "producing",
            "location_id": "bakery", "at": 50,
        },)
        payload = json.dumps(player_handoff(gw)["player_memory"])
        for secret in ("baking-job", "recipe_id", "input_before",
                       "output_amount", "grain", "oven", "tools"):
            assert secret not in payload
        clock.advance("test", seconds=40, command_id="done",
                      expected_revision=db.load("test").revision)
        assert gw.inspect().details["activities"] == ()
        assert gw.recall().details["witnessed_events"] == memories


def test_stale_duplicate_empty_and_other_player_isolation(tmp_path):
    with SQLiteEventStore(tmp_path / "other.sqlite") as db:
        clock, gw = player_in_action_world(db, fatigue=5)
        begin_action(db, clock, "basim", "real-work")
        before = db.load("world")
        with pytest.raises(RevisionConflict):
            gw.observe(command_id="stale", expected_revision=before.revision - 1)
        db.append("world", "other-human", before.revision, [
            DomainEvent("EntityCreated", None, "additional test player", 0, {
                "id": "other", "name": "Other", "controller": "player",
                "location_id": "square",
            }),
        ], bootstrap=True)
        other = PlayerGateway(db, clock, world_id="world", player_id="other")
        assert other.recall().details == {"observations": (), "hearsay": ()}
        first = look(db, gw, "only-carlos")
        assert first.status == "present"
        assert "witnessed_events" not in other.recall().details
        assert "basim" not in json.dumps(other.recall().details)
        snapshot = db.load("world").to_dict()
        with pytest.raises(DuplicateCommand):
            look(db, gw, "only-carlos")
        assert db.load("world").to_dict() == snapshot
        assert db.verify("world").to_dict() == snapshot


def test_forged_activity_look_is_rejected_atomically(tmp_path):
    with SQLiteEventStore(tmp_path / "forgery.sqlite") as db:
        clock, gw = player_in_action_world(db, fatigue=5)
        begin_action(db, clock, "basim", "real-work")
        state = db.load("world")
        occupants = _visible(state.to_dict(), "square")
        valid = {"location_id": "square", "occupants": occupants,
                 "activities": [{"actor_id": "basim", "activity": "working"}]}
        variations = [
            dict(valid, activities=[{"actor_id": "basim", "activity": "resting"}]),
            dict(valid, activities=[{"actor_id": "nora", "activity": "working"}]),
            dict(valid, activities=[]),
            dict(valid, activities=[{"actor_id": "basim", "activity": "working",
                                     "reason": "secret-injury"}]),
            dict(valid, location_id="unknown"),
            dict(valid, occupants=["basim"]),
        ]
        for idx, data in enumerate(variations):
            event = DomainEvent("PlayerObserved", "carlos",
                                "player deliberately looked around locally",
                                state.time, data)
            with pytest.raises((InvalidEvent, ValueError)):
                db.append("world", "player-observe:fake-" + str(idx),
                          state.revision, [event], movement_authorized=True)
            with pytest.raises(ValueError):
                apply_event(state, event, movement_authorized=True)
            assert db.load("world").to_dict() == state.to_dict()
        valid_event = DomainEvent("PlayerObserved", "carlos",
                                  "player deliberately looked around locally",
                                  state.time, valid)
        for cid in ("forged-memory", "player-wait:not-a-look"):
            with pytest.raises(InvalidEvent, match="dedicated active look"):
                db.append("world", cid, state.revision, [valid_event],
                          movement_authorized=True)
        with pytest.raises(InvalidEvent):
            db.append("world", "player-observe:untrusted", state.revision,
                      [valid_event], movement_authorized=False)
        with pytest.raises(InvalidEvent):
            db.append("world", "player-observe:bundled", state.revision,
                      [valid_event, valid_event], movement_authorized=True)
        assert db.verify("world").to_dict() == state.to_dict()


def test_snapshot_and_sqlite_reopen_preserve_old_sighting(tmp_path):
    filename = tmp_path / "replay.sqlite"
    with SQLiteEventStore(filename) as db:
        clock, gw = player_in_action_world(db, fatigue=5)
        begin_action(db, clock, "basim", "work-until-done")
        look(db, gw)
        saved = gw.recall().details
        snapshot = db.snapshot("world").to_dict()
        assert db.verify("world").to_dict() == snapshot
    with SQLiteEventStore(filename) as db:
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        assert gw.recall().details == saved
        assert player_handoff(gw)["player_memory"] == saved
        before = db.load("world").to_dict()
        for _ in range(3):
            assert gw.recall().details == saved
        assert db.load("world").to_dict() == before
        assert db.verify("world").to_dict() == snapshot
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
