"""PLAY-48R — same real 13-NPC farmland, bounded fertile-soil field scenario.

Not a magic food gift, not a new NPC. The only changed world fact is a
trusted time-zero, more productive eastern crop recipe (7 -> 12 grain per
real harvested crop, after the same real 24h growth, seed, water, tools,
worker and transport). A fertile field is a *hypothesis* to compare, not
established improved agronomy or a claim of seven-day survival.
Other 13-NPC professions (timber, charcoal) remain active as before.
"""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import DAY, WORLD
from test_play48h3_early_market_wage import _conserve, _run
from test_play48m_finite_employment import (
    _seed_employed, _joined_with_new_employment, _real_stats,
)
from test_play48q_real_food_capacity import _capacity
import test_play38_multi_farm_couriers as east

FERTILE_EAST_GRAIN_YIELD = 12
OLD_EAST_GRAIN_YIELD = 7


def _seed_fertile(path):
    # The original helper is re-used, with exactly one declared difference:
    # a bounded harvest output at t=0. Never add food or cash after creation.
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY,
            east_grain_yield=FERTILE_EAST_GRAIN_YIELD,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            bootstrap=_joined_with_new_employment,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2,
        )
        previous = db.load(WORLD)
        result = db.append(WORLD, "closure-policy", previous.revision, [
            DomainEvent(
                "WaterSourceConfigured", None, "same bounded rain", 0,
                {"site_id": "well", "capacity": 8},
            ),
            DomainEvent(
                "MetabolismPolicyConfigured", None, "same actual hunger", 0,
                {"hunger_seconds_per_point": 3600,
                 "activity_hunger_percent": 20},
            ),
        ], bootstrap=True)
        assert db.verify(WORLD).to_dict() == result.to_dict()
        return result


def _measured(state):
    economy = _real_stats(state)
    crop_jobs = {}
    for farm in ("farm", "farm_east"):
        recipe = next(
            r for r in state.production_recipes.values()
            if r["site_id"] == farm and
            r.get("input_resource") == "crop_ready"
            and r["output_resource"] == "grain"
        )
        completed = [
            job for job in state.production_jobs.values()
            if job["status"] == "completed"
            and job["recipe_id"] == recipe["id"]
        ]
        crop_jobs[farm] = {
            "grain_per_real_harvest": recipe["output_amount"],
            "completed_harvest_jobs": len(completed),
            "actual_produced_grain": len(completed) * recipe["output_amount"],
            "matured_crop_lots": state.farm_plots[farm]["matured"],
            "standing_grain": state.resources[farm]["grain"],
        }
    bread_jobs = sum(
        job["status"] == "completed" and
        state.production_recipes[job["recipe_id"]]["output_resource"] == "food"
        for job in state.production_jobs.values()
    )
    audit = audit_npc_economy(state)
    assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
    assert len(state.npcs) == 13
    return {
        "time": state.time,
        "crop_jobs": crop_jobs,
        "completed_bakery_batches": bread_jobs,
        "market_food": state.resources["market"]["food"],
        "bakery_grain": state.resources["bakery"]["grain"],
        "bakery_food": state.resources["bakery"]["food"],
        "food_sales": economy["bread_sales"],
        "meals": economy["meals"],
        "hunger_100": economy["hunger_100"],
        "charcoal_sales": economy["charcoal_sales"],
        "wood_sales": economy["wood_sales"],
        "wage_receipts": economy["wages_paid"],
        "copper_total": economy["copper_total"],
        "courier_deliveries": {
            who: state.supply_circuits[who]["deliveries"]
            for who in ("huda", "hana")
        },
        "rain_received": state.hydrology_sources["well"]["received_total"],
        "water_at_well": state.resources["well"]["water"],
    }


def test_reject_any_undeclared_field_yield_or_mutable_numeric_alias(tmp_path):
    for bad in (-1, 0, 4, 8, 11, 13, 20, True, 12.0):
        with SQLiteEventStore(tmp_path / ("bad-" + str(bad) + ".sqlite")) as db:
            with pytest.raises(ValueError, match="counterfactual"):
                east.seed_two_field_world(
                    db, east_grain_yield=bad,
                    initial_water=2, initial_market_food=3,
                )


