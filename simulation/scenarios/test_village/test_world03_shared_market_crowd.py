"""WORLD-03 bounded contention at one market with scarce real stock."""
from __future__ import annotations

from bench_shared_market_scale import run_sample


def test_thirteen_npcs_compete_for_four_owned_market_food_units_deterministically(
        tmp_path):
    first = run_sample(tmp_path / "market-crowd-a.sqlite", 13, food_stock=4)
    second = run_sample(tmp_path / "market-crowd-b.sqlite", 13, food_stock=4)

    assert first["audit"]["buyers"] == 12
    assert first["audit"]["market_trades"] == 4
    assert len(first["audit"]["served_buyers"]) == 4
    assert len(first["audit"]["unserved_buyers"]) == 8
    assert first["audit"]["food_remaining_at_market"] == 0
    assert first["audit"]["food_held_by_buyers"] == 4
    assert first["audit"]["opening_copper"] == 24
    assert first["audit"]["closing_copper"] == 24
    assert first["state_digest"] == second["state_digest"]
    assert first["event_ledger_digest"] == second["event_ledger_digest"]
    assert first["event_types"]["MarketTradeExecuted"] == 4
