"""PLAY-48Q: audit closed 13-person food-chain carrying capacity, not policy.

This operator-only analytic upper/lower bound reuses the real PLAY-48M
genesis, actual one-day crop growth and calorie/hunger contracts. The eight
water units are a GENEROUS upper bound: the opening two physical units plus
the existing 2+2+2 observed-weather test receipts through day three. No rain
or food event is actually written by this audit. It cannot drive NPC decisions.
"""
from __future__ import annotations

import json
from math import ceil

from carlos_sim import SQLiteEventStore
from carlos_sim.consumption import HUNGER_RELIEF_PER_FOOD
from carlos_sim.survival import hunger_period
from carlos_sim.bakery_buffer import GRAIN_TARGET
from test_play47_closure_endurance import DAY, WORLD
from test_play48m_finite_employment import _seed_employed

HORIZON_DAYS = 7
# Exactly the weather already used by PLAY-48O's genuine 13-NPC 96h
# experiment. Future days 4-7 receive no documented additional rainfall.
OBSERVED_BOUNDED_FUTURE_RAIN = (2, 2, 2)


def _capacity(state):
    frozen = state.to_dict()
    assert len(state.npcs) == 13
    assert state.time == 0
    period = hunger_period(frozen)
    per_meal = HUNGER_RELIEF_PER_FOOD
    assert period > 0 and per_meal > 0

    farm_caps = []
    for site_id, plot in sorted(state.farm_plots.items()):
        crops = [
            recipe for recipe in state.production_recipes.values()
            if recipe["site_id"] == site_id
            and recipe["input_resource"] == "crop_ready"
            and recipe["output_resource"] == "grain"
        ]
        assert len(crops) == 1
        assert crops[0]["input_amount"] == 1
        max_cycles = HORIZON_DAYS * DAY // plot["growth_seconds"]
        farm_caps.append({
            "farm": site_id,
            "max_growth_cycles_even_if_perfect": max_cycles,
            "grain_per_crop": crops[0]["output_amount"],
            "max_daily_grain_at_continuous_full_water":
                (DAY // plot["growth_seconds"]) * crops[0]["output_amount"],
        })
    assert len(farm_caps) == 2
    bakery = state.production_recipes["grain-to-bread"]
    assert bakery["input_resource"] == "grain"
    assert bakery["input_amount"] == bakery["output_amount"] == 1
    assert bakery["output_resource"] == "food"

    initial_food = sum(
        stock.get("food", 0) for stock in state.resources.values()
    )
    initial_grain = sum(
        stock.get("grain", 0) for stock in state.resources.values()
    )
    initial_water = sum(
        stock.get("water", 0) for stock in state.resources.values()
    )
    assert initial_food == 3
    assert initial_grain == 0
    assert initial_water == 2
    assert set(OBSERVED_BOUNDED_FUTURE_RAIN) == {2}
    water_ceiling = initial_water + sum(OBSERVED_BOUNDED_FUTURE_RAIN)

    # Optimistic allocation: use each of the strictly finite water units
    # where the physically configured grain yield is greatest. This ignores
    # worker fatigue, actual courier delays and crop scheduling, so can only
    # overestimate real grain production in the same two-field channel.
    water_remaining = water_ceiling
    upper_grain = initial_grain
    allocation = []
    for farm in sorted(farm_caps, key=lambda p: -p["grain_per_crop"]):
        watered_cycles = min(water_remaining, farm["max_growth_cycles_even_if_perfect"])
        upper_grain += watered_cycles * farm["grain_per_crop"]
        water_remaining -= watered_cycles
        allocation.append({"farm": farm["farm"], "watered_cycles": watered_cycles})

    # An optimistic logistics ceiling for the configured courier circuits.
    # It assumes each physical circuit completes every scheduled departure,
    # carries one real bakery food unit, and all workers remain capable.
    # The actual simulation proves those optimistic assumptions fail.
    courier_market_upper = sum(
        DAY // circuit["period_seconds"]
        for circuit in state.supply_circuits.values()
        if circuit["stops"][2:4] == ["bakery", "market"]
    )

    # If none of these 13 citizens ever reaches hunger 90, every citizen
    # must consume at least this many genuine loaves by the end of day 7,
    # even with PERFECT distribution and ignoring additional work hunger.
    # The lower bound excludes exhaustion/drought and cannot overstate needs.
    projected_hunger_points = HORIZON_DAYS * DAY // period
    minimum_meals_by_actor = {
        who: max(0, ceil(
            (npc["needs"]["hunger"] + projected_hunger_points - 89) / per_meal
        ))
        for who, npc in sorted(state.npcs.items())
    }
    min_meals_for_all_below_90 = sum(minimum_meals_by_actor.values())
    steady_daily_required = ceil(
        len(state.npcs) * DAY / (period * per_meal)
    )
    steady_daily_grain_ceiling = sum(
        f["max_daily_grain_at_continuous_full_water"] for f in farm_caps
    )
    assert state.to_dict() == frozen
    return {
        "people": len(state.npcs),
        "horizon_days": HORIZON_DAYS,
        "hunger_seconds_per_point": period,
        "relief_points_per_real_meal": per_meal,
        "real_initial_bread": initial_food,
        "real_initial_grain": initial_grain,
        "real_initial_water": initial_water,
        "assumed_observed_later_rain_total": sum(OBSERVED_BOUNDED_FUTURE_RAIN),
        "total_seven_day_water_ceiling": water_ceiling,
        "farm_yields": farm_caps,
        "optimistic_water_allocation": allocation,
        "optimistic_max_bread_units_in_7days": initial_food + upper_grain,
        "minimum_real_meals_for_all_to_stay_below_hunger90": min_meals_for_all_below_90,
        "minimum_meals_per_person": minimum_meals_by_actor,
        "necessary_steady_daily_meals": steady_daily_required,
        "optimistic_steady_daily_two_farm_grain": steady_daily_grain_ceiling,
        "optimistic_scheduled_courier_market_loaves_per_day":
            courier_market_upper,
        "market_transport_not_theoretical_capacity_bottleneck":
            courier_market_upper >= steady_daily_required,
        "structural_daily_deficit_even_with_unlimited_water":
            max(0, steady_daily_required - steady_daily_grain_ceiling),
        "seven_day_not_all_healthy_even_with_perfect_logistics":
            min_meals_for_all_below_90 > initial_food + upper_grain,
        # Pure counterfactual upper bound, NOT actual food at t=0 or license to mint.
        "counterfactual_extra_preexisting_grain_reserve": GRAIN_TARGET,
        "counterfactual_max_with_real_prior_funded_reserve":
            initial_food + upper_grain + GRAIN_TARGET,
        "reserve_alone_is_not_sufficient":
            min_meals_for_all_below_90 > initial_food + upper_grain + GRAIN_TARGET,
        "not_a_survival_trajectory": True,
    }


def test_authentic_13_npc_seven_day_optimistic_food_capacity(tmp_path):
    path = tmp_path / "play48q-snapshot.sqlite"
    state = _seed_employed(path)
    before = state.to_dict()
    report = _capacity(state)
    assert report["people"] == 13
    assert report["necessary_steady_daily_meals"] == 13
    assert report["optimistic_steady_daily_two_farm_grain"] == 10
    assert report["structural_daily_deficit_even_with_unlimited_water"] == 3
    assert report["optimistic_scheduled_courier_market_loaves_per_day"] == 52
    assert report["market_transport_not_theoretical_capacity_bottleneck"]
    assert report["total_seven_day_water_ceiling"] == 8
    assert report["optimistic_max_bread_units_in_7days"] == 55
    assert report["seven_day_not_all_healthy_even_with_perfect_logistics"]
    assert report["minimum_real_meals_for_all_to_stay_below_hunger90"] == 61
    assert report["counterfactual_extra_preexisting_grain_reserve"] == 3
    assert report["counterfactual_max_with_real_prior_funded_reserve"] == 58
    assert report["reserve_alone_is_not_sufficient"]
    assert before == state.to_dict()
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == before
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    print("PLAY48Q_AUTHENTIC_13NPC_FOOD_CAPACITY",
          json.dumps(report, sort_keys=True), flush=True)
