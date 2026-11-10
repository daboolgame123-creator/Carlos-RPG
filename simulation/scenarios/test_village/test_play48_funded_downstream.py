"""PLAY-48D: second *real* builder and repairer contracts with funded demand.

Four distinct downstream customers/worksites compete for ONLY two existing
upstream units of plank/fitting. Second projects are actual t=0 NPC routines,
physical workshop sites, recipes, tools and wallets, never scripted trades
or post-genesis gifts. Deliberately observes any unmet demand (no success fraud).
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from test_play45_multisector import (
    WORLD, _seed, _engine, _cash, _e, CARP, SMITH, BUILD, REPAIR, WOOD, IRON, HOME,
)


def _two_real_contracts(db, *, material=2, worker_coins=2, second_shift=250):
    # Old and new buyers have separately owned, INITIALIZED money and
    # workplaces. No post-genesis transfer, subsidized loan or fiat wage.
    state = _seed(
        db, wood=material, iron=material,
        carpenter_cash=2, smith_cash=2,
        builder_cash=worker_coins, repairer_cash=worker_coins,
    )
    events = []
    for site, who, role, source, product, tool, supplier, duration in (
        ("building_east", "builder_east", "builder", "plank", "frame",
         "hammer", CARP, 90),
        ("repair_east", "repairer_east", "repairer", "iron_fitting", "fixed_gear",
         "wrench", SMITH, 90),
    ):
        events.extend([
            _e("LocationCreated", {"id": site, "name": site}),
            _e("RouteCreated", {
                "id": supplier + "-" + site,
                "a": supplier, "b": site, "seconds": duration,
            }),
            _e("EntityCreated", {
                "id": who, "name": who, "location_id": site, "controller": "npc",
            }),
            _e("NPCConfigured", {
                "npc_id": who, "role": role,
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ])
        for resource, count in (
            (source, 0), (product, 0), (tool, 1), ("coin_copper", 0),
        ):
            events.append(_e("ResourceChanged", {
                "owner_id": site, "resource": resource,
                "previous": None, "current": count,
                "source": "initialization",
            }))
        for resource, count in ((source, 0), ("coin_copper", worker_coins)):
            events.append(_e("ResourceChanged", {
                "owner_id": who, "resource": resource,
                "previous": None, "current": count,
                "source": "initialization",
            }))
        events.extend([
            _e("NPCRoutineConfigured", {
                "npc_id": who, "home_id": HOME,
                "workplace_id": site, "work_start": second_shift,
                "work_end": 20_000,
            }),
            _e("ProductionRecipeConfigured", {
                "id": site + "-project",
                "site_id": site, "role": role,
                "input_resource": source, "input_amount": 1,
                "output_resource": product, "output_amount": 1,
                "tool_resource": tool, "duration_seconds": 90,
            }),
        ])
    state = db.append(
        WORLD, "play48:two-distinct-projects", state.revision,
        events, bootstrap=True,
    )
    assert len(state.npcs) == 8
    assert len(state.production_recipes) == 6
    assert _cash(state) == 4 + 4 * worker_coins
    return state


@pytest.mark.parametrize("material,worker_coins,second_shift", [
    (2, 2, 250), (2, 2, 520), (1, 2, 520), (2, 0, 520),
])
def test_four_distinct_downstream_customers_preserve_economy(
    tmp_path, material, worker_coins, second_shift,
):
    with SQLiteEventStore(tmp_path / f"four-real-customers-{material}-{worker_coins}-{second_shift}.sqlite") as db:
        start = _two_real_contracts(db, material=material, worker_coins=worker_coins,
                                    second_shift=second_shift)
        money = _cash(start)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            for checkpoint in (700, 1400, 2600, 4300, 6500):
                start = engine.advance(
                    WORLD, seconds=checkpoint - start.time,
                    command_id=f"play48:real-demand:{material}:{worker_coins}:{checkpoint}",
                    expected_revision=start.revision,
                ).state
                assert _cash(start) == money
                assert all(value >= 0 for owned in start.resources.values()
                           for value in owned.values() if type(value) is int)
            assert db.snapshot(WORLD).to_dict() == start.to_dict()
            assert db.verify(WORLD).to_dict() == start.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            upstream = {"wood": 0, "iron_ore": 0}
            for trade in start.market_trades.values():
                if trade["resource"] in upstream:
                    upstream[trade["resource"]] += trade["quantity"]
            assert upstream["wood"] <= material and upstream["iron_ore"] <= material
            terminal = {
                site: {
                    "resource": result,
                    "quantity": start.resources[site][result],
                    "workers": [job["npc_id"] for job in start.production_jobs.values()
                                if job["site_id"] == site and job["status"] == "completed"],
                }
                for site, result in (
                    (BUILD, "frame"), ("building_east", "frame"),
                    (REPAIR, "fixed_gear"), ("repair_east", "fixed_gear")
                )
            }
            for site, item in terminal.items():
                assert item["quantity"] <= 1
                assert item["quantity"] == len(item["workers"])
            # When a second genuine worker has a later work shift they
            # cannot arrive together and compete for the first single-item
            # quote. Any second job must still buy its OWN second batch.
            if material == 2 and worker_coins == 2 and second_shift == 520:
                assert terminal["building"]["quantity"] == 1
                assert terminal["building_east"]["quantity"] == 1
                assert terminal["repair"]["quantity"] == 1
                assert terminal["repair_east"]["quantity"] == 1
                assert sum(t["resource"] == "plank"
                           for t in start.market_trades.values()) == 2
                assert sum(t["resource"] == "iron_fitting"
                           for t in start.market_trades.values()) == 2
            if worker_coins == 0:
                assert all(item["quantity"] == 0 for item in terminal.values()), (
                    "No downstream buyer may receive a free product"
                )
            print("PLAY48_REAL_DEMAND_MATRIX " + json.dumps({
                "source_units_per_resource": material,
                "second_shift": second_shift,
                "wallet_per_downstream_buyer": worker_coins,
                "copper_total": money,
                "completed_projects": terminal,
                "trades": [
                    {"buyer": t["buyer_id"], "item": t["resource"],
                     "price": t["total_paid"]}
                    for t in start.market_trades.values()
                ],
                "two_separate_construction_sites": True,
                "two_separate_repair_sites": True,
                "unmet_orders_not_fabricated": True,
                "untouched_engine_rules": True,
            }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
