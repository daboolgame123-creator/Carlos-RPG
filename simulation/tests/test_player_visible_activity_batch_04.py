"""PLAY-04 current, observable NPC activity for Carlos; never diagnoses.

No PlayerObserved schema change: activities are a read-only CURRENT view,
not retroactive actor knowledge or permanently remembered actions.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from carlos_sim import (
    DomainEvent, NPCService, PlayerGateway, SQLiteEventStore, TimeEngine,
)
from carlos_sim.actions import NPCActionService
from carlos_sim.player_activity_scene import visible_player_activities
from carlos_sim.player_handoff import player_handoff
from test_actions import setup as setup_actions
from test_production_02b import setup as setup_production, start as start_production

SIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM / "scenarios" / "test_village"))
from living_player_fixture import (  # noqa: E402
    WORLD, setup_living_player_world, living_player_gateway,
)


def player_in_action_world(db, *, fatigue: int = 5, injury: bool = False):
    setup_actions(db, fatigue=fatigue)
    events = [DomainEvent("EntityCreated", None, "test player at square", 0, {
        "id": "carlos", "name": "Carlos", "controller": "player",
        "location_id": "square",
    })]
    if injury:
        events.append(DomainEvent(
            "InjuryRecorded", None, "trusted private injury", 0, {
                "injury_id": "nora-hidden-wound", "subject_id": "nora",
                "severity": 65, "source": "trusted_test_bootstrap",
            }))
    db.append("world", "add-human-at-square", db.load("world").revision,
              events, bootstrap=True)
    clock = TimeEngine(db)
    clock.open_session("world")
    return clock, PlayerGateway(db, clock, world_id="world", player_id="carlos")


def begin_action(db, clock, who: str, action_id: str):
    decision = NPCService(db, clock).decide(
        "world", who, command_id="decide-" + action_id,
        expected_revision=db.load("world").revision)
    result = NPCActionService(db, clock).start(
        "world", who, action_id,
        expected_revision=db.load("world").revision)
    return decision.action, result


@pytest.mark.parametrize("injury,fatigue", [(False, 90), (True, 5)])
def test_nora_is_visibly_resting_without_exposing_the_cause(tmp_path, injury, fatigue):
    with SQLiteEventStore(tmp_path / "rest.sqlite") as db:
        clock, gw = player_in_action_world(db, fatigue=fatigue, injury=injury)
        before = db.load("world").to_dict()
        assert gw.inspect().details["activities"] == ()
        assert db.load("world").to_dict() == before
        action, started = begin_action(db, clock, "nora", "nora-rest")
        assert action == "rest"
        shown = ({"actor_id": "nora", "activity": "resting"},)
        assert visible_player_activities(started.state, "carlos") == shown
        view = gw.inspect()
        assert view.details["activities"] == shown
        output = player_handoff(gw)
        public = json.dumps(output)
        assert output["scene"]["details"]["activities"] == shown
        assert '"severity"' not in public
        assert "nora-hidden-wound" not in public
        assert '"needs"' not in public and '"beliefs"' not in public
        assert '"action_id"' not in public and '"due"' not in public
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_current_scene_is_read_only_and_player_look_is_not_retrospective_action_memory(tmp_path):
    with SQLiteEventStore(tmp_path / "look.sqlite") as db:
        clock, gw = player_in_action_world(db, fatigue=5)
        action, started = begin_action(db, clock, "basim", "basim-working")
        assert action == "work"
        live = gw.inspect()
        assert live.details["activities"] == ({"actor_id": "basim", "activity": "working"},)
        old = db.load("world").to_dict()
        for _ in range(3):
            assert gw.inspect().details["activities"] == live.details["activities"]
            assert gw.recall().details["observations"] == ()
            assert player_handoff(gw)["scene"]["details"]["activities"] == live.details["activities"]
        assert db.load("world").to_dict() == old
        gw.observe(command_id="genuine-look",
                   expected_revision=db.load("world").revision)
        memories = gw.recall().details["observations"]
        assert len(memories) == 1
        assert "activities" not in memories[0]
        assert "working" not in repr(memories)
        # Current action ends exactly at its trusted due tick.
        until = clock.advance(
            "world", seconds=180, command_id="finish-work",
            expected_revision=db.load("world").revision).state
        assert until.actions["basim-working"]["status"] == "completed"
        assert gw.inspect().details["activities"] == ()
        assert db.verify("world").to_dict() == until.to_dict()


def test_seven_independent_npcs_only_show_local_behaviors_not_remote_secrets(tmp_path):
    with SQLiteEventStore(tmp_path / "seven.sqlite") as db:
        setup_living_player_world(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gw = living_player_gateway(db, clock)
        from carlos_sim.actions import NPCActionService
        for who in ("basim", "nora"):
            dec = NPCService(db, clock).decide(
                WORLD, who, command_id=f"decision-{who}",
                expected_revision=db.load(WORLD).revision)
            NPCActionService(db, clock).start(
                WORLD, who, f"action-{who}",
                expected_revision=db.load(WORLD).revision)
        start = db.load(WORLD)
        assert start.actions["action-basim"]["action"] == "work"
        assert start.actions["action-nora"]["action"] == "rest"
        view = gw.inspect().details
        assert {"actor_id": "basim", "activity": "working"} in view["activities"]
        assert not any(x["actor_id"] == "nora" for x in view["activities"])
        secret = json.dumps(player_handoff(gw))
        for distant in ("nora", "huda", "omar", "layla"):
            assert distant not in secret
        # A route costs 40 logical seconds. At the departure endpoint,
        # the player's transit view cannot see Basim or Nora's activities.
        gw.move("square-bakery", command_id="to-bakery",
                expected_revision=start.revision)
        moving = gw.inspect()
        assert moving.status == "traveling"
        assert "activities" not in moving.details
        gw.wait(40, command_id="arrive",
                expected_revision=db.load(WORLD).revision)
        arrived = gw.inspect()
        assert arrived.details["location_id"] == "bakery"
        assert {"actor_id": "nora", "activity": "resting"} in arrived.details["activities"]
        assert not any(x["actor_id"] == "basim" for x in arrived.details["activities"])
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_live_production_is_visible_but_goods_recipe_and_private_npc_data_are_not(tmp_path):
    with SQLiteEventStore(tmp_path / "production.sqlite") as db:
        setup_production(db, routes=True)
        db.append("test", "player-southern-square",
                  db.load("test").revision, [
            DomainEvent("EntityCreated", None, "add local player", 0, {
                "id": "carlos", "name": "Carlos",
                "controller": "player", "location_id": "square",
            }),
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("test")
        gw = PlayerGateway(db, clock, world_id="test", player_id="carlos")
        start_production(db, clock, "basim", "actual-oven")
        assert gw.inspect().details["activities"] == ()
        gw.move("bakery-square", command_id="enter-bakery",
                expected_revision=db.load("test").revision)
        assert "activities" not in gw.inspect().details
        clock.advance("test", seconds=50, command_id="walk-50",
                      expected_revision=db.load("test").revision)
        seen = gw.inspect()
        assert seen.details["activities"] == ({"actor_id": "basim", "activity": "producing"},)
        exposed = json.dumps(player_handoff(gw))
        assert "producing" in exposed
        for private in ('"input_before"', '"output_amount"', '"recipe_id"',
                        '"production_jobs"', '"grain"', '"oven"', '"bread"'):
            assert private not in exposed
        clock.advance("test", seconds=40, command_id="job-due",
                      expected_revision=db.load("test").revision)
        assert gw.inspect().details["activities"] == ()
        assert db.verify("test").to_dict() == db.load("test").to_dict()


def test_player_scene_refuses_fake_world_and_nonplayers(tmp_path):
    with SQLiteEventStore(tmp_path / "wrong-player.sqlite") as db:
        clock, gw = player_in_action_world(db)
        state = db.load("world")
        with pytest.raises(ValueError, match="WorldState"):
            visible_player_activities(state.to_dict(), "carlos")
        for invalid in ("nora", "basim", "missing", None, False):
            with pytest.raises(ValueError, match="player"):
                visible_player_activities(state, invalid)
        assert db.verify("world").to_dict() == state.to_dict()


def test_activity_scene_survives_sqlite_snapshot_and_reopen_without_time_progress(tmp_path):
    path = tmp_path / "reopen.sqlite"
    with SQLiteEventStore(path) as db:
        clock, gw = player_in_action_world(db, fatigue=90)
        begin_action(db, clock, "nora", "pending-rest")
        prior = gw.inspect().details["activities"]
        assert prior == ({"actor_id": "nora", "activity": "resting"},)
        db.snapshot("world")
        saved = db.load("world").to_dict()
        assert db.verify("world").to_dict() == saved
    with SQLiteEventStore(path) as db:
        assert db.load("world").to_dict() == saved
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        assert gw.inspect().details["activities"] == prior
        assert gw.inspect().time == 0
        assert db.verify("world").to_dict() == saved
        clock.advance("world", seconds=120, command_id="rest-finished",
                      expected_revision=db.load("world").revision)
        assert gw.inspect().details["activities"] == ()
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_local_cli_showcases_real_actions_without_changing_scene(tmp_path):
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    # t=1: NPCs start actual action/travel lifecycles, then two identical
    # handoffs must not cause an action, time step or new player memory.
    output = _cli("wait 1\nscene\nhandoff\nscene\nhandoff\nquit\n")
    handoffs = _json_handoffs(output.stdout)
    assert len(handoffs) == 2
    assert handoffs[0] == handoffs[1]
    visible = handoffs[0]["scene"]["details"]["activities"]
    assert handoffs[0]["time"] == 1
    assert handoffs[0]["player_memory"]["observations"] == []
    assert all(set(x) == {"actor_id", "activity"} for x in visible)
    assert all(x["actor_id"] in ("basim", "salma", "adel") for x in visible)
    assert '"npcs"' not in json.dumps(handoffs)
    assert '"injuries"' not in json.dumps(handoffs)


def test_resumable_cli_current_actions_same_after_pause_and_read_only_export(tmp_path):
    from test_play_living_resumable_batch_03 import (
        run_cli, saved_states, backups_list,
    )
    db_path = tmp_path / "real-save.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    new = run_cli("wait 1\nhandoff\nquit\n", db_path, backups, "--new",
                  extra=("--disposable-test",))
    first = saved_states(new.stdout)
    assert len(first) == 1 and first[0]["time"] == 1
    count = len(backups_list(backups))
    assert count == 2  # initialization, one explicit wait
    saved_view = first[0]
    with SQLiteEventStore(db_path) as db:
        frozen = db.verify(WORLD).to_dict()
    resume = run_cli("scene\nhandoff\nhandoff\nquit\n", db_path,
                     backups, "--resume", extra=("--disposable-test",))
    after = saved_states(resume.stdout)
    assert after == [saved_view, saved_view]
    assert len(backups_list(backups)) == count
    with SQLiteEventStore(db_path) as db:
        assert db.verify(WORLD).to_dict() == frozen


def test_foraging_is_visible_only_for_genuine_running_local_actions(tmp_path):
    from carlos_sim import LivingWorldEngine
    from test_gathering_autonomy import make_world
    with SQLiteEventStore(tmp_path / "forage.sqlite") as db:
        make_world(db)
        db.append("r", "carlos-at-grove", db.load("r").revision, [
            DomainEvent("EntityCreated", None, "local player", 0, {
                "id": "carlos", "name": "Carlos",
                "location_id": "grove", "controller": "player",
            })
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("r")
        gw = PlayerGateway(db, clock, world_id="r", player_id="carlos")
        assert gw.inspect().details["activities"] == ()
        result = LivingWorldEngine(db, clock, foraging_enabled=True).advance(
            "r", seconds=1, command_id="actual-forage",
            expected_revision=db.load("r").revision)
        witnessed = gw.inspect().details["activities"]
        assert {x["actor_id"] for x in witnessed
                if x["activity"] == "foraging"} == {
            "adel", "basim", "nora", "salma"}
        assert "omar" not in repr(witnessed)
        assert result.state.resources["grove"]["wild_food"] == 2
        assert '"wild_food"' not in json.dumps(player_handoff(gw))
        assert db.verify("r").to_dict() == result.state.to_dict()
