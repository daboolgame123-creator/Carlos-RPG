"""PLAY48: same physical world, evaluate EXISTING lawful free subsistence.

Only the old engine flags differ. No staff, supplies, copper, road, weather
or prey is injected in either arm after original 13NPC trusted genesis.
No win is assumed. Physical wildlife lots must account for timed hunting AND
foraged one-unit wild-food collection after a completed action.
"""
from __future__ import annotations

import json

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_peddler_fast import seed
from test_play48_peddler_24h_diagnostic import measures, HOUR

SITES = ("hunting_woods", "riverbank")


def _conserve_with_real_foraging(state):
    assert len(state.npcs) == 13
    cash = audit_npc_economy(state)
    assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    physical = state.resources
    foraged = sum(f["quantity"] for f in state.foraging_attempts.values()) + sum(
        g["quantity"] for g in state.gatherings.values()
    )
    completed_wild = [
        j for j in state.production_jobs.values()
        if j["recipe_id"] in ("two-portions-hunter", "two-portions-fisher")
        and j["status"] == "completed"
    ]
    # Prey: initial 2 real lots + 6 finite environmental reserve per site.
    for site in SITES:
        worked = sum(
            j["site_id"] == site
            and j["recipe_id"] in ("two-portions-hunter", "two-portions-fisher")
            for j in state.production_jobs.values()
        )
        collected = sum(
            row["quantity"]
            for row in state.foraging_attempts.values()
            if row["site_id"] == site
        ) + sum(
            row["quantity"] for row in state.gatherings.values()
            if row["site_id"] == site
        )
        assert (physical[site]["wild_food"] +
                physical[site]["regrowth_reserve"] +
                worked + collected == 8), site
    food = (sum(bag.get("food", 0) for bag in physical.values())
            + sum(p["remaining"] for p in state.courier_provisions.values()))
    grain = sum(bag.get("grain", 0) for bag in physical.values())
    meals = sum(m["quantity"] for m in state.consumptions.values())
    harvest_yields = {}
    for site in state.farm_plots:
        candidates = [
            rec["output_amount"] for rec in state.production_recipes.values()
            if rec["site_id"] == site
            and rec.get("input_resource") == "crop_ready"
            and rec["output_resource"] == "grain"
        ]
        assert len(candidates) == 1
        harvest_yields[site] = candidates[0]
    pending_bakes = sum(
        state.production_recipes[j["recipe_id"]]["input_amount"]
        for j in state.production_jobs.values()
        if j["status"] == "running"
        and state.production_recipes[j["recipe_id"]].get("input_resource") == "grain"
        and state.production_recipes[j["recipe_id"]]["output_resource"] == "food"
    )
    pending_harvest = sum(
        harvest_yields[j["site_id"]]
        for j in state.production_jobs.values()
        if j["status"] == "running"
        and state.production_recipes[j["recipe_id"]].get("input_resource") == "crop_ready"
    )
    grown = sum(plot["matured"] * harvest_yields[site]
                for site, plot in state.farm_plots.items())
    ripe = sum(physical[site]["crop_ready"] * amount
               for site, amount in harvest_yields.items())
    assert food + grain + meals + pending_bakes + pending_harvest + ripe == (
        3 + grown + 2 * len(completed_wild) + foraged
    )
    water = sum(physical[k]["water"] for k in
                ("well", "farm", "farm_east", "huda", "hana")
                if k in physical and "water" in physical[k])
    used = sum(f["started"] for f in state.farm_plots.values())
    assert water + used == 2 + state.hydrology_sources["well"]["received_total"]


def _engine(db, clock, *, autonomous_foraging):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=10000,
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
        foraging_enabled=autonomous_foraging,
        gathering_enabled=autonomous_foraging,
        knowledge_enabled=autonomous_foraging,
        food_navigation_enabled=autonomous_foraging,
        assistance_enabled=autonomous_foraging,
        aid_relay_enabled=autonomous_foraging,
        scarcity_enabled=autonomous_foraging,
    )


def test_equal_worlds_do_existing_institutional_foraging_and_help_change_24h(tmp_path):
    paths = [tmp_path / "no-forage.sqlite", tmp_path / "real-forage.sqlite"]
    first, second = [seed(p) for p in paths]
    assert first.to_dict() == second.to_dict()
    snapshots = []
    for path, enabled in zip(paths, (False, True)):
        readings = []
        with SQLiteEventStore(path) as db:
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                engine = _engine(db, clock, autonomous_foraging=enabled)
                for hour in (6, 12, 24):
                    previous = db.verify(WORLD)
                    current = engine.advance(
                        WORLD, seconds=hour*HOUR - previous.time,
                        command_id=f"same-world-{enabled}:{hour}h",
                        expected_revision=previous.revision,
                    ).state
                    assert current.time == hour*HOUR
                    _conserve_with_real_foraging(current)
                    assert db.verify(WORLD).to_dict() == current.to_dict()
                    assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                    assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                    stats = measures(current)
                    stats["collected_by_real_forage"] = sum(
                        row["quantity"]
                        for row in current.foraging_attempts.values()
                    )
                    stats["collected_by_real_investigation"] = sum(
                        row["quantity"] for row in current.gatherings.values()
                    )
                    stats["real_help_deliveries"] = sum(
                        o["status"] == "fulfilled" for o in current.obligations.values()
                    )
                    readings.append(stats)
            finally:
                clock.close_session(WORLD)
        snapshots.append({
            "ordinary_shop_couriers_vs_optin_survival": enabled,
            "hours": readings,
        })
    print("PLAY48_ACTUAL_IDENTICAL_GENESIS_FORAGING_ASSISTANCE_24H_AB " +
          json.dumps(snapshots, sort_keys=True), flush=True)
