"""PLAY-01: player-only narrated handoff in disposable local play.

These tests deliberately verify NPC knowledge separation and state fidelity.
No network boundary, canonical-story state or production approval is implied.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, PlayerGateway, TimeEngine
from carlos_sim.player_gateway import PlayerCommandResult
from carlos_sim.player_handoff import player_handoff
from carlos_sim.resumable_play import ResumableTestSession
from test_player_gateway import setup_player_demo_world


SIMULATION = Path(__file__).resolve().parents[1]
DEMO_DIR = SIMULATION / "scenarios" / "test_village"


def _cli(script: str, *, commands: str, argv: tuple[str, ...] = ()):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SIMULATION / "src")
    return subprocess.run(
        [sys.executable, str(DEMO_DIR / script), *argv], input=commands,
        text=True, capture_output=True, cwd=SIMULATION, env=env, timeout=35,
        check=True,
    )


def _envelopes(stdout: str) -> list[dict]:
    # input("carlos> ") prints a prompt on the *same line* as the JSON.
    prefix = '{"canonical_story":'
    return [json.loads(line[line.index(prefix):])
            for line in stdout.splitlines() if prefix in line]


def test_player_handoff_hides_private_npc_state_and_never_writes(tmp_path):
    with SQLiteEventStore(tmp_path / "player-view.sqlite") as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        before = db.load("world").to_dict()
        with db.db:
            old_rows = db.db.execute(
                "SELECT COUNT(*) FROM events WHERE world_id=?", ("world",)
            ).fetchone()[0]
        view = player_handoff(gw)
        assert view["format"] == "carlos-player-handoff-v1"
        assert view["disposable_test"] is True
        assert view["canonical_story"] is False
        assert view["revision"] == before["revision"]
        assert view["scene"]["status"] == "present"
        assert {x["id"] for x in view["scene"]["details"]["occupants"]} == {
            "carlos", "nora", "basim"}
        encoded = json.dumps(view, ensure_ascii=False)
        for secret in ("npcs", "relations", "social_messages",
                       "injuries", "beliefs", "resource_balances", "sara"):
            assert f'"{secret}"' not in encoded
        assert db.load("world").to_dict() == before
        assert db.db.execute(
            "SELECT COUNT(*) FROM events WHERE world_id=?", ("world",)
        ).fetchone()[0] == old_rows
        gw.move("road", command_id="toward-sara",
                expected_revision=db.load("world").revision)
        underway = player_handoff(gw)
        assert underway["scene"]["status"] == "traveling"
        assert "forest" not in json.dumps(underway["scene"])
        gw.wait(90, command_id="arrival",
                expected_revision=db.load("world").revision)
        arrived = player_handoff(gw)
        assert arrived["scene"]["details"]["location_id"] == "forest"
        assert {x["id"] for x in arrived["scene"]["details"]["occupants"]} == {
            "carlos", "sara"}
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_handoff_refuses_cross_revision_composition(tmp_path, monkeypatch):
    with SQLiteEventStore(tmp_path / "inconsistent.sqlite") as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        original = gw.recall

        def stale_projection():
            p = original()
            return PlayerCommandResult(p.world_id, p.time, p.revision + 1,
                                       p.status, p.details)

        monkeypatch.setattr(gw, "recall", stale_projection)
        before = db.load("world").to_dict()
        with pytest.raises(RuntimeError, match="changed"):
            player_handoff(gw)
        assert db.load("world").to_dict() == before
        assert db.verify("world").to_dict() == before


def test_resumable_handoff_survives_sqlite_reopen_without_mutation(tmp_path):
    filename = tmp_path / "checkpointed-world.sqlite"
    with ResumableTestSession.create(
        filename, "world", "carlos", setup_player_demo_world,
        disposable_test=True
    ) as session:
        start = session.handoff()
        old = session.store.load("world").to_dict()
        assert session.handoff() == start
        assert session.store.load("world").to_dict() == old
        session.gateway.observe(command_id="carlos-witnesses",
                                expected_revision=old["revision"])
        remembered = session.handoff()
        assert remembered["revision"] > start["revision"]
        assert remembered["player_memory"]["observations"]
        session.store.snapshot("world")
        committed = session.store.load("world").to_dict()
        assert session.store.verify("world").to_dict() == committed

    with ResumableTestSession.resume(
        filename, "world", "carlos", disposable_test=True
    ) as session:
        assert session.handoff() == remembered
        assert session.store.load("world").to_dict() == committed
        assert session.store.verify("world").to_dict() == committed


def test_local_cli_handoff_does_not_move_player_or_reveal_remote_nora():
    out = _cli("play_local.py",
               commands="scene\nhandoff\nlook\nhandoff\nmove square-woods\n"
                        "wait 50\nscene\nhandoff\nquit\n").stdout
    views = _envelopes(out)
    assert len(views) == 3
    first, looked, traveled = views
    assert first["scene"]["details"]["location_id"] == "square"
    assert first["revision"] + 1 == looked["revision"]
    assert looked["player_memory"]["observations"]
    assert traveled["scene"]["details"]["location_id"] == "woods"
    assert {x["id"] for x in traveled["scene"]["details"]["occupants"]} == {
        "carlos", "nora"}
    assert "nora" not in json.dumps(first)
    assert all(v["canonical_story"] is False for v in views)


def test_resumable_cli_handoff_and_scene_do_not_create_extra_checkpoints(tmp_path):
    filename = tmp_path / "test.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    params = ("--db", str(filename), "--backups", str(backups),
              "--code-commit", "a" * 40, "--disposable-test")
    new = _cli("play_resumable_demo.py",
               commands="scene\nhandoff\nlook\nhandoff\nquit\n",
               argv=(*params, "--new"))
    views = _envelopes(new.stdout)
    assert len(views) == 2
    assert views[0]["revision"] + 1 == views[1]["revision"]
    assert views[1]["player_memory"]["observations"]
    assert len(list(backups.glob("test-carlos-rev-*"))) == 2
    resumed = _cli("play_resumable_demo.py",
                   commands="scene\nhandoff\nquit\n",
                   argv=(*params, "--resume"))
    assert _envelopes(resumed.stdout) == [views[1]]
    assert len(list(backups.glob("test-carlos-rev-*"))) == 2
    with ResumableTestSession.resume(
        filename, "demo", "carlos", disposable_test=True
    ) as session:
        assert session.store.verify("demo").to_dict() == session.store.load("demo").to_dict()
        assert json.loads(json.dumps(session.handoff())) == views[1]


def test_player_handoff_never_exposes_noras_private_injury_even_after_look(tmp_path):
    with SQLiteEventStore(tmp_path / "private-injury.sqlite") as db:
        setup_player_demo_world(db)
        initial = db.load("world")
        db.append("world", "nora-injury-test", initial.revision, [
            DomainEvent("InjuryRecorded", None, "trusted private fixture", 0, {
                "injury_id": "nora-confidential-wound",
                "subject_id": "nora",
                "severity": 77,
                "source": "trusted_test_bootstrap",
            }),
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session("world")
        gw = PlayerGateway(db, clock, world_id="world", player_id="carlos")
        before = db.load("world").to_dict()
        for view in (player_handoff(gw),):
            public = json.dumps(view)
            assert "nora-confidential-wound" not in public
            assert '"injuries"' not in public
            assert '"severity"' not in public
        assert db.load("world").to_dict() == before
        gw.observe(command_id="carlos-looks-at-nora",
                   expected_revision=before["revision"])
        after = json.dumps(player_handoff(gw))
        assert "nora-confidential-wound" not in after
        assert '"severity"' not in after
        assert "nora" in after  # identity is visible, private diagnosis is not
        assert db.verify("world").to_dict() == db.load("world").to_dict()


def test_player_handoff_denies_raw_world_state_as_input(tmp_path):
    with SQLiteEventStore(tmp_path / "reject-raw.sqlite") as db:
        setup_player_demo_world(db)
        before = db.load("world")
        with pytest.raises(TypeError, match="PlayerGateway"):
            player_handoff(before)
        with pytest.raises(TypeError, match="PlayerGateway"):
            player_handoff(before.to_dict())
        assert db.verify("world").to_dict() == before.to_dict()
