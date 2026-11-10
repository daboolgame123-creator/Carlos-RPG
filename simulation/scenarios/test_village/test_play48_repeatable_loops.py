"""PLAY-48 A: discover why real physical two-cycle production stops.

Uses unmodified PLAY-45 real six-NPC, six-worksite world. This phase's first
probe is observational, not an assertion of recovered self-sufficiency.
After t=0, the test does not issue NPC trades, movements or production actions.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.store import DuplicateCommand
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

            # Reusing an accepted engine command must never replay wages,
            # copy outputs or create a second transaction ledger receipt.
            head = state.to_dict()
            known_receipts = db.db.execute(
                "SELECT count(*) FROM events WHERE world_id=?", (WORLD,)
            ).fetchone()[0]
            with pytest.raises(DuplicateCommand):
                engine.advance(
                    WORLD, seconds=1,
                    command_id=f"play48:diagnose:{raw_stock}:4300",
                    expected_revision=state.revision,
                )
            assert db.load(WORLD).to_dict() == head
            assert db.db.execute(
                "SELECT count(*) FROM events WHERE world_id=?", (WORLD,)
            ).fetchone()[0] == known_receipts

            counts = {
                name: len(_jobs(state, name)) for name in
                ("saw-board", "forge-fitting", "build-frame", "repair-gear")
            }
            if raw_stock == 2:
                # Two real extraction-to-workshop purchases / production cycles
                # for both professions. Downstream tools have no second real
                # buyer/work order: prove and preserve that bottleneck instead
                # of silently disposing of unsold finished goods.
                assert counts == {
                    "saw-board": 2, "forge-fitting": 2,
                    "build-frame": 1, "repair-gear": 1,
                }
                assert state.resources[CARP]["plank"] == 1
                assert state.resources[SMITH]["iron_fitting"] == 1
                assert state.resources[BUILD]["frame"] == 1
                assert state.resources[REPAIR]["fixed_gear"] == 1
                for recipe in ("saw-board", "forge-fitting"):
                    jobs = _jobs(state, recipe)
                    assert len({j["started_at"] for j in jobs}) == 2
                    assert all(j["input_before"] == j["input_after"] + 1 for j in jobs)
                    assert all("work_wage" in j for j in jobs)
                    assert sum(j["work_wage"]["amount"] for j in jobs) == 2
                assert sum(trade["resource"] == "wood"
                           for trade in state.market_trades.values()) == 2
                assert sum(trade["resource"] == "iron_ore"
                           for trade in state.market_trades.values()) == 2
            elif raw_stock == 1:
                assert counts == {k: 1 for k in counts}
            else:
                assert counts == {k: 0 for k in counts}
                assert not state.market_trades

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


@pytest.mark.parametrize("carpenter_cash,smith_cash", [(0, 0), (0, 2), (2, 0)])
def test_full_raw_inventory_does_not_create_free_trade_or_unfunded_wages(
    tmp_path, carpenter_cash, smith_cash,
):
    """A stock-rich supplier alone cannot fund an insolvent worker's order."""
    with SQLiteEventStore(tmp_path / f"cash-{carpenter_cash}-{smith_cash}.sqlite") as db:
        start = _seed(
            db, wood=2, iron=2,
            carpenter_cash=carpenter_cash, smith_cash=smith_cash,
            builder_cash=4, repairer_cash=4,
        )
        opening = _cash(start)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            final = engine.advance(
                WORLD, seconds=700, command_id="play48:credit-negative",
                expected_revision=start.revision,
            ).state
            _audit(final, opening, 2, 2)
            completed = {
                recipe: len(_jobs(final, recipe)) for recipe in
                ("saw-board", "forge-fitting", "build-frame", "repair-gear")
            }
            assert (completed["saw-board"] == 0) == (carpenter_cash == 0)
            assert (completed["forge-fitting"] == 0) == (smith_cash == 0)
            if carpenter_cash == 0:
                assert final.resources[WOOD]["wood"] == 2
                assert final.resources[BUILD]["frame"] == 0
                assert not any(t["buyer_id"] == "carpenter"
                               for t in final.market_trades.values())
            if smith_cash == 0:
                assert final.resources[IRON]["iron_ore"] == 2
                assert final.resources[REPAIR]["fixed_gear"] == 0
                assert not any(t["buyer_id"] == "smith"
                               for t in final.market_trades.values())
            assert db.verify(WORLD).to_dict() == final.to_dict()
            print("PLAY48_NEGATIVE_FINANCING " + json.dumps({
                "carpenter_cash": carpenter_cash, "smith_cash": smith_cash,
                "copper_conserved": opening == _cash(final),
                "completed": completed,
                "no_silent_credit": True,
            }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