def test_authentic_genesis_fertile_field_capacity_with_existing_finite_water(tmp_path):
    standard = _seed_employed(tmp_path / "original-real-13.sqlite")
    treatment = _seed_fertile(tmp_path / "fertile-real-13.sqlite")
    assert standard.schema_version == treatment.schema_version == 43
    assert standard.rules_version == treatment.rules_version == 58
    assert len(standard.npcs) == len(treatment.npcs) == 13
    for original in (standard, treatment):
        assert _real_stats(original)["copper_total"] == 12
        assert sum(stock.get("food", 0) for stock in original.resources.values()) == 3
        assert sum(stock.get("grain", 0) for stock in original.resources.values()) == 0
        assert sum(stock.get("water", 0) for stock in original.resources.values()) == 2
        assert original.resources["lumberyard"]["standing_timber"] == 3
        assert original.farm_plots["farm_east"]["growth_seconds"] == DAY
        assert original.production_recipes["east-seed-planting"]["input_amount"] == 1
        assert original.production_recipes["east-finite-harvest"]["input_amount"] == 1
        assert original.production_recipes["east-finite-harvest"]["tool_resource"] == "sickle"
        assert _conserve(original) == 0
    old_cap, new_cap = _capacity(standard), _capacity(treatment)
    assert old_cap["optimistic_steady_daily_two_farm_grain"] == 10
    assert new_cap["optimistic_steady_daily_two_farm_grain"] == 15
    assert old_cap["optimistic_max_bread_units_in_7days"] == 55
    assert new_cap["optimistic_max_bread_units_in_7days"] == 90
    assert old_cap["seven_day_not_all_healthy_even_with_perfect_logistics"]
    assert not new_cap["seven_day_not_all_healthy_even_with_perfect_logistics"]
    drought_cap = _capacity(treatment, recorded_future_rain=0)
    assert drought_cap["total_seven_day_water_ceiling"] == 2
    assert drought_cap["optimistic_max_bread_units_in_7days"] == 27
    assert drought_cap["seven_day_not_all_healthy_even_with_perfect_logistics"]
    for bad in (-1, 7, True, 3.5, "rain"):
        with pytest.raises(ValueError, match="rain bound"):
            _capacity(treatment, recorded_future_rain=bad)
    assert old_cap["real_initial_water"] == new_cap["real_initial_water"] == 2
    assert old_cap["total_seven_day_water_ceiling"] == new_cap["total_seven_day_water_ceiling"] == 8
    assert old_cap["minimum_real_meals_for_all_to_stay_below_hunger90"] == new_cap["minimum_real_meals_for_all_to_stay_below_hunger90"] == 61
    print("PLAY48R_FERTILE_FIELD_THEORETICAL_ONLY",
          json.dumps({
              "baseline": old_cap, "declared_fertile_field": new_cap,
              "fertile_but_no_future_rain": drought_cap,
              "changed_harvest_recipe_only_at_time_zero": True,
              "same_opening_food_seed_water_labor_and_money": True,
              "real_meals_improvement_claimed": False,
          }, sort_keys=True), flush=True)


def test_true_13npc_48h_fertile_field_harvest_vs_original(tmp_path):
    base_path = tmp_path / "13-real-original-grain7.sqlite"
    fertile_path = tmp_path / "13-real-fertile-grain12.sqlite"
    base = _seed_employed(base_path)
    fertile = _seed_fertile(fertile_path)
    assert base.time == fertile.time == 0
    checkpoints = []
    for day in (1, 2):
        left, _ = _run(
            base_path, day * DAY, early=False,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        right, _ = _run(
            fertile_path, day * DAY, early=False,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        assert left.time == right.time == day * DAY
        normal, better = _measured(left), _measured(right)
        assert normal["copper_total"] == better["copper_total"] == 12
        assert normal["rain_received"] == better["rain_received"]
        assert normal["crop_jobs"]["farm_east"]["grain_per_real_harvest"] == 7
        assert better["crop_jobs"]["farm_east"]["grain_per_real_harvest"] == 12
        for p, state in ((base_path, left), (fertile_path, right)):
            with SQLiteEventStore(p) as reopened:
                assert reopened.verify(WORLD).to_dict() == state.to_dict()
                assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert reopened.db.execute("PRAGMA foreign_key_check").fetchall() == []
        checkpoints.append({"day": day, "original": normal, "fertile": better})

    # At least one actual physically watered crop must have been cut on the
    # original and fertile plot. This is provenance, NOT a promised meal.
    old = checkpoints[-1]["original"]["crop_jobs"]["farm_east"]
    new = checkpoints[-1]["fertile"]["crop_jobs"]["farm_east"]
    assert old["completed_harvest_jobs"] >= 1
    assert new["completed_harvest_jobs"] >= 1
    assert old["actual_produced_grain"] >= 7
    assert new["actual_produced_grain"] >= 12
    print("PLAY48R_TRUE_48H_FERTILE_FIELD_A_B",
          json.dumps({
              "same_13_npcs_and_12_copper": True,
              "same_bounded_observed_rain": True,
              "only_recipe_yield_changed_at_time_zero": True,
              "checkpoints": checkpoints,
              "improved_48h_meals_observed": (
                  checkpoints[-1]["fertile"]["meals"]
                  > checkpoints[-1]["original"]["meals"]
              ),
              "improved_48h_food_sales_observed": (
                  checkpoints[-1]["fertile"]["food_sales"]
                  > checkpoints[-1]["original"]["food_sales"]
              ),
              "post72_recovery_claimed": False,
              "seven_day_stability_claimed": False,
          }, sort_keys=True), flush=True)
