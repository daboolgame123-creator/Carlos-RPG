"""PLAY48 watch-income real 48h *observational* continuation.

Operator snapshots diagnose why the physically linked 24h improvement ends:
actual employer and worker stock, needs, signed jobs, market demand, and trips.
No new actions/rain/food/currency, no scripted NPC decisions. An observed
72h recovery is NOT claimed. The historical full source remains available.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.routines import routine_allows_work
from test_play38_multi_farm_couriers import WORLD
from test_play48_real_watch_income_24h import seed, engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures


def audit_local_stall_gates(state):
    actors = {}
    for who, npc in sorted(state.npcs.items()):
        needs = npc["needs"]
        owned = state.resources.get(who, {})
        eligible = []
        here = state.entities[who]["location_id"]
        working = routine_allows_work(state, who)
        for recipe_id, recipe in sorted(state.production_recipes.items()):
            if recipe["site_id"] != here or recipe["role"] != npc["role"]:
                continue
            local = state.resources.get(here, {})
            output = local.get(recipe["output_resource"])
            input_amount = local.get(recipe["input_resource"])
            eligible.append({
                "recipe": recipe_id, "in_stock": input_amount,
                "needed": recipe["input_amount"], "output_stock": output,
                "work_shift_ok": working,
                "hunger_block": needs["hunger"] > 89,
                "fatigue_block": needs["fatigue"] > 69,
                "material_block": (input_amount is None or
                                   input_amount < recipe["input_amount"]),
            })
        actors[who] = {
            "hunger": needs["hunger"], "fatigue": needs["fatigue"],
            "site": here, "own_food": owned.get("food", 0),
            "own_copper": owned.get("coin_copper", 0),
            "workplace": state.npc_routines.get(who, {}).get("workplace_id"),
            "known_local_recipes": eligible,
        }
    offers = {
        ident: {
            "site": q["site_id"], "seller": q["seller_id"],
            "owner": q["stock_owner_id"], "resource": q["resource"],
            "price": q["unit_price"], "status": q["status"],
            "remaining": q["remaining"],
            "physical_stock": state.resources[q["stock_owner_id"]].get(q["resource"]),
        }
        for ident, q in sorted(state.market_offers.items())
        if q["resource"] == "food" and q["status"] == "open"
    }
    recipes = {}
    for ident, recipe in sorted(state.production_recipes.items()):
        jobs = [j for j in state.production_jobs.values()
                if j["recipe_id"] == ident]
        recipes[ident] = {
            "completed": sum(j["status"] == "completed" for j in jobs),
            "running": sum(j["status"] == "running" for j in jobs),
            "unpaid_completed": sum(j["status"] == "completed"
                                    and recipe.get("wage_coin") is not None
                                    and "work_wage" not in j
                                    or j["status"] == "completed"
                                    and recipe.get("wage_food") is not None
                                    and "food_wage" not in j for j in jobs),
            "employer_cash": state.resources[recipe["site_id"]].get("coin_copper", 0),
            "employer_food": state.resources[recipe["site_id"]].get("food", 0),
        }
    return {"workers": actors, "food_quotes": offers,
            "production_by_recipe": recipes, "copper": {
                k: v for k, v in sorted(audit_npc_economy(state)["copper_known_by_owner"].items())
                if v > 0}}


def test_same_actual_guard_world_exposes_48h_stop_gates_without_intervention(tmp_path):
    path = tmp_path / "real-48h-next-day-gates.sqlite"
    first = seed(path)
    assert len(first.npcs) == 13
    readings = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner = engine(db, clock)
            for hour in (6, 12, 24, 30, 36, 48):
                previous = db.verify(WORLD)
                state = runner.advance(
                    WORLD, seconds=hour * HOUR - previous.time,
                    expected_revision=previous.revision,
                    command_id=f"same-signed-guard-48h:{hour}",
                ).state
                assert len(state.npcs) == 13
                assert state.time == hour * HOUR
                conserve_diverse(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                cash = audit_npc_economy(state)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"] == 12
                current = measures(state)
                current["gates"] = audit_local_stall_gates(state)
                readings.append(current)
                print("PLAY48_REAL_48H_POST24_PRODUCTION_GATES " +
                      json.dumps(current, sort_keys=True), flush=True)
            assert readings[-1]["hour"] == 48
            assert readings[-1]["copper"] == 12
        finally:
            clock.close_session(WORLD)
