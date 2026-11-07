"""PLAY-03: real CLI resume, seven independent NPCs, replay and fail-closed P0.

No production save or canonical Carlos story is created by these tests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from carlos_sim import PlayerGateway, SQLiteEventStore, TimeEngine
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.player_handoff import player_handoff
from carlos_sim.store import DuplicateCommand, RevisionConflict
from carlos_sim.backup import verify_backup_bundle
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION

SIM = Path(__file__).resolve().parents[1]
DEMOS = SIM / "scenarios" / "test_village"
sys.path.insert(0, str(DEMOS))
from living_player_fixture import (  # noqa: E402
    WORLD, PLAYER, PEOPLE, living_player_gateway, setup_living_player_world,
)

SOURCE_SHA = "a" * 40


def run_cli(commands: str, db: Path, backups: Path, mode: str, *,
            sha: str = SOURCE_SHA, extra: tuple[str, ...] = (),
            ok: bool = True):
    env = dict(os.environ, PYTHONPATH=str(SIM / "src"))
    result = subprocess.run(
        [sys.executable, str(DEMOS / "play_living_resumable.py"),
         "--db", str(db), "--backups", str(backups),
         "--code-commit", sha, mode, *extra],
        input=commands, text=True, capture_output=True,
        cwd=SIM, env=env, timeout=70)
    if ok:
        assert result.returncode == 0, (result.stdout, result.stderr)
    else:
        assert result.returncode != 0
    return result


def saved_states(out: str) -> list[dict]:
    marker = '{"canonical_story":'
    return [json.loads(line[line.index(marker):])
            for line in out.splitlines() if marker in line]


def backups_list(folder: Path):
    return sorted(folder.glob("living-test-rev-*"))


def test_exact_session_gateway_binding_rejects_wrong_objects_without_writes(tmp_path):
    path = tmp_path / "bound.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_player_world, disposable_test=True
    ) as session:
        before = session.store.load(WORLD).to_dict()
        valid = living_player_gateway(session.store, session.clock)
        session.bind_gateway(valid)
        assert session.gateway is valid
        assert session.handoff() == player_handoff(valid)
        from carlos_sim.player_gateway import PlayerCommandResult
        for invalid in (
            object(),
            session.store.load(WORLD),
            PlayerGateway(session.store, session.clock,
                          world_id=WORLD, player_id="nora"),
            PlayerGateway(session.store, session.clock,
                          world_id="other-world", player_id=PLAYER),
        ):
            with pytest.raises(ValueError, match="exact player test session"):
                session.bind_gateway(invalid)
            assert session.gateway is valid
        with SQLiteEventStore(tmp_path / "other.sqlite") as alien_store:
            other_clock = TimeEngine(alien_store)
            forged = PlayerGateway(alien_store, other_clock,
                                   world_id=WORLD, player_id=PLAYER)
            with pytest.raises(ValueError, match="exact player test session"):
                session.bind_gateway(forged)
        assert session.store.load(WORLD).to_dict() == before
        assert session.store.verify(WORLD).to_dict() == before
    with pytest.raises(PermissionError, match="closed"):
        session.bind_gateway(valid)


def test_seven_npcs_continue_independent_schedules_after_reopen(tmp_path):
    path = tmp_path / "npc-continuation.sqlite"
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_player_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        initial = session.store.load(WORLD)
        session.gateway.wait(90, command_id="first-live",
                             expected_revision=initial.revision)
        state = session.store.load(WORLD)
        assert state.time == 90 and state.actions
        assert PLAYER not in state.npcs
        first = session.handoff()
        session.store.snapshot(WORLD)
        saved = session.store.verify(WORLD).to_dict()

    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        assert session.store.load(WORLD).to_dict() == saved
        assert session.handoff() == first
        assert session.store.load(WORLD).time == 90  # paused outside the app
        session.gateway.wait(180, command_id="second-live",
                             expected_revision=session.store.load(WORLD).revision)
        state = session.store.load(WORLD)
        assert state.time == 270
        assert len({record["npc_id"] for record in state.actions.values()}) >= 2
        assert any(a["status"] == "completed" for a in state.actions.values())
        assert state.entities[PLAYER]["location_id"] == "square"
        assert set(state.npcs) == {person[0] for person in PEOPLE}
        assert session.store.verify(WORLD).to_dict() == state.to_dict()


def test_living_cli_two_processes_preserve_npc_time_memory_and_checkpoints(tmp_path):
    file = tmp_path / "seven.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    first = run_cli(
        "scene\nhandoff\nlook\nhandoff\n"
        "talk basim greeting Hello\nwait 180\nscene\nhandoff\nquit\n",
        file, backups, "--new", extra=("--disposable-test",))
    first_handoffs = saved_states(first.stdout)
    assert len(first_handoffs) == 3
    assert first_handoffs[0]["time"] == 0
    assert first_handoffs[1]["revision"] == first_handoffs[0]["revision"] + 1
    assert first_handoffs[2]["time"] == 180
    assert first_handoffs[2]["player_memory"]["observations"]
    before_resume = len(backups_list(backups))
    assert before_resume == 4  # initial, look, talk, wait
    with SQLiteEventStore(file) as store:
        state = store.verify(WORLD)
        assert state.time == 180 and len(state.npcs) == 7
        saved = state.to_dict()

    second = run_cli(
        "scene\nhandoff\nremember\nstatus\nquit\n",
        file, backups, "--resume", extra=("--disposable-test",))
    reloaded = saved_states(second.stdout)
    assert reloaded == [first_handoffs[-1]]
    assert len(backups_list(backups)) == before_resume
    with SQLiteEventStore(file) as store:
        assert store.verify(WORLD).to_dict() == saved


def test_player_can_resume_mid_journey_npc_autonomy_does_not_teleport(tmp_path):
    file = tmp_path / "travel.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    first = run_cli(
        "move square-woods\nwait 49\nhandoff\nquit\n",
        file, backups, "--new", extra=("--disposable-test",))
    assert saved_states(first.stdout)[0]["scene"]["status"] == "traveling"
    with SQLiteEventStore(file) as store:
        state = store.verify(WORLD)
        assert state.time == 49
        assert state.entities[PLAYER]["location_id"] == "square"
        old = state.to_dict()
    second = run_cli(
        "scene\nwait 1\nscene\nhandoff\nquit\n",
        file, backups, "--resume", extra=("--disposable-test",))
    result = saved_states(second.stdout)[0]
    assert result["time"] == 50
    assert result["scene"]["details"]["location_id"] == "woods"
    with SQLiteEventStore(file) as store:
        state = store.verify(WORLD)
        assert state.time == 50
        assert state.entities[PLAYER]["location_id"] == "woods"
        assert state.revision > old["revision"]
        assert len(state.npcs) == 7


def test_explicit_duplicate_id_rejected_after_restart_without_extra_checkpoint(tmp_path):
    file = tmp_path / "dedup.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    run_cli(
        "id my-look look\nquit\n",
        file, backups, "--new", extra=("--disposable-test",))
    with SQLiteEventStore(file) as store:
        frozen = store.verify(WORLD).to_dict()
    count = len(backups_list(backups))
    retried = run_cli(
        "id my-look look\nhandoff\nquit\n",
        file, backups, "--resume", extra=("--disposable-test",))
    assert "Rejected:" in retried.stdout
    assert len(saved_states(retried.stdout)) == 1
    assert len(backups_list(backups)) == count
    with SQLiteEventStore(file) as store:
        assert store.verify(WORLD).to_dict() == frozen


def test_cli_requires_opt_in_and_strict_sha_before_creating_world(tmp_path):
    file = tmp_path / "must-not-create.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    r = run_cli("", file, backups, "--new", ok=False)
    assert "disposable-test" in r.stderr
    assert not file.exists()
    for invalid in ("", "not-sha", "A" * 40, "g" * 40, "a" * 39):
        r = run_cli("", file, backups, "--new", sha=invalid,
                    extra=("--disposable-test",), ok=False)
        assert "code-commit" in r.stderr
        assert not file.exists()
    missing_backups = tmp_path / "missing"
    run_cli("", file, missing_backups, "--new",
            extra=("--disposable-test",), ok=False)
    assert not file.exists()


def test_wrong_schema_resume_rejected_without_modifying_database(tmp_path):
    file = tmp_path / "wrong-version.sqlite"
    with ResumableTestSession.create(
        file, WORLD, PLAYER, setup_living_player_world,
        disposable_test=True) as session:
        session.store.verify(WORLD)
    with sqlite3.connect(file) as db:
        db.execute("UPDATE worlds SET rules_version=?", (RULES_VERSION - 1,))
    prior = file.read_bytes()
    backups = tmp_path / "backups"
    backups.mkdir()
    result = run_cli("", file, backups, "--resume",
                     extra=("--disposable-test",), ok=False)
    assert "unsupported version" in result.stderr
    assert file.read_bytes() == prior
    assert backups_list(backups) == []


def test_existing_checkpoint_commit_collision_rejected_before_mutation(tmp_path):
    file = tmp_path / "same-revision.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    run_cli("quit\n", file, backups, "--new",
            extra=("--disposable-test",))
    state = None
    with SQLiteEventStore(file) as store:
        state = store.verify(WORLD).to_dict()
    checkpoints = backups_list(backups)
    assert len(checkpoints) == 1
    assert verify_backup_bundle(checkpoints[0])["code_commit"] == SOURCE_SHA
    changed = run_cli("quit\n", file, backups, "--resume",
                      sha="b" * 40, extra=("--disposable-test",), ok=False)
    assert "does not match" in changed.stderr
    with SQLiteEventStore(file) as store:
        assert store.verify(WORLD).to_dict() == state
    assert len(backups_list(backups)) == 1


def test_new_world_refuses_existing_file_without_overwrite(tmp_path):
    file = tmp_path / "already.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    data = b"existing user data"
    file.write_bytes(data)
    run_cli("", file, backups, "--new",
            extra=("--disposable-test",), ok=False)
    assert file.read_bytes() == data
    assert not backups_list(backups)


def test_resume_requires_existing_checkpoint_for_same_revision(tmp_path):
    file = tmp_path / "unbacked.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    with ResumableTestSession.create(
        file, WORLD, PLAYER, setup_living_player_world, disposable_test=True
    ) as session:
        before = session.store.verify(WORLD).to_dict()
    result = run_cli("quit\n", file, backups, "--resume",
                     extra=("--disposable-test",), ok=False)
    assert "existing verified checkpoint" in result.stderr
    with SQLiteEventStore(file) as store:
        assert store.verify(WORLD).to_dict() == before
    assert backups_list(backups) == []


def test_new_world_refuses_reused_checkpoint_folder_before_creating_file(tmp_path):
    file = tmp_path / "new.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    old = backups / "living-test-rev-0000000000"
    old.mkdir()
    (old / "keep").write_bytes(b"do not overwrite")
    result = run_cli("quit\n", file, backups, "--new",
                     extra=("--disposable-test",), ok=False)
    assert "empty dedicated" in result.stderr
    assert not file.exists()
    assert (old / "keep").read_bytes() == b"do not overwrite"


def test_mismatched_or_corrupted_current_checkpoint_blocks_resume(tmp_path):
    file = tmp_path / "stopped.sqlite"
    backups = tmp_path / "backups"
    backups.mkdir()
    run_cli("look\nquit\n", file, backups, "--new",
            extra=("--disposable-test",))
    with SQLiteEventStore(file) as store:
        before = store.verify(WORLD).to_dict()
    current = backups_list(backups)[-1]
    manifest_file = current / "manifest.json"
    original = manifest_file.read_bytes()
    manifest_file.write_bytes(original + b"garbage")
    result = run_cli("quit\n", file, backups, "--resume",
                     extra=("--disposable-test",), ok=False)
    assert result.returncode != 0
    with SQLiteEventStore(file) as store:
        assert store.verify(WORLD).to_dict() == before
    assert manifest_file.read_bytes() == original + b"garbage"
