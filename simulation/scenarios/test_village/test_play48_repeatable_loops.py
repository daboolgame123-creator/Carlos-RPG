"""PLAY-48 A: discover why real physical two-cycle production stops.

Uses unmodified PLAY-45 real six-NPC, six-worksite world. This phase's first
probe is observational, not an assertion of recovered self-sufficiency.
After t=0, the test does not issue NPC trades, movements or production actions.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from test_play45_multisector import (
    _seed, _engine, _cash, WORLD, CARP, SMITH, BUILD, REPAIR, WOOD, IRON,
)


def _jobs(state, recipe):
    return [
        job for job in state.production_jobs.values()
        if job["recipe_id"] == recipe and job["status"] == "completed"
    ]


def _audit(state, total, starting_wood, starting_iron):
    assert _cash(state) == total, "copper was minted or lost"
    assert all(value >= 0 for owner in state.resources.values()
               for value in owner.values() if type(value) is int)
    recipes = (
        ("saw-board", "wood", "plank", CARP),
        ("forge-fitting", "iron_ore", "iron_fitting", SMITH),
        ("build-frame", "plank", "frame", BUILD),
        ("repair-gear", "iron_fitting", "fixed_gear", REPAIR),
    )
    for name, _, _, _ in recipes:
        for job in _jobs(state, name):
            assert job["input_before"] == job["input_after"] + 1
            assert job["output_after"] == job["output_before"] + 1
            assert job["tool_seen"] >= 1
            if "work_wage" in job:
                w = job["work_wage"]
                assert w["site_before"] - w["site_after"] == w["amount"]
                assert w["worker_after"] - w["worker_before"] == w["amount"]
    assert (state.resources[WOOD]["wood"] +
            state.resources[CARP]["wood"] +
            state.resources["carpenter"]["wood"] +
            sum(job["recipe_id"] == "saw-board" for job in state.production_jobs.values()) == starting_wood)
    assert (state.resources[IRON]["iron_ore"] +
            state.resources[SMITH]["iron_ore"] +
            state.resources["smith"]["iron_ore"] +
            sum(job["recipe_id"] == "forge-fitting" for job in state.production_jobs.values()) == starting_iron)


@pytest.mark.parametrize("raw_stock,cash", [
    (1, (1, 1, 2, 2)),
    (2, (2, 2, 4, 4)),
    (0, (2, 2, 4, 4)),
])
def test_two_cycle_physical_material_bottleneck_diagnosis(tmp_path, raw_stock, cash):
    path = tmp_path / f"bounded-{raw_stock}.sqlite"
    with SQLiteEventStore(path) as db:
        state = _seed(db, wood=raw_stock, iron=raw_stock,
                      carpenter_cash=cash[0], smith_cash=cash[1],
                      builder_cash=cash[2], repairer_cash=cash[3])
        initial_copper = _cash(state)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            for end in (700, 1400, 2600, 4300):
                state = engine.advance(
                    WORLD, seconds=end-state.time,
                    command_id=f"play48:diagnose:{raw_stock}:{end}",
                    expected_revision=state.revision,
                ).state
                assert state.time == end
                _audit(state, initial_copper, raw_stock, raw_stock)
                assert db.snapshot(WORLD).to_dict() == state.to_dict()
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            counts = {
                name: len(_jobs(state, name)) for name in
                ("saw-board", "forge-fitting", "build-frame", "repair-gear")
            }
            trades = [
                {"buyer": trade["buyer_id"], "resource": trade["resource"],
                 "time": trade["executed_at"]}
                for trade in state.market_trades.values()
            ]
            report = {
                "raw_stock": raw_stock, "opening_copper": initial_copper,
                "completed_by_recipe": counts,
                "trades": trades,
                "final_resources": {owner: dict(state.resources[owner])
                                    for owner in (WOOD, IRON, CARP, SMITH, BUILD, REPAIR)},
                "tools_not_consumed": all(
                    state.resources[site][tool] == 1 for site, tool in
                    ((CARP, "saw"), (SMITH, "anvil"),
                     (BUILD, "hammer"), (REPAIR, "wrench"))
                ),
                "source_unchanged_after_genesis": True,
                "manual_npc_actions": 0,
            }
            print("PLAY48A_BOTTLENECK " + json.dumps(report, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
