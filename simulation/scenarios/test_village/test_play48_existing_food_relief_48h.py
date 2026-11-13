"""PLAY48: already present real aid/forage/known-road behavior vs original 48h.

NO new game rules; same physical genesis, coin, people, finite water/forest.
Only flip authentic built-in opt-ins for physically sourced foraging, local
assistance, relay and personally learned routes. Count every gathered and
foraged wild portion separately in the conservation equation.
A passed observational test is NOT a release acceptance or magic welfare.
"""
from __future__ import annotations
import json

from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_real_watch_income_24h import seed, HOUR
from test_play48_peddler_24h_diagnostic import measures
from test_play48_finite_hunt_fish_roads import INITIAL_FOOD, INITIAL_WATER, SITES


def _universal_physical_conservation(state):
    assert len(state.npcs) == 13
    coins = audit_npc_economy(state)
    assert coins["copper_scope_complete"] and coins["copper_known_total"] == 12
    inventory = state.resources
    taken = (
        sum(a["quantity"] for a in state.foraging_attempts.values()) +
        sum(a["quantity"] for a in state.gatherings.values())
    )
    for site in SITES:
        used_by_jobs = sum(
            job["site_id"] == site and job["recipe_id"] in
            ("two-portions-hunter", "two-portions-fisher")
            for job in state.production_jobs.values()
        )
        got_here = sum(
            rec["quantity"] for rec in state.foraging_attempts.values()
            if rec["site_id"] == site
        ) + sum(
            rec["quantity"] for rec in state.gatherings.values()
            if rec["site_id"] == site
        )
        assert (
            inventory[site]["wild_food"] +
            inventory[site]["regrowth_reserve"] +
            used_by_jobs + got_here
        ) == 8
    esc = sum(contract["remaining"] for contract in
              state.courier_provisions.values())
    owned_food = sum(bal.get("food", 0) for bal in inventory.values()) + esc
    grain = sum(bal.get("grain", 0) for bal in inventory.values())
    eaten = sum(r["quantity"] for r in state.consumptions.values())
    plots = {
        k: [
            r["output_amount"] for r in state.production_recipes.values()
            if r["site_id"] == k and r.get("input_resource") == "crop_ready"
            and r["output_resource"] == "grain"
        ][0]
        for k in state.farm_plots
    }
    awaiting_bread = sum(
        state.production_recipes[j["recipe_id"]]["input_amount"]
        for j in state.production_jobs.values()
        if j["status"] == "running" and
        state.production_recipes[j["recipe_id"]].get("input_resource") == "grain"
        and state.production_recipes[j["recipe_id"]]["output_resource"] == "food"
    )
    awaiting_harvest = sum(
        plots[j["site_id"]] for j in state.production_jobs.values()
        if j["status"] == "running" and
        state.production_recipes[j["recipe_id"]].get("input_resource") == "crop_ready"
    )
    ripe = sum(inventory[k]["crop_ready"] * yield_
               for k, yield_ in plots.items())
    mature = sum(plot["matured"] * plots[site]
                 for site, plot in state.farm_plots.items())
    completed_wild = sum(
        j["status"] == "completed" and j["recipe_id"] in
        ("two-portions-hunter", "two-portions-fisher")
        for j in state.production_jobs.values()
    )
    assert owned_food + grain + eaten + awaiting_bread + awaiting_harvest + ripe == (
        INITIAL_FOOD + mature + 2 * completed_wild + taken
    )
    water = sum(inventory[k]["water"] for k in
                ("well", "farm", "farm_east", "hana", "huda")
                if "water" in inventory.get(k, {}))
    used = sum(p["started"] for p in state.farm_plots.values())
    assert water + used == (
        INITIAL_WATER + state.hydrology_sources["well"]["received_total"]
    )


def _real_world_engine(db, clock, *, community_support):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=12000,
        decision_cooldown=3600, economic_enabled=True,
        agriculture_enabled=True, navigation_enabled=True,
        routines_enabled=True, consumption_enabled=True,
        survival_enabled=True, supply_enabled=True,
        shopping_routes_enabled=True,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        professional_full_life_enabled=True,
        food_for_work_enabled=True, food_peddler_enabled=True,
        food_peddler_self_meal_reserve_enabled=True,
        seek_alternative_food_market_enabled=True,
        foraging_enabled=community_support,
        gathering_enabled=community_support,
        knowledge_enabled=community_support,
        food_navigation_enabled=community_support,
        assistance_enabled=community_support,
        aid_relay_enabled=community_support,
        scarcity_enabled=community_support,
    )


def _execute(path, *, aid):
    initial = seed(path)
    results = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = _real_world_engine(db, clock, community_support=aid)
            for hour in (6, 12, 24, 30, 36, 48):
                last = db.verify(WORLD)
                state = sim.advance(
                    WORLD, seconds=hour * HOUR - last.time,
                    command_id=f"same-world-existing-assistance:{aid}:{hour}",
                    expected_revision=last.revision).state
                assert state.time == hour*HOUR
                _universal_physical_conservation(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                metrics = measures(state)
                metrics["courier_hunger"] = {
                    who: state.npcs[who]["needs"]["hunger"]
                    for who in ("hana", "huda")
                }
                metrics["courier_meals"] = {
                    who: sum(r["npc_id"] == who for r in state.consumptions.values())
                    for who in ("hana", "huda")
                }
                metrics["source_known_local_forages"] = sum(
                    r["quantity"] for r in state.foraging_attempts.values()
                )
                metrics["source_completed_gatherings"] = sum(
                    r["quantity"] for r in state.gatherings.values()
                )
                metrics["all_owners_food_units"] = {
                    k: v.get("food", 0) for k,v in sorted(state.resources.items())
                    if v.get("food", 0) > 0
                }
                results.append(metrics)
        finally:
            clock.close_session(WORLD)
    return initial, results


def test_48h_community_routes_and_aid_without_new_resources(tmp_path):
    original, control = _execute(tmp_path/"unmodified.sqlite", aid=False)
    compare, altered = _execute(tmp_path/"existing-tools-only.sqlite", aid=True)
    assert original.to_dict() == compare.to_dict(), (
        "these worlds must have BIT-FOR-BIT identical time-zero source"
    )
    print("PLAY48_48H_EXISTING_PHYSICAL_ASSISTANCE_13NPC_AB " +
          json.dumps({"control": control, "existing_aid": altered},
                     sort_keys=True), flush=True)
    assert altered[-1]["hour"] == control[-1]["hour"] == 48
    assert altered[-1]["copper"] == control[-1]["copper"] == 12
    # No forced "GO" assertion: this is an honest physical 48h
    # characterization of existing autonomy options, not a rescue claim.
