"""PLAY-19: exercise the SAME seven-NPC world through one continuous journey."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from carlos_sim import SQLiteEventStore
from carlos_sim.resumable_play import ResumableTestSession
from living_player_fixture import WORLD, PLAYER, living_player_gateway
from play_integrated_journey import run_integrated_journey


def _run(tmp_path, label="village"):
    return run_integrated_journey(tmp_path / (label + ".sqlite"))


def test_seven_npc_journey_crosses_market_speech_gifts_meals_travel_and_restart(tmp_path):
    result = _run(tmp_path)
    assert result["format"] == "carlos-play19-integrated-test-v1"
    assert result["canonical_story"] is False
    assert result["disposable_test"] is True
    view = result["player_visible"]
    scenes = view["route_sightings"]
    assert {"square", "bakery", "woods"} == {row["place"] for row in scenes}
    assert scenes[0]["time"] == 0 and scenes[-1]["time"] == 131
    assert view["time_at_checkpoint"] == 191
    assert view["own_wallet"] == {
        "bread": 1, "coin_copper": 4, "food": 0,
    }
    assert view["own_purchases"]["total"] == 1
    assert view["own_gifts"]["total"] == 1
    assert view["own_meals"]["total"] == 2
    assert view["own_conversations"]["total"] >= 2
    assert len(view["own_hearsay"]) == 1
    assert view["own_hearsay"][0]["status"] == "unverified"
    assert all(x["activity"] in (
        "working", "resting", "foraging", "producing",
        "eating", "talking",
    ) for x in view["witnessed_events"])
    assert len(view["witnessed_events"]) <= 20
    report = result["test_audit_only"]
    assert report["npc_count"] == 7
    assert report["npc_action_count"] >= 2
    assert report["social_exchange_count"] > 0
    assert all(report[k] for k in (
        "bread_conserved", "copper_conserved", "woods_food_conserved",
        "no_unsanctioned_player_health_effect", "verified_replay_matches_save",
    ))
    assert result["restart"] == {
        "handoff_identical_before_new_action": True,
        "replayed_world_identical": True,
        "no_time_advanced_while_closed": True,
        "duplicate_meal_rejected": True,
        "stale_revision_rejected": True,
        "time_after_explicit_next_wait": 201,
    }


def test_journey_is_deterministic_in_two_unrelated_sqlite_files(tmp_path):
    first = _run(tmp_path, "first")
    second = _run(tmp_path, "second")
    assert first == second


def test_journey_report_contains_no_private_npc_state_or_health_guess(tmp_path):
    report = _run(tmp_path)
    player = json.dumps(report["player_visible"], ensure_ascii=False)
    for secret in (
        '"npcs"', '"beliefs"', '"goals"', '"needs"',
        '"relations"', '"injuries"', '"inventory"', '"production_jobs"',
        '"market_trades"', '"resource_before"', '"trust_before"',
        '"trust_after"', '"hunger"', '"fatigue"',
        '"health_effect": "healed"',
    ):
        assert secret not in player
    assert report["canonical_story"] is False
    assert not any("nora" in str(item) for item in
                   report["player_visible"]["route_sightings"]
                   if item["place"] == "square" and item["time"] == 0)


def test_integration_script_prints_actual_machine_readable_outcomes(tmp_path):
    script = Path(__file__).resolve().parents[1] / (
        "scenarios/test_village/play_integrated_journey.py")
    output = subprocess.run(
        [sys.executable, str(script)], text=True,
        capture_output=True, timeout=100, check=True,
    )
    marker = "PLAY19_JSON="
    result = json.loads(next(x.split(marker, 1)[1] for x in
                             output.stdout.splitlines() if x.startswith(marker)))
    assert result["restart"]["time_after_explicit_next_wait"] == 201
    assert result["player_visible"]["own_wallet"]["coin_copper"] == 4
    assert "CARLOS — PLAY-19" in output.stdout
    assert "conserved" in output.stdout


def test_resumed_file_requires_explicit_disposable_permission(tmp_path):
    path = tmp_path / "world.sqlite"
    result = _run(tmp_path, "world")
    assert result["restart"]["no_time_advanced_while_closed"]
    with pytest.raises(PermissionError, match="experimental"):
        ResumableTestSession.resume(path, WORLD, PLAYER)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
