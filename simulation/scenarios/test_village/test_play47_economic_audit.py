"""PLAY-47 first economic audit pilot — no fabricated population or supply.

This pilot intentionally reuses the real PLAY-46 autonomous smith/repairer
world. It is NOT a 7-NPC survival test and NOT a proof of 24h/7d viability.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play46_physical_chain import (
    WORLD, _auto_boot, _add_second_autonomous_profession, _auto_engine,
    _auto_until,
)


def _simple(resources):
    return SimpleNamespace(
        world_id="read-only-audit", time=0, revision=0,
        entities={"npc": {"controller": "npc"}},
        locations={"site": {"name": "site"}},
        resources=resources,
        market_trades={}, production_jobs={}, travels={},
        npcs={"npc": {"needs": {"hunger": 10}}},
    )


def test_missing_copper_is_unknown_not_zero_and_audit_does_not_mutate():
    state = _simple({"npc": {"coin_copper": 2}, "site": {"bread": 3}})
    before = {"npc": dict(state.resources["npc"]),
              "site": dict(state.resources["site"])}
    report = audit_npc_economy(state)
    assert report["copper_known_total"] == 2
    assert report["copper_unknown_owners"] == ("site",)
    assert report["copper_scope_complete"] is False
    assert report["stock_known_by_resource"] == {"bread": 3}
    assert state.resources == before


@pytest.mark.parametrize("invalid", [-1, True, 1.5, "two"])
def test_invalid_financial_ledger_fails_closed(invalid):
    world = _simple({"npc": {"coin_copper": invalid}, "site": {}})
    with pytest.raises(ValueError, match="invalid amount"):
        audit_npc_economy(world)


def test_autonomous_compound_economy_audit_pilot_one_hour(tmp_path):
    """Observe actual NPC decisions and money at t=0, 700 and 3600."""
    with SQLiteEventStore(tmp_path / "play47-real-economic-pilot.sqlite") as db:
        _auto_boot(db)
        genesis = _add_second_autonomous_profession(db)
        start = audit_npc_economy(genesis)
        assert start["copper_known_total"] == 6
        assert start["trades"] == 0
        assert start["completed_jobs"] == 0

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _auto_engine(db, clock)
            snapshots = [start]
            for stop in (700, 3600):
                current = _auto_until(db, engine, stop, f"play47-{stop}")
                record = audit_npc_economy(current)
                snapshots.append(record)
                assert record["copper_known_total"] == 6
                assert record["copper_unknown_owners"] == start["copper_unknown_owners"]
            observed = snapshots[-1]
            assert observed["trades"] == 3
            assert observed["trades_by_resource"] == {
                "charcoal": 1, "iron_fitting": 1, "iron_ore": 1,
            }
            assert observed["completed_jobs"] == 2
            assert observed["wage_receipts"] == 1
            assert observed["trips_arrived"] >= 6
            assert observed["time"] == 3600
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == current.to_dict()
            print("PLAY47_INITIAL_NPC_ECONOMY_AUDIT", json.dumps(
                snapshots, sort_keys=True))
        finally:
            clock.close_session(WORLD)
