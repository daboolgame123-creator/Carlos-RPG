"""PLAY-15: voluntary, opt-in NPC-owned food and existing autonomous hunger.

No player hunger meter, hidden NPC needs in narration, food minting or
backwards-incompatible schema/rules edits. All sources disposable.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from carlos_sim import PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from living_player_fixture import (
    WORLD, PLAYER, PEOPLE, living_player_gateway,
    setup_living_foraging_world, setup_living_npc_survival_world,
    is_living_npc_survival_world,
)

SIM = Path(__file__).resolve().parents[1]
CLI = SIM / "scenarios" / "test_village" / "play_living_village.py"


def village(tmp_path, *, survival=True):
    db = SQLiteEventStore(tmp_path / "npc-life.sqlite")
    if survival:
        setup_living_npc_survival_world(db)
    else:
        setup_living_foraging_world(db)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    gateway = living_player_gateway(db, clock, npc_survival_demo=survival)
    return db, clock, gateway


def advance(db, gw, seconds, cid):
    return gw.wait(seconds, command_id=cid,
                   expected_revision=db.load(WORLD).revision)


def test_new_npc_world_is_strict_optin_with_exact_known_stock(tmp_path):
    db, clock, g = village(tmp_path)
    with db:
        old = db.load(WORLD)
        assert old.schema_version == 34
        assert old.rules_version == 46
        assert is_living_npc_survival_world(db)
        with pytest.raises(ValueError, match="bootstrap"):
            living_player_gateway(db, clock)
        assert set(old.npcs) == {row[0] for row in PEOPLE}
        assert all(old.npcs[ident]["needs"]["hunger"] == 80 for ident in old.npcs)
        assert sum(old.resources[n]["food"] for n in old.npcs) == 2
        assert old.resources["basim"]["food"] == 1
        assert old.resources["nora"]["food"] == 1
        for person in ("salma", "adel", "huda", "omar", "layla"):
            assert old.resources[person]["food"] == 0
        assert old.resources[PLAYER]["food"] == 0
        assert old.resources["square"]["wild_food"] == 2
        assert old.resources["woods"]["wild_food"] == 4
        assert g.needs().details["hunger"] == "not_modeled"
        assert g.status().details["profile"]["vitals"]["st"] == {
            "current": 8, "max": 8}
        assert db.verify(WORLD).to_dict() == old.to_dict()


def test_real_npcs_decide_to_eat_their_own_stock_only_after_wait(tmp_path):
    db, clock, g = village(tmp_path)
    with db:
        before = db.load(WORLD).to_dict()
        assert len(db.load(WORLD).consumptions) == 0
        assert db.verify(WORLD).to_dict() == before
        result = advance(db, g, 1, "run-one-second")
        state = db.load(WORLD)
        assert state.time == 1
        assert len(state.consumptions) == 2
        assert {r["npc_id"] for r in state.consumptions.values()} == {
            "basim", "nora"}
        for who in ("basim", "nora"):
            assert state.resources[who]["food"] == 0
            assert state.npcs[who]["needs"]["hunger"] == 55
        for who in ("salma", "adel", "huda", "omar", "layla"):
            assert state.resources[who]["food"] == 0
        assert result.details["nearby_meals"] == (
            {"npc_id": "basim", "activity": "eating", "at": 0},)
        assert "nora" not in json.dumps(result.details)
        assert "hunger" not in json.dumps(result.details)
        assert state.resources[PLAYER]["food"] == 0
        assert state.resources["square"]["wild_food"] == 2
        assert state.resources["woods"]["wild_food"] == 4
        assert len(state.actions) >= 2  # remaining NPCs make independent choices
        assert g.meals().details["total"] == 0
        assert g.needs().details["hunger"] == "not_modeled"
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_survival_tick_affects_only_npc_hunger_not_carlos_health(tmp_path):
    db, clock, g = village(tmp_path)
    with db:
        before = g.status().details
        advance(db, g, 301, "advance-life")
        now = db.load(WORLD)
        # 300 simulation seconds increase hunger by exactly one.
        assert now.time == 301
        # NPC work/rest/investigation may add extra hunger independently
        # of the one-point baseline after 300 simulated seconds.
        assert now.npcs["salma"]["needs"]["hunger"] >= 81
        assert now.npcs["basim"]["needs"]["hunger"] >= 56
        assert now.npcs["nora"]["needs"]["hunger"] >= 56
        assert now.resources[PLAYER]["food"] == 0
        assert g.status().details == before
        assert g.needs().details["hunger"] == "not_modeled"
        assert db.verify(WORLD).to_dict() == now.to_dict()


def test_default_demo_does_not_silently_activate_npc_metabolism(tmp_path):
    db, clock, g = village(tmp_path, survival=False)
    with db:
        before = db.load(WORLD)
        assert not is_living_npc_survival_world(db)
        assert all("food" not in before.resources[n] for n in before.npcs)
        with pytest.raises(ValueError, match="dedicated"):
            living_player_gateway(db, clock, npc_survival_demo=True)
        with pytest.raises(ValueError, match="boolean"):
            living_player_gateway(db, clock, npc_survival_demo="true")
        result = advance(db, g, 1, "old-mode")
        assert "nearby_meals" not in result.details
        after = db.load(WORLD)
        assert not after.consumptions
        assert not after.survival_progress
        assert db.verify(WORLD).to_dict() == after.to_dict()


def test_buying_and_gifting_bread_does_not_magically_create_npc_food(tmp_path):
    db, clock, g = village(tmp_path)
    with db:
        bought = g.buy("salma-bread", 1, 2,
            command_id="buy-loaf", expected_revision=db.load(WORLD).revision)
        assert bought.status == "purchased"
        given = g.give("salma", "bread", 1,
            command_id="give-loaf", expected_revision=db.load(WORLD).revision)
        assert given.status == "gifted"
        stock = db.load(WORLD)
        assert stock.resources["salma"]["bread"] == 3
        assert stock.resources["salma"]["food"] == 0
        assert stock.resources[PLAYER]["bread"] == 0
        advance(db, g, 1, "npc-changes")
        now = db.load(WORLD)
        assert {m["npc_id"] for m in now.consumptions.values()} == {"basim", "nora"}
        assert now.resources["salma"]["bread"] == 3
        assert now.resources["salma"]["food"] == 0
        assert g.gifts().details["total"] == 1
        assert db.verify(WORLD).to_dict() == now.to_dict()


def test_travelling_player_does_not_witness_npc_meal(tmp_path):
    db, clock, g = village(tmp_path)
    with db:
        moved = g.move("square-woods", command_id="leave",
                       expected_revision=db.load(WORLD).revision)
        assert moved.status == "traveling"
        seen = advance(db, g, 1, "npc-eats-while-absent")
        assert "nearby_meals" not in seen.details
        state = db.load(WORLD)
        assert {m["npc_id"] for m in state.consumptions.values()} == {"basim", "nora"}
        assert "nora" not in json.dumps(player_handoff(g))
        assert "hunger" not in json.dumps(g.inspect().details)
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_npc_gateway_cannot_read_human_private_needs(tmp_path):
    db, clock, g = village(tmp_path)
    with db:
        spy = PlayerGateway(db, clock, world_id=WORLD, player_id="nora")
        with pytest.raises(PermissionError):
            spy.needs()
        with pytest.raises(PermissionError):
            spy.supplies()
        assert g.meals().details == {"total": 0, "recent": ()}
        before = db.load(WORLD).to_dict()
        assert db.verify(WORLD).to_dict() == before


def test_npc_survival_world_snapshot_resume_no_wall_clock_or_double_eating(tmp_path):
    path = tmp_path / "resume.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_npc_survival_world,
        disposable_test=True,
    ) as session:
        g = living_player_gateway(session.store, session.clock,
                                  npc_survival_demo=True)
        session.bind_gateway(g)
        assert is_living_npc_survival_world(session.store)
        before = session.store.verify(WORLD).to_dict()
        session.store.snapshot(WORLD)
        paused = session.handoff()
    with ResumableTestSession.resume(path, WORLD, PLAYER,
                                    disposable_test=True) as session:
        g = living_player_gateway(session.store, session.clock,
                                  npc_survival_demo=True)
        session.bind_gateway(g)
        assert is_living_npc_survival_world(session.store)
        assert session.store.verify(WORLD).to_dict() == before
        assert session.handoff() == paused
        advance(session.store, g, 1, "resume-life")
        state = session.store.verify(WORLD)
        assert state.time == 1
        assert len(state.consumptions) == 2
        session.store.snapshot(WORLD)
    with ResumableTestSession.resume(path, WORLD, PLAYER,
                                    disposable_test=True) as session:
        g = living_player_gateway(session.store, session.clock,
                                  npc_survival_demo=True)
        session.bind_gateway(g)
        assert session.store.verify(WORLD).time == 1
        assert len(session.store.verify(WORLD).consumptions) == 2
        advance(session.store, g, 1, "no-more-food")
        assert len(session.store.verify(WORLD).consumptions) == 2


def test_own_food_stock_no_remote_truth_in_handoff(tmp_path):
    db, clock, g = village(tmp_path)
    with db:
        initial = db.verify(WORLD).to_dict()
        view = player_handoff(g)
        assert "nora" not in json.dumps(view)
        assert "food_before" not in json.dumps(view)
        assert "hunger_before" not in json.dumps(view)
        assert "npc_temperaments" not in json.dumps(view)
        assert view["player_needs"]["hunger"] == "not_modeled"
        assert db.verify(WORLD).to_dict() == initial


def test_temporary_cli_optin_shows_only_physical_local_meal():
    env = dict(os.environ, PYTHONPATH=str(SIM / "src"))
    result = subprocess.run(
        [sys.executable, str(CLI), "--npc-survival-demo"],
        input="needs\nwait 1\nscene\nhandoff\nquit\n", text=True,
        capture_output=True, cwd=SIM, env=env, timeout=50, check=True,
    )
    assert "TEST ONLY: independent NPC hunger/food active" in result.stdout
    assert "nearby_meals:" in result.stdout
    assert "basim" in result.stdout
    assert '"hunger": "not_modeled"' in result.stdout
    # Remote consumption and NPC hunger must not appear in the player handoff.
    from test_play_living_village_batch_02 import _json_handoffs
    views = _json_handoffs(result.stdout)
    assert len(views) == 1
    assert "hunger_before" not in json.dumps(views[0])
    assert "food_before" not in json.dumps(views[0])
    assert "nora" not in json.dumps(views[0])


def test_resumable_cli_optin_mode_survives_and_wrong_flag_rejected(tmp_path):
    from test_play_living_resumable_batch_03 import (
        run_cli, saved_states, backups_list,
    )
    path, backups = tmp_path / "world.sqlite", tmp_path / "backups"
    backups.mkdir()
    extra = ("--disposable-test", "--npc-survival-demo")
    initial = run_cli(
        "id tick1 wait 1\nhandoff\nquit\n",
        path, backups, "--new", extra=extra,
    )
    assert "nearby_meals:" in initial.stdout
    view = saved_states(initial.stdout)
    assert len(view) == 1
    assert view[0]["time"] == 1
    assert view[0]["player_needs"]["hunger"] == "not_modeled"
    checkpoints = backups_list(backups)
    assert len(checkpoints) == 2
    mismatch = run_cli(
        "handoff\nquit\n", path, backups, "--resume",
        extra=("--disposable-test",), ok=False,
    )
    assert "NPC survival mode mismatch" in mismatch.stderr
    assert backups_list(backups) == checkpoints
    correct = run_cli(
        "handoff\nquit\n", path, backups, "--resume", extra=extra,
    )
    assert saved_states(correct.stdout) == view
    assert backups_list(backups) == checkpoints


def test_resumable_default_world_rejects_optin_flag(tmp_path):
    from test_play_living_resumable_batch_03 import run_cli, backups_list
    path, backups = tmp_path / "normal.sqlite", tmp_path / "backups"
    backups.mkdir()
    initial = run_cli("handoff\nquit\n", path, backups,
                      "--new", extra=("--disposable-test",))
    checkpoints = backups_list(backups)
    assert len(checkpoints) == 1
    mismatch = run_cli(
        "quit\n", path, backups, "--resume",
        extra=("--disposable-test", "--npc-survival-demo"), ok=False,
    )
    assert "NPC survival mode mismatch" in mismatch.stderr
    assert backups_list(backups) == checkpoints
