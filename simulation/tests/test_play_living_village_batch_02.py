"""PLAY-02 disposable living-village character, world and CLI acceptance.

The living world may act without Carlos issuing NPC commands; it never
chooses Carlos's actions or reveals the private reasons/needs of other NPCs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.player_handoff import player_handoff

SIM = Path(__file__).resolve().parents[1]
DEMO = SIM / "scenarios" / "test_village"
sys.path.insert(0, str(DEMO))
from living_player_fixture import (  # noqa: E402
    WORLD, PLAYER, PEOPLE, living_player_gateway, setup_living_player_world,
)


def _new(tmp_path):
    db = SQLiteEventStore(tmp_path / "living.sqlite")
    setup_living_player_world(db)
    clock = TimeEngine(db)
    clock.open_session(WORLD)
    return db, clock, living_player_gateway(db, clock)


def _cli(commands: str):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SIM / "src")
    return subprocess.run(
        [sys.executable, str(DEMO / "play_living_village.py")],
        input=commands, capture_output=True, text=True, cwd=SIM, env=env,
        timeout=50, check=True,
    )


def _json_handoffs(text: str):
    prefix = '{"canonical_story":'
    return [json.loads(s[s.index(prefix):]) for s in text.splitlines()
            if prefix in s]


def test_trusted_fixture_contains_seven_independent_npcs_and_no_free_wealth(tmp_path):
    db, clock, gw = _new(tmp_path)
    with db:
        state = db.load(WORLD)
        assert len(state.npcs) == 7
        assert set(state.npcs) == {row[0] for row in PEOPLE}
        assert PLAYER not in state.npcs
        assert state.entities[PLAYER]["controller"] == "player"
        assert {x["location_id"] for x in state.entities.values()} == {
            "square", "bakery", "woods"}
        assert set(state.routes) == {"square-bakery", "square-woods"}
        assert all(set(state.resources[npc]) == {
            "labor_units", "investigation_attempts"} for npc in state.npcs)
        assert all(state.resources[npc]["labor_units"] == 0
                   and state.resources[npc]["investigation_attempts"] == 0
                   for npc in state.npcs)
        assert not state.social_messages and not state.injuries
        assert not state.travels and not state.actions
        before = state.to_dict()
        start = player_handoff(gw)
        assert {row["id"] for row in start["scene"]["details"]["occupants"]} == {
            "carlos", "basim", "salma", "adel"}
        for distant in ("nora", "huda", "omar", "layla"):
            assert distant not in json.dumps(start)
        assert start["canonical_story"] is False
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before


def test_autonomous_npcs_work_rest_and_explore_only_when_player_waits(tmp_path):
    db, clock, gw = _new(tmp_path)
    with db:
        initial = db.load(WORLD)
        assert gw.inspect().time == 0
        assert db.load(WORLD).to_dict() == initial.to_dict()
        elapsed = gw.wait(
            180, command_id="advance-life", expected_revision=initial.revision)
        assert elapsed.time == 180
        state = db.load(WORLD)
        assert state.entities[PLAYER]["location_id"] == "square"
        assert PLAYER not in state.npcs
        assert len(state.actions) >= 2
        assert len({a["npc_id"] for a in state.actions.values()}) >= 2
        assert any(a["status"] == "completed" for a in state.actions.values())
        assert state.revision > initial.revision
        assert db.verify(WORLD).to_dict() == state.to_dict()
        assert gw.inspect().time == 180
        assert db.load(WORLD).to_dict() == state.to_dict()


def test_player_travel_happens_in_time_and_never_teleports_npcs(tmp_path):
    db, clock, gw = _new(tmp_path)
    with db:
        before = db.load(WORLD)
        gw.move("square-bakery", command_id="road-bakery",
                expected_revision=before.revision)
        departure = db.load(WORLD)
        assert departure.entities[PLAYER]["location_id"] == "square"
        assert gw.inspect().status == "traveling"
        with pytest.raises(ValueError, match="travelling"):
            gw.interact("nora", kind="greeting", text="Hello",
                        command_id="remote-while-travelling",
                        expected_revision=departure.revision)
        assert db.load(WORLD).to_dict() == departure.to_dict()
        gw.wait(39, command_id="almost-bakery",
                expected_revision=departure.revision)
        assert gw.inspect().status == "traveling"
        assert gw.inspect().details["remaining_seconds"] == 1
        gw.wait(1, command_id="arrive-bakery",
                expected_revision=db.load(WORLD).revision)
        arrived = db.load(WORLD)
        assert arrived.time == 40
        assert arrived.entities[PLAYER]["location_id"] == "bakery"
        assert gw.inspect().status == "present"
        assert db.verify(WORLD).to_dict() == arrived.to_dict()


def test_forbidden_remote_talk_cannot_change_world_and_handoff_is_private(tmp_path):
    db, clock, gw = _new(tmp_path)
    with db:
        before = db.load(WORLD)
        with pytest.raises(InvalidEvent):
            gw.interact("huda", kind="greeting", text="Hello",
                        command_id="remote-greeting",
                        expected_revision=before.revision)
        assert db.load(WORLD).to_dict() == before.to_dict()
        view = player_handoff(gw)
        public = json.dumps(view)
        for secret in ('"npcs"', '"needs"', '"goals"', '"beliefs"',
                       '"resources"', '"injuries"', '"relations"'):
            assert secret not in public
        assert gw.recall().details["observations"] == ()
        gw.observe(command_id="look-around", expected_revision=before.revision)
        after = player_handoff(gw)
        assert after["player_memory"]["observations"]
        for distant in ("nora", "huda", "omar", "layla"):
            assert distant not in json.dumps(after)
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()


def test_world_snapshot_restore_preserves_npc_autonomy_not_player_input(tmp_path):
    path = tmp_path / "restore.sqlite"
    with SQLiteEventStore(path) as db:
        setup_living_player_world(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gw = living_player_gateway(db, clock)
        gw.wait(150, command_id="one-advance",
                expected_revision=db.load(WORLD).revision)
        gw.observe(command_id="player-witness",
                   expected_revision=db.load(WORLD).revision)
        frozen = player_handoff(gw)
        db.snapshot(WORLD)
        saved = db.load(WORLD).to_dict()
        assert db.verify(WORLD).to_dict() == saved
        clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        restored = db.load(WORLD)
        assert restored.to_dict() == saved
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gw = living_player_gateway(db, clock)
        assert player_handoff(gw) == frozen
        assert db.verify(WORLD).to_dict() == saved
        with pytest.raises(RevisionConflict):
            gw.wait(10, command_id="stale",
                    expected_revision=restored.revision - 1)
        assert db.load(WORLD).to_dict() == saved
        gw.wait(90, command_id="resume-life",
                expected_revision=restored.revision)
        after = db.load(WORLD)
        assert after.time == 240
        assert after.entities[PLAYER]["location_id"] == "square"
        assert db.verify(WORLD).to_dict() == after.to_dict()


def test_seven_npc_world_deterministic_across_two_fresh_sqlite_files(tmp_path):
    results = []
    for name in ("first", "second"):
        path = tmp_path / name
        path.mkdir()
        db, clock, gw = _new(path)
        with db:
            gw.wait(180, command_id="same-choice",
                    expected_revision=db.load(WORLD).revision)
            results.append(db.verify(WORLD).to_dict())
    assert results[0] == results[1]


def test_real_living_cli_showcases_independent_npcs_and_safe_handoff():
    output = _cli("scene\nhandoff\nlook\nhandoff\n"
                  "talk basim greeting Hello\nwait 180\nscene\nhandoff\nquit\n").stdout
    exports = _json_handoffs(output)
    assert len(exports) == 3
    initial, witnessed, later = exports
    assert initial["time"] == 0
    assert initial["revision"] + 1 == witnessed["revision"]
    assert witnessed["player_memory"]["observations"]
    assert later["time"] == 180
    assert later["revision"] > witnessed["revision"]
    assert all(row["canonical_story"] is False for row in exports)
    assert "Temporary world discarded" in output
