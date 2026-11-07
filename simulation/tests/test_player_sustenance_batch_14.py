"""PLAY-14 verified player sustenance evidence, without inventing a hunger meter."""
from __future__ import annotations

import pytest

from carlos_sim import PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from living_player_fixture import (
    WORLD, PLAYER, setup_living_foraging_world, setup_living_player_world,
    living_player_gateway,
)
from test_player_foraging_batch_11 import demo


def test_empty_history_is_unknown_not_full_or_starving(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        result = gateway.needs()
        assert result.status == "needs"
        assert result.details == {
            "hunger": "not_modeled",
            "physical_energy": "not_modeled",
            "rpg_stamina_link": "not_established",
            "last_meal": None,
            "seconds_since_last_meal": None,
            "owned_edible": {"food": 0, "bread": 0},
        }
        assert player_handoff(gateway)["player_needs"] == result.details
        assert db.verify(WORLD).to_dict() == before


def test_meal_time_and_elapsed_are_actual_simulated_seconds(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        gateway.buy("salma-bread", 1, 2, command_id="buy",
                    expected_revision=db.load(WORLD).revision)
        eaten = gateway.eat("bread", command_id="meal",
                            expected_revision=db.load(WORLD).revision)
        assert eaten.status == "ate"
        at_zero = gateway.needs().details
        assert at_zero["last_meal"] == {"resource": "bread", "consumed_at": 0}
        assert at_zero["seconds_since_last_meal"] == 0
        assert at_zero["owned_edible"] == {"food": 0, "bread": 0}
        gateway.wait(65, command_id="elapsed",
                     expected_revision=db.load(WORLD).revision)
        now = gateway.needs().details
        assert now["seconds_since_last_meal"] == 65
        assert now["last_meal"] == at_zero["last_meal"]
        assert now["hunger"] == "not_modeled"
        assert now["physical_energy"] == "not_modeled"
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_more_recent_meal_resets_elapsed_only_from_real_event(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        gateway.buy("salma-bread", 2, 2, command_id="buy",
                    expected_revision=db.load(WORLD).revision)
        gateway.eat("bread", command_id="first",
                    expected_revision=db.load(WORLD).revision)
        gateway.wait(130, command_id="time",
                     expected_revision=db.load(WORLD).revision)
        assert gateway.needs().details["seconds_since_last_meal"] == 130
        gateway.eat("bread", command_id="second",
                    expected_revision=db.load(WORLD).revision)
        assert gateway.needs().details["seconds_since_last_meal"] == 0
        assert gateway.needs().details["last_meal"] == {
            "resource": "bread", "consumed_at": 130}
        assert gateway.meals().details["total"] == 2


def test_no_meal_after_very_long_wait_remains_unknown(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        gateway.wait(300, command_id="long-wait",
                     expected_revision=db.load(WORLD).revision)
        result = gateway.needs()
        assert result.details["seconds_since_last_meal"] is None
        assert result.details["hunger"] == "not_modeled"
        assert result.details["physical_energy"] == "not_modeled"
        assert gateway.status().details["profile"]["vitals"]["st"] == {
            "current": 8, "max": 8}
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_missing_balances_remain_unknown_not_fabricated_zero(tmp_path):
    with SQLiteEventStore(tmp_path / "plain.sqlite") as db:
        setup_living_player_world(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gateway = living_player_gateway(db, clock)
        before = db.load(WORLD).to_dict()
        needs = gateway.needs().details
        assert needs["owned_edible"] == {"food": None, "bread": None}
        assert needs["last_meal"] is None
        assert db.verify(WORLD).to_dict() == before


def test_npc_may_not_read_player_needs_through_own_gateway(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        faker = PlayerGateway(db, clock, world_id=WORLD, player_id="basim")
        with pytest.raises(PermissionError):
            faker.needs()
        assert "basim" not in str(gateway.needs().details)
        assert "nora" not in str(gateway.needs().details)
        assert "huda" not in str(gateway.needs().details)


def test_handoff_version_coherent_and_readonly(tmp_path):
    db, clock, gateway = demo(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        handoff = player_handoff(gateway)
        assert handoff["player_needs"] == gateway.needs().details
        assert handoff["revision"] == db.load(WORLD).revision
        assert handoff["time"] == db.load(WORLD).time
        assert handoff["player_status"]["details"]["profile"]["vitals"]["st"] == {
            "current": 8, "max": 8}
        assert db.verify(WORLD).to_dict() == before


def test_snapshot_reopen_persists_actual_meal_time_not_wall_clock(tmp_path):
    path = tmp_path / "sustenance.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_foraging_world, disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        g = session.gateway
        g.buy("salma-bread", 1, 2, command_id="buy",
              expected_revision=session.store.load(WORLD).revision)
        g.wait(60, command_id="wait",
               expected_revision=session.store.load(WORLD).revision)
        g.eat("bread", command_id="meal",
              expected_revision=session.store.load(WORLD).revision)
        g.wait(30, command_id="wait-again",
               expected_revision=session.store.load(WORLD).revision)
        before = session.handoff()
        assert before["player_needs"]["seconds_since_last_meal"] == 30
        state = session.store.verify(WORLD).to_dict()
        session.store.snapshot(WORLD)
    with ResumableTestSession.resume(path, WORLD, PLAYER, disposable_test=True) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.handoff() == before
        assert session.gateway.needs().details["seconds_since_last_meal"] == 30
        assert session.store.verify(WORLD).to_dict() == state


def test_temporary_cli_needs_reading_and_handoff():
    from test_play_living_village_batch_02 import _cli, _json_handoffs
    output = _cli(
        "needs\nbuy salma-bread 1 2\neat bread\nwait 70\nneeds\nhandoff\nquit\n"
    ).stdout
    assert "seconds_since_last_meal: 70" in output
    handoffs = _json_handoffs(output)
    assert len(handoffs) == 1
    assert handoffs[0]["player_needs"]["seconds_since_last_meal"] == 70
    assert handoffs[0]["player_needs"]["physical_energy"] == "not_modeled"


def test_resumable_cli_needs_uses_saved_sim_clock(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, saved_states, backups_list
    file, backups = tmp_path / "living.sqlite", tmp_path / "backups"
    backups.mkdir()
    first = run_cli(
        "id buy1 buy salma-bread 1 2\nid eat1 eat bread\n"
        "id wait1 wait 40\nneeds\nhandoff\nquit\n",
        file, backups, "--new", extra=("--disposable-test",),
    )
    views = saved_states(first.stdout)
    assert views[0]["player_needs"]["seconds_since_last_meal"] == 40
    n = len(backups_list(backups))
    second = run_cli(
        "needs\nhandoff\nquit\n",
        file, backups, "--resume", extra=("--disposable-test",),
    )
    assert saved_states(second.stdout) == views
    assert len(backups_list(backups)) == n
