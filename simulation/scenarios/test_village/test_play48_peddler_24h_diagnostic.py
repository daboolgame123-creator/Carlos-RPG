"""PLAY48: measure the next genuine 24h bottleneck, not a success oracle.

No gifts, no invented jobs, no scripted NPC movements, no imports and no
unstated rain. Positive food ownership is NOT counted as a meal. Historical
control caveat: this is an *opt-in new ecology* with actual finite initial
wild food, not an equal-resource A/B against the old PR90 world.
"""
from __future__ import annotations

import json

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_peddler_fast import seed
from test_play48_finite_hunt_fish_roads import conserve_diverse
from carlos_sim.food_peddler import TRADER

HOUR = 3600


def measures(state):
    site_stock = {
        site: state.resources[site]["food"]
        for site in ("market", "bakery", "hunting_woods", "riverbank")
    }
    consumed = len(state.consumptions)
    paid_production = {
        job["npc_id"] for job in state.production_jobs.values()
        if "food_wage" in job or "work_wage" in job
    }
    paid_courier = {
        c["courier_id"] for c in state.courier_provisions.values()
        if c["payments"]
    }
    peddler_buys = sum(t["buyer_id"] == TRADER
                       and t["site_id"] == "hunting_woods"
                       and t["resource"] == "food"
                       for t in state.market_trades.values())
    peddler_sales = sum(t["seller_id"] == TRADER
                        and t["site_id"] == "market"
                        and t["resource"] == "food"
                        for t in state.market_trades.values())
    cash = audit_npc_economy(state)
    return {
        "hour": state.time // HOUR,
        "hunger100": sum(n["needs"]["hunger"] == 100
                         for n in state.npcs.values()),
        "food_eaten_meals": consumed,
        "food_stock_by_site": site_stock,
        "food_owned_by_npcs": sum(state.resources.get(n, {}).get("food", 0)
                                   for n in state.npcs),
        "total_food_sales": sum(t["resource"] == "food"
                                for t in state.market_trades.values()),
        "peddler_source_purchases": peddler_buys,
        "peddler_market_resales": peddler_sales,
        "production_jobs_completed": sum(j["status"] == "completed"
                                          for j in state.production_jobs.values()),
        "persons_with_real_wage": len(paid_production | paid_courier),
        "courier_deliveries": {
            who: state.supply_circuits[who]["deliveries"]
            for who in ("hana", "huda")
        },
        "prey_lots_remaining": {
            site: state.resources[site]["wild_food"]
            + state.resources[site]["regrowth_reserve"]
            for site in ("hunting_woods", "riverbank")
        },
        "well_water": state.resources["well"]["water"],
        "copper": cash["copper_known_total"],
    }


def test_real_thirteen_npc_diversified_economy_first_twentyfour_hours(tmp_path):
    path = tmp_path / "play48-diversified-24h-diagnostic.sqlite"
    seed(path)
    snapshots = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=9000,
                decision_cooldown=3600, economic_enabled=True,
                agriculture_enabled=True, navigation_enabled=True,
                routines_enabled=True, consumption_enabled=True,
                survival_enabled=True, supply_enabled=True,
                shopping_routes_enabled=True,
                multi_professional_markets_enabled=True,
                compound_procurement_enabled=True,
                professional_full_life_enabled=True,
                food_for_work_enabled=True,
                food_peddler_enabled=True,
                seek_alternative_food_market_enabled=True,
            )
            for hour in (6, 12, 18, 24):
                earlier = db.verify(WORLD)
                current = engine.advance(
                    WORLD, seconds=hour * HOUR - earlier.time,
                    command_id=f"real-diverse-economy:{hour}h",
                    expected_revision=earlier.revision,
                ).state
                assert current.time == hour * HOUR
                conserve_diverse(current)
                cash = audit_npc_economy(current)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"] == 12
                assert db.verify(WORLD).to_dict() == current.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                snapshots.append(measures(current))
            print("PLAY48_DIVERSE_ECONOMY_24H_MEASURED_NO_GO_CHECK " +
                  json.dumps(snapshots, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
