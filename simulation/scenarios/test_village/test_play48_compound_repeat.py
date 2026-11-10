"""PLAY-48C: two autonomous compound ore+charcoal cycles with finite physical input.

This proves actual repeated atomic compound workshops and separately reports
the absent second final repair demand. No scripted NPC actions after genesis.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore, TimeEngine
from test_play46_physical_chain import (
    _auto_boot, _add_second_autonomous_profession, _auto_engine,
    _money, WORLD, SMITH, MINE, KILN, FORGE,
)


def test_two_real_compound_input_cycles_without_invented_second_buyer(tmp_path):
    with SQLiteEventStore(tmp_path / "repeat-compound-smith.sqlite") as db:
        _auto_boot(db, ore_stock=2, charcoal_stock=2, smith_copper=4)
        state = _add_second_autonomous_profession(db)
        assert _money(state) == 8
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _auto_engine(db, clock)
            for t in (700, 1400, 2400, 4300):
                state = engine.advance(
                    WORLD, seconds=t-state.time,
                    command_id=f"play48:compound:{t}",
                    expected_revision=state.revision,
                ).state
                assert state.time == t
                assert _money(state) == 8
                assert all(amount >= 0 for stock in state.resources.values()
                           for amount in stock.values() if type(amount) is int)
            jobs = [
                job for job in state.production_jobs.values()
                if job["recipe_id"] == "iron-plus-fuel" and job["status"] == "completed"
            ]
            repaired = [
                job for job in state.production_jobs.values()
                if job["recipe_id"] == "repair-tools" and job["status"] == "completed"
            ]
            smith_trades = [
                trade for trade in state.market_trades.values()
                if trade["buyer_id"] == SMITH
            ]
            assert len(jobs) == 2
            assert len(repaired) == 1  # no second genuine repaired-gear buyer
            assert sorted(t["resource"] for t in smith_trades) == [
                "charcoal", "charcoal", "iron_ore", "iron_ore",
            ]
            assert state.resources[MINE]["iron_ore"] == 0
            assert state.resources[KILN]["charcoal"] == 0
            assert state.resources[FORGE]["anvil"] == 1
            assert state.resources[FORGE]["iron_fitting"] == 1
            assert state.resources["repair_shop"]["repaired_gear"] == 1
            assert sum("work_wage" in job for job in jobs) == 1, (
                "only the first genuine sale finances the first wage"
            )
            for job in jobs:
                assert dict(job["input_before_by_resource"]) == {
                    "iron_ore": 1, "charcoal": 1,
                }
                assert dict(job["input_after_by_resource"]) == {
                    "iron_ore": 0, "charcoal": 0,
                }
                assert job["tool_seen"] == 1
                assert job["finished_at"] == job["due"]
            assert db.snapshot(WORLD).to_dict() == state.to_dict()
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            print("PLAY48_COMPOUND_CYCLES " + json.dumps({
                "source_ore": 2, "source_charcoal": 2,
                "smith_completed": len(jobs),
                "repair_completed": len(repaired),
                "smith_local_material_purchases": len(smith_trades),
                "paid_smith_jobs": sum("work_wage" in j for j in jobs),
                "unsold_fitting": state.resources[FORGE]["iron_fitting"],
                "remaining_copper": _money(state),
                "no_virtual_trade_or_materials": True,
                "independent_actors": 5,
            }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
