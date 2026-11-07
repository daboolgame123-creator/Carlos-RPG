"""PLAY-14: honest needs evidence without inventing physiological rules."""
from __future__ import annotations

import json
import pytest

from carlos_sim import SQLiteEventStore, TimeEngine, PlayerGateway
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION
from carlos_sim.player_handoff import player_handoff
from carlos_sim.player_needs_evidence import personal_needs_evidence
from carlos_sim.resumable_play import ResumableTestSession
from test_player_foraging_batch_11 import demo, take
from living_player_fixture import (
    WORLD, PLAYER, setup_living_foraging_world, setup_living_player_world,
    living_player_gateway,
)


def buy_and_eat(db, gateway, name="first"):
    gateway.buy("salma-bread", 1, 2, command_id="buy-" + name,
                expected_revision=db.load(WORLD).revision)
    return gateway.eat("bread", command_id="eat-" + name,
                       expected_revision=db.load(WORLD).revision)


def test_no_persistence_version_bump_for_readonly_projection():
    assert (SCHEMA_VERSION, RULES_VERSION) == (34, 46)


def test_no_food_history_never_invents_player_hunger(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        initial = db.load(WORLD).to_dict()
        result = gateway.needs()
        assert result.status == "needs_evidence"
        assert result.details == {
            "hunger": {
                "mode": "not_modeled",
                "last_verified_meal_at": None,
                "seconds_since_last_verified_meal": None},
            "energy": {"mode": "rpg_st_only", "st": {"current": 8, "max": 8}},
            "activity": "available",
        }
        assert player_handoff(gateway)["player_needs_evidence"] == result.details
        assert db.verify(WORLD).to_dict() == initial


def test_bought_and_verified_meal_reset_only_elapsed_time(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        status = gateway.status().details
        buy_and_eat(db, gateway)
        now = gateway.needs().details
        assert now["hunger"] == {
            "mode": "not_modeled",
            "last_verified_meal_at": 0,
            "seconds_since_last_verified_meal": 0,
        }
        assert now["energy"]["st"] == {"current": 8, "max": 8}
        assert gateway.status().details == status
        assert gateway.meals().details["total"] == 1
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_elapsed_time_is_world_time_not_wall_clock(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        buy_and_eat(db, gateway)
        frozen = gateway.needs()
        assert frozen.details["hunger"]["seconds_since_last_verified_meal"] == 0
        assert gateway.needs().details == frozen.details
        gateway.wait(299, command_id="elapsed",
                     expected_revision=db.load(WORLD).revision)
        now = gateway.needs()
        assert now.time == 299
        assert now.details["hunger"]["seconds_since_last_verified_meal"] == 299
        assert now.details["hunger"]["mode"] == "not_modeled"
        assert now.details["energy"]["st"] == frozen.details["energy"]["st"]
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_second_meal_restarts_timer_only_after_actual_consumption(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        # Buy both units while Salma is physically present at t=0.
        # She is autonomous and may leave the market before t=70.
        gateway.buy("salma-bread", 2, 2, command_id="buy-two",
                    expected_revision=db.load(WORLD).revision)
        assert gateway.meals().details["total"] == 0
        gateway.eat("bread", command_id="eat-a",
                    expected_revision=db.load(WORLD).revision)
        gateway.wait(70, command_id="advance",
                     expected_revision=db.load(WORLD).revision)
        previous = gateway.needs()
        assert previous.details["hunger"]["seconds_since_last_verified_meal"] == 70
        # Possessing a second bought loaf doesn't imply it was eaten.
        assert gateway.supplies().details["balances"]["bread"] == 1
        assert gateway.meals().details["total"] == 1
        gateway.eat("bread", command_id="eat-b",
                    expected_revision=db.load(WORLD).revision)
        now = gateway.needs()
        assert now.details["hunger"]["last_verified_meal_at"] == 70
        assert now.details["hunger"]["seconds_since_last_verified_meal"] == 0
        assert gateway.meals().details["total"] == 2


def test_forage_wait_and_activity_not_implied_hunger(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        assert gateway.needs().details["activity"] == "available"
        take(db, gateway, "gather")
        assert gateway.needs().details["activity"] == "foraging"
        gateway.wait(20, command_id="partial",
                     expected_revision=db.load(WORLD).revision)
        result = gateway.needs()
        assert result.details["activity"] == "foraging"
        assert result.details["hunger"]["seconds_since_last_verified_meal"] is None
        gateway.wait(40, command_id="finish",
                     expected_revision=db.load(WORLD).revision)
        assert gateway.needs().details["activity"] == "available"
        assert gateway.supplies().details["balances"]["food"] == 1
        assert gateway.needs().details["hunger"]["last_verified_meal_at"] is None


def test_travel_activity_observable_but_no_exhaustion_assumption(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        gateway.move("square-woods", command_id="depart",
                     expected_revision=db.load(WORLD).revision)
        assert gateway.needs().details["activity"] == "traveling"
        assert gateway.needs().details["energy"]["st"] == {"current": 8, "max": 8}
        gateway.wait(50, command_id="arrive",
                     expected_revision=db.load(WORLD).revision)
        assert gateway.needs().details["activity"] == "available"
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_preexisting_noncanonical_player_profile_unknown_safe(tmp_path):
    db = SQLiteEventStore(tmp_path / "plain.sqlite")
    with db:
        setup_living_player_world(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gateway = living_player_gateway(db, clock)
        result = gateway.needs()
        assert result.details["hunger"]["mode"] == "not_modeled"
        assert result.details["hunger"]["last_verified_meal_at"] is None
        assert "npc" not in json.dumps(result.details)
        assert result.details["energy"]["st"] == {"current": 8, "max": 8}


def test_player_identity_boundary_prevents_npc_projection(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        fake = PlayerGateway(db, clock, world_id=WORLD, player_id="nora")
        with pytest.raises(PermissionError):
            fake.needs()
        with pytest.raises(PermissionError):
            personal_needs_evidence(db.load(WORLD), "basim",
                {"total": 0, "recent": ()})
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


@pytest.mark.parametrize("record", [
    {}, {"total": 0, "recent": [1]}, {"total": -1, "recent": ()},
    {"total": True, "recent": ()}, {"total": 1, "recent": ()},
    {"total": 0, "recent": ({"consumed_at": 0},)},
    {"total": 1, "recent": ({"consumed_at": -1},)},
    {"total": 1, "recent": ({"consumed_at": 500},)},
])
def test_private_evidence_helper_rejects_unsupported_records(tmp_path, record):
    db, clock, gateway = demo(tmp_path)
    with db:
        with pytest.raises((TypeError, ValueError)):
            personal_needs_evidence(db.load(WORLD), PLAYER, record)


def test_snapshot_and_restart_dont_fabricate_elapsed_time(tmp_path):
    path = tmp_path / "meals.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_foraging_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        buy_and_eat(session.store, session.gateway)
        session.gateway.wait(35, command_id="advance",
                             expected_revision=session.store.load(WORLD).revision)
        original = session.gateway.needs().details
        view = session.handoff()
        initial = session.store.verify(WORLD).to_dict()
        session.store.snapshot(WORLD)
    with ResumableTestSession.resume(path, WORLD, PLAYER, disposable_test=True) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.gateway.needs().details == original
        assert session.handoff() == view
        assert session.store.verify(WORLD).to_dict() == initial
        session.gateway.wait(15, command_id="resume-advance",
                             expected_revision=session.store.load(WORLD).revision)
        assert session.gateway.needs().details["hunger"]["seconds_since_last_verified_meal"] == 50


def test_full_seven_npc_world_progresses_without_autonomous_player_hunger(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        buy_and_eat(db, gateway)
        status = gateway.status().details
        gateway.wait(180, command_id="independent-life",
                     expected_revision=db.load(WORLD).revision)
        state = db.load(WORLD)
        assert len({row["npc_id"] for row in state.actions.values()}) >= 2
        assert gateway.needs().details["hunger"]["mode"] == "not_modeled"
        assert gateway.needs().details["hunger"]["seconds_since_last_verified_meal"] == 180
        assert gateway.status().details == status
        assert PLAYER not in state.npcs
        assert "basim" in state.npcs and "salma" in state.npcs and "nora" in state.npcs
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_temporary_cli_renders_evidence_and_handoff():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    output = _cli("needs\nbuy salma-bread 1 2\neat bread\n"
                  "wait 40\nneeds\nhandoff\nquit\n").stdout
    assert "needs_evidence" in output
    assert "seconds_since_last_verified_meal" in output
    views = _json_handoffs(output)
    assert len(views) == 1
    assert views[0]["player_needs_evidence"]["hunger"]["seconds_since_last_verified_meal"] == 40
    assert views[0]["player_needs_evidence"]["energy"]["st"] == {
        "current": 8, "max": 8}


def test_resumable_cli_read_only_needs_does_not_create_checkpoint(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    dbfile, backups = tmp_path / "world.sqlite", tmp_path / "checkpoints"
    backups.mkdir()
    first = run_cli("id buy1 buy salma-bread 1 2\nid eat1 eat bread\n"
                    "needs\nhandoff\nquit\n",
                    dbfile, backups, "--new", extra=("--disposable-test",))
    views = saved_states(first.stdout)
    assert views[0]["player_needs_evidence"]["hunger"]["seconds_since_last_verified_meal"] == 0
    num = len(backups_list(backups))
    again = run_cli("needs\nhandoff\nquit\n",
                    dbfile, backups, "--resume", extra=("--disposable-test",))
    assert saved_states(again.stdout) == views
    assert len(backups_list(backups)) == num
