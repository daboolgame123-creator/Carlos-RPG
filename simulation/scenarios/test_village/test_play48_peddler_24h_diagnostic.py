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
from carlos_sim.economic_autonomy import choose_local_food_purchase
from carlos_sim.market import _present, reserved_trade_units

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


def market_resale_gates(state):
    """Operator-only, read-only local resale gate report (never an NPC oracle)."""
    site = "market"
    visible_quote = [
        {"id": offer_id, "price": offer["unit_price"],
         "remaining": offer["remaining"], "status": offer["status"]}
        for offer_id, offer in sorted(state.market_offers.items())
        if offer["seller_id"] == TRADER and offer["stock_owner_id"] == TRADER
        and offer["site_id"] == site and offer["resource"] == "food"
    ]
    here = state.entities[TRADER]["location_id"] == site
    eligible_buys = []
    local_customers = []
    other_hungry_funded = []
    for who, npc in sorted(state.npcs.items()):
        if who == TRADER:
            continue
        bag = state.resources.get(who, {})
        owned_cash = bag.get("coin_copper", 0)
        available_cash = owned_cash - reserved_trade_units(
            state.supply_circuits, who, "coin_copper"
        )
        owned_food = bag.get("food", 0)
        physically_here = state.entities[who]["location_id"] == site
        reason = choose_local_food_purchase(state, who) if physically_here else None
        row = {"npc": who, "hunger": npc["needs"]["hunger"],
               "owned_food": owned_food, "cash": available_cash,
               "next_decision_at": npc["next_decision_at"],
               "here": physically_here,
               "eligible_offer_id": reason.offer_id if reason else None}
        if physically_here:
            local_customers.append(row)
        elif npc["needs"]["hunger"] >= 70 and available_cash >= 2:
            other_hungry_funded.append(row)
        if reason:
            eligible_buys.append({"npc": who, "offer_id": reason.offer_id})
    return {
        "hour": state.time // HOUR,
        "trader_here": here,
        "trader_physically_present": _present(state.to_dict(), TRADER, site),
        "trader_owned_food": state.resources[TRADER]["food"],
        "trader_owned_copper": state.resources[TRADER]["coin_copper"],
        "trader_quotes": visible_quote,
        "eligible_on_site_purchases": eligible_buys,
        "on_site_customers": local_customers,
        "remote_hungry_with_at_least_2_copper": other_hungry_funded,
    }


def test_real_thirteen_npc_diversified_economy_first_twentyfour_hours(tmp_path):
    path = tmp_path / "play48-diversified-24h-diagnostic.sqlite"
    seed(path)
    snapshots = []
    gate_snapshots = []
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
                gate_snapshots.append(market_resale_gates(current))
            print("PLAY48_DIVERSE_ECONOMY_24H_MEASURED_NO_GO_CHECK " +
                  json.dumps(snapshots, sort_keys=True), flush=True)
            print("PLAY48_REAL_PEDDLER_24H_MARKET_GATES " +
                  json.dumps(gate_snapshots, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
