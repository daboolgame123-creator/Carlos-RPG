"""PLAY-48B: independent 96h physical-economy post-stall diagnosis.

This is a negative-control experiment, not an engine fix or a positive claim of
renewable village survival. Existing genuine PLAY-47 world and event reducers.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply_diagnostics import audit_courier
from test_play47_closure_endurance import _seed, _day, _reading, DAY, WORLD


def _count(state, resource):
    return sum(trade["resource"] == resource for trade in state.market_trades.values())


def _finished(state):
    return sum(job["status"] == "completed" for job in state.production_jobs.values())


def test_96h_detects_no_phantom_recovery_and_explains_courier_stall(tmp_path):
    path = tmp_path / "shared-thirteen-resident-economy.sqlite"
    _seed(path)
    checkpoints = []
    for day in range(1, 5):
        state = _day(path, day * DAY, rain=(day <= 3))
        with SQLiteEventStore(path) as reopened:
            assert reopened.verify(WORLD).to_dict() == state.to_dict()
        audit = audit_npc_economy(state)
        assert audit["copper_scope_complete"]
        assert audit["copper_known_total"] == 12
        assert all(val is None or (type(val) is int and val >= 0)
                   for stocks in state.resources.values() for val in stocks.values())
        couriers = {
            courier: audit_courier(state, courier, supply_enabled=True)
            for courier in ("huda", "hana")
        }
        checkpoint = {
            "day": day, "time": state.time, "market_food": state.resources["market"]["food"],
            "trades": audit["trades"], "finished_jobs": _finished(state),
            "wage_receipts": audit["wage_receipts"],
            "market_food_sales": _count(state, "food"),
            "couriers": {
                k: {
                    "hunger": v["needs"]["hunger"], "deliveries": v["deliveries"],
                    "blocked_reasons": v["blocked_reasons"], "next_action": v["next_action"],
                    "location": v["location"],
                } for k, v in couriers.items()
            },
            "copper_known": audit["copper_known_total"],
            "hunger_at_cap": sum(npc["needs"]["hunger"] == 100
                                 for npc in state.npcs.values()),
        }
        checkpoints.append(checkpoint)

    third, fourth = checkpoints[2], checkpoints[3]
    for metric in ("trades", "finished_jobs", "wage_receipts", "market_food_sales"):
        assert fourth[metric] == third[metric], (
            "unexpected change in documented 72h stall; investigate", metric, third, fourth
        )
    for courier in ("huda", "hana"):
        assert fourth["couriers"][courier]["deliveries"] == third["couriers"][courier]["deliveries"]
        assert fourth["couriers"][courier]["hunger"] >= 90
        assert "hunger_at_or_above_90" in fourth["couriers"][courier]["blocked_reasons"]
    assert fourth["market_food"] > 0, "market inventory exists despite starvation"
    assert fourth["hunger_at_cap"] > 0
    assert fourth["copper_known"] == third["copper_known"] == 12
    print("PLAY48_POST72_CAUSAL_BLOCKERS " + json.dumps({
        "checkpoints": checkpoints,
        "no_fourth_day_new_trades_jobs_wages": True,
        "no_fourth_day_courier_delivery": True,
        "hunger_blocks_known_courier_actions": True,
        "unsold_food_exists_without_authorized_distribution": True,
        "no_auto_restock_or_copper_mint": True,
        "engine_modified_to_force_recovery": False,
    }, sort_keys=True), flush=True)
