"""PLAY-16: only first-hand, event-adjacent NPC meals enter Carlos's memory.

These are deliberately disposable worlds. SQLite/event evidence remains
authoritative; the narrator receives no remote meals or private NPC state.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.consumption import NPCConsumptionService
from carlos_sim.player_handoff import player_handoff
from living_player_fixture import (
    WORLD, PLAYER, living_player_gateway, setup_living_npc_survival_world,
    setup_living_foraging_world,
)


def make_world(tmp_path, *, survival=True):
    db = SQLiteEventStore(tmp_path / "memory.sqlite")
    (setup_living_npc_survival_world if survival
     else setup_living_foraging_world)(db)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    gateway = living_player_gateway(db, clock, npc_survival_demo=survival)
    return db, clock, gateway


def tick(db, gateway, command="player-advance"):
    return gateway.wait(1, command_id=command,
                        expected_revision=db.load(WORLD).revision)


def test_local_witness_keeps_only_real_basims_meal(tmp_path):
    db, _, gateway = make_world(tmp_path)
    with db:
        assert "witnessed_events" not in gateway.recall().details
        before = db.load(WORLD)
        result = tick(db, gateway)
        assert result.details["nearby_meals"] == (
            {"npc_id": "basim", "activity": "eating", "at": 0},)
        memory = gateway.recall().details["witnessed_events"]
        # PLAY-18 independently adds nearby NPC speech, but must never
        # invent a second meal or disclose Nora's remote consumption.
        meals = tuple(item for item in memory if item["activity"] == "eating")
        assert meals == ({
            "actor_id": "basim", "activity": "eating",
            "location_id": "square", "at": 0,
        },)
        assert all(item["activity"] in ("eating", "talking") for item in memory)
        assert db.load(WORLD).revision > before.revision
        view = player_handoff(gateway)
        assert view["player_memory"]["witnessed_events"] == memory
        assert "nora" not in json.dumps(view)
        for private in ("food_before", "food_after", "hunger_before",
                        "hunger_after", "quantity", "consumptions"):
            assert private not in json.dumps(view["player_memory"])
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_witness_history_is_read_only_stable_and_reopenable(tmp_path):
    db, clock, gateway = make_world(tmp_path)
    with db:
        tick(db, gateway)
        saved = gateway.recall().details
        original = db.verify(WORLD).to_dict()
        count = db.db.execute(
            "SELECT COUNT(*) FROM events WHERE world_id=?", (WORLD,)
        ).fetchone()[0]
        for _ in range(3):
            assert gateway.recall().details == saved
            assert player_handoff(gateway)["player_memory"] == saved
        assert db.db.execute(
            "SELECT COUNT(*) FROM events WHERE world_id=?", (WORLD,)
        ).fetchone()[0] == count
        db.snapshot(WORLD)
        assert db.load(WORLD).to_dict() == original

    with SQLiteEventStore(tmp_path / "memory.sqlite") as reopened:
        resumed_clock = TimeEngine(reopened)
        resumed_clock.open_session(WORLD)
        resumed = living_player_gateway(reopened, resumed_clock,
                                        npc_survival_demo=True)
        assert resumed.recall().details == saved
        assert player_handoff(resumed)["player_memory"] == saved
        assert reopened.verify(WORLD).to_dict() == original
        assert reopened.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_remote_meals_are_not_remembered_while_player_travels(tmp_path):
    db, _, gateway = make_world(tmp_path)
    with db:
        gateway.move("square-woods", command_id="leave",
                     expected_revision=db.load(WORLD).revision)
        result = tick(db, gateway)
        assert "nearby_meals" not in result.details
        assert "witnessed_events" not in gateway.recall().details
        assert "nora" not in json.dumps(player_handoff(gateway))
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_direct_npc_eating_and_plain_look_are_not_player_witness(tmp_path):
    db, clock, gateway = make_world(tmp_path)
    with db:
        gateway.observe(command_id="look-before-meal",
                        expected_revision=db.load(WORLD).revision)
        NPCConsumptionService(db, clock).eat(
            WORLD, "basim", 1, command_id="independent-npc-meal",
            expected_revision=db.load(WORLD).revision)
        memory = gateway.recall().details
        assert "witnessed_events" not in memory
        assert len(memory["observations"]) == 1
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_other_player_cannot_recall_carlos_witness(tmp_path):
    db, clock, gateway = make_world(tmp_path)
    with db:
        state = db.load(WORLD)
        db.append(WORLD, "other-human", state.revision, [
            DomainEvent("EntityCreated", None, "test second human", state.time, {
                "id": "other", "name": "Other", "controller": "player",
                "location_id": "square",
            })
        ], bootstrap=True)
        other = PlayerGateway(db, clock, world_id=WORLD, player_id="other",
                              engine=gateway.engine)
        tick(db, gateway)
        assert gateway.recall().details["witnessed_events"][0]["actor_id"] == "basim"
        assert "witnessed_events" not in other.recall().details
        assert "basim" not in json.dumps(other.recall().details)
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_default_village_and_invalid_observer_do_not_write_memory(tmp_path):
    db, clock, gateway = make_world(tmp_path, survival=False)
    with db:
        old = db.load(WORLD).to_dict()
        with pytest.raises(PermissionError):
            gateway.engine.advance(WORLD, seconds=1, command_id="player-wait:bad",
                                   expected_revision=old["revision"],
                                   player_observer_id="nora")
        assert db.load(WORLD).to_dict() == old
        tick(db, gateway)
        # Default mode may now witness local conversations, but still
        # cannot silently activate NPC hunger or eating.
        assert all(row["activity"] != "eating"
                   for row in gateway.recall().details.get("witnessed_events", ()))
        assert not db.load(WORLD).consumptions
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
