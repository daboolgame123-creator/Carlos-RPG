"""PLAY-31: a player can actually run a seven-NPC village in a disposable CLI."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from play_physical_supply import WORLD, PEOPLE, audit_physical_supply, seed_physical_supply
from play_village_local import create_session, execute, HELP, MAX_WAIT


def session(tmp_path):
    db = SQLiteEventStore(tmp_path / "playable.sqlite")
    clock = TimeEngine(db)
    gateway = create_session(db, clock)
    return db, clock, gateway


def test_playable_bootstrap_is_seven_real_npcs_finite_seed_water_and_carlos_profile(tmp_path):
    db, clock, gateway = session(tmp_path)
    try:
        state = db.verify(WORLD)
        assert len(state.npcs) == len(PEOPLE) == 7
        assert state.schema_version == 41 and state.rules_version == 54
        assert state.entities["carlos"]["location_id"] == "home"
        assert state.routes["home-market"]["seconds"] == 90
        assert "carlos" in state.rpg_profiles
        assert state.resources["carlos"]["coin_copper"] == 10
        assert state.resources["carlos"]["food"] == 0
        assert state.resources["market"]["food"] == 2
        assert audit_physical_supply(state, seed=1, water=2,
                                     buyer_copper=2, personal_food=2,
                                     initial_market_food=2)["copper"] == 12
        assert execute(gateway, "status", 1).status == "rpg_status"
        assert execute(gateway, "supplies", 2).details["balances"]["food"] == 0
        assert execute(gateway, "scene", 3).details["location_id"] == "home"
        assert {e["route_id"] for e in gateway.inspect().details["exits"]} == {"home-market"}
    finally:
        clock.close_session(WORLD)
        db.close()


def test_no_player_auto_move_and_real_ninety_second_road(tmp_path):
    db, clock, gateway = session(tmp_path)
    try:
        state_before = db.load(WORLD)
        road = execute(gateway, "move home-market", 1)
        assert road.status == "traveling"
        assert db.load(WORLD).time == state_before.time == 0
        midway = execute(gateway, "wait 89", 2)
        assert midway.status == "traveling"
        assert midway.time == 89
        assert execute(gateway, "scene", 3).details["remaining_seconds"] == 1
        arrived = execute(gateway, "wait 1", 4)
        assert arrived.time == 90
        assert execute(gateway, "scene", 5).details["location_id"] == "market"
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_gateway_only_shows_player_scoped_projection_and_no_hidden_state(tmp_path):
    db, clock, gateway = session(tmp_path)
    try:
        handoff = execute(gateway, "handoff", 1)
        assert handoff["format"] == "carlos-player-handoff-v1"
        assert handoff["canonical_story"] is False
        assert handoff["disposable_test"] is True
        assert handoff["player_supplies"]["balances"]["coin_copper"] == 10
        assert "npcs" not in handoff and "resources" not in handoff
        before = db.load(WORLD).revision
        for cmd in ("scene", "status", "supplies", "needs", "offers", "food",
                    "purchases", "meals", "gifts", "conversations", "remember", "handoff"):
            assert execute(gateway, cmd, 10) is not None
        assert db.load(WORLD).revision == before
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("cmd", [
    "move well-farm", "give salma food 1", "buy fake 1 2",
    "eat", "wait 21601", "wait -1", "wait 0",
    "talk salma greeting Hello", "unknown", "give nobody food 1",
])
def test_bad_player_actions_do_not_create_events_or_teleport(tmp_path, cmd):
    db, clock, gateway = session(tmp_path)
    try:
        before = db.load(WORLD).to_dict()
        with pytest.raises((ValueError, PermissionError, InvalidEvent)):
            execute(gateway, cmd, 1)
        assert db.verify(WORLD).to_dict() == before
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("nonbool", [None, 1, 0, "true", []])
def test_demo_setup_is_strictly_opt_in(tmp_path, nonbool):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        with pytest.raises(ValueError, match="playable_demo"):
            seed_physical_supply(db, playable_demo=nonbool)


def test_previous_fixture_is_not_converted_into_playable_story(tmp_path):
    with SQLiteEventStore(tmp_path / "old.sqlite") as db:
        seed_physical_supply(db)
        state = db.verify(WORLD)
        assert "home-market" not in state.routes
        assert "carlos" not in state.rpg_profiles
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_real_console_script_runs_and_exits_without_saving(tmp_path):
    script = Path(__file__).with_name("play_village_local.py")
    run = subprocess.run(
        [sys.executable, str(script)],
        input="scene\nstatus\nmove home-market\nwait 90\nscene\nquit\n",
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert run.returncode == 0, run.stderr + run.stdout[-1000:]
    assert "7 autonomous NPCs" in run.stdout
    assert "home-market" in run.stdout
    assert "location_id: market" in run.stdout
    assert "Temporary world destroyed" in run.stdout
    assert "Rejected:" not in run.stdout
    assert "forbidden" not in run.stdout.lower()


def test_help_includes_actual_player_actions():
    assert MAX_WAIT == 21600
    for verb in ("buy", "forage", "askfood", "supplies", "needs", "talk",
                 "move", "wait", "give", "eat", "handoff"):
        assert verb in HELP
