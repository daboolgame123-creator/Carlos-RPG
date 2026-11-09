"""PLAY-47: measure actual workforce cost before hypothetical extra farms.

Uses the *same* eleven-NPC world seeded by the real integrated survival test.
No post-genesis food, funds, rain or extra farmers are introduced.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.consumption import HUNGER_RELIEF_PER_FOOD
from carlos_sim.survival import hunger_period
from play37_food_feasibility import closed_test_village_feasibility
from play_physical_supply import WORLD, DAY
from play47_net_food_capacity import FoodCapacityParameters
from test_play47_joined_professions import _joined_bootstrap


def _from_live_genesis(state):
    report = closed_test_village_feasibility(state, horizon_seconds=3 * DAY)
    plot = state.farm_plots["farm"]
    courier = state.supply_circuits["huda"]
    # This exact-world fit is narrower than a generic resource estimator.
    assert len(state.farm_plots) == len(state.supply_circuits) == 1
    assert report.physical_grain_yield_per_crop == 3
    return FoodCapacityParameters(
        original_npcs=len(state.npcs),
        current_plots=1, current_couriers=1,
        plot_yield_loaves=report.physical_grain_yield_per_crop,
        plot_growth_seconds=plot["growth_seconds"],
        courier_period_seconds=courier["period_seconds"],
        courier_food_per_trip=1,
        hunger_seconds_per_point=hunger_period(state.to_dict()),
        relief_points_per_meal=HUNGER_RELIEF_PER_FOOD,
        current_known_food=report.initial_food_units,
        current_known_water=report.finite_water_units,
    )


def test_default_meal_demand_outgrows_hypothetical_additional_workers(tmp_path):
    with SQLiteEventStore(tmp_path / "default-carrying-capacity.sqlite") as db:
        state = _joined_bootstrap(db)
        initial_dict = state.to_dict()
        envelope = _from_live_genesis(state)
        baseline = envelope.evaluate(1, 1)
        assert (baseline.npc_count, baseline.daily_minimum_meals,
                baseline.daily_market_upper_loaves,
                baseline.daily_shortfall_lower_bound) == (11, 127, 3, 124)
        # A proposed farm without a new farm worker is *not* valid in this model.
        expanded = envelope.evaluate(8, 6)
        assert expanded.added_npcs == 12
        assert expanded.npc_count == 23
        assert expanded.daily_minimum_meals == 265
        assert expanded.daily_market_upper_loaves == 24
        assert expanded.daily_shortfall_lower_bound == 241
        # No feasible pair under a generously bounded search. The model does
        # not assert an unbounded theorem from a finite search.
        assert envelope.fewest_additional_workers_candidate(
            max_plots=64, max_couriers=64
        ) is None
        assert db.verify(WORLD).to_dict() == initial_dict
        assert state.to_dict() == initial_dict


def test_slower_existing_policy_needs_eight_fields_six_couriers_AND_water(tmp_path):
    with SQLiteEventStore(tmp_path / "slow-carrying-capacity.sqlite") as db:
        first = _joined_bootstrap(db)
        calibrated = db.append(
            WORLD, "play47:net-capacity-slower-policy", first.revision,
            [DomainEvent(
                "MetabolismPolicyConfigured", None,
                "trusted time-zero policy comparison, no actual food transfer", 0,
                {"hunger_seconds_per_point": 3600,
                 "activity_hunger_percent": 20},
            )],
            bootstrap=True,
        )
        envelope = _from_live_genesis(calibrated)
        baseline = envelope.evaluate(1, 1)
        assert (baseline.npc_count, baseline.daily_minimum_meals,
                baseline.daily_market_upper_loaves) == (11, 11, 3)
        optimal = envelope.fewest_additional_workers_candidate(
            max_plots=20, max_couriers=20, horizon_days=3
        )
        assert optimal is not None
        assert (optimal.plots, optimal.couriers, optimal.npc_count) == (8, 6, 23)
        assert optimal.added_npcs == 12
        assert optimal.daily_minimum_meals == 23
        assert optimal.daily_plot_upper_loaves == 24
        assert optimal.daily_transport_upper_loaves == 24
        assert optimal.daily_shortfall_lower_bound == 0
        assert optimal.water_observed_at_t0 == 2
        assert optimal.hypothetical_future_water == 0
        assert optimal.water_scenario_total == 2
        assert optimal.water_for_full_plot_utilization == 24
        assert optimal.water_missing_for_full_utilization == 22
        assert optimal.horizon_market_upper_loaves_with_water == 9
        # Only actual recorded rainfall could meet the extra requirement.
        hypothetical = replace(envelope, hypothetical_future_water=22)
        wetted = hypothetical.evaluate(8, 6, horizon_days=3)
        assert wetted.water_missing_for_full_utilization == 0
        assert wetted.water_observed_at_t0 == 2
        assert wetted.hypothetical_future_water == 22
        assert wetted.water_scenario_total == 24
        assert wetted.horizon_market_upper_loaves_with_water == 75
        assert db.verify(WORLD).to_dict() == calibrated.to_dict()
        # The hypothetical water is NOT an event or a credit to this world.
        assert calibrated.resources == db.load(WORLD).resources


def test_bounded_water_and_vehicle_ceiling_do_not_double_count_opening_food():
    e = FoodCapacityParameters(
        original_npcs=11, current_plots=1, current_couriers=1,
        plot_yield_loaves=3, plot_growth_seconds=DAY,
        courier_period_seconds=DAY // 4, courier_food_per_trip=1,
        hunger_seconds_per_point=3600, relief_points_per_meal=25,
        current_known_food=3, current_known_water=0,
    )
    result = e.evaluate(8, 6, horizon_days=3)
    assert result.horizon_crop_upper_loaves_with_water == 0
    assert result.horizon_market_upper_loaves_with_water == 3
    assert result.water_missing_for_full_utilization == 24
    assert e.fewest_additional_workers_candidate(
        max_plots=3, max_couriers=3
    ) is None


@pytest.mark.parametrize(
    "override", [
        {"original_npcs": True}, {"hunger_seconds_per_point": 0},
        {"current_known_water": -1}, {"plot_growth_seconds": 0},
    ],
)
def test_capacity_envelope_rejects_invalid_or_unknown_inputs(override):
    args = dict(
        original_npcs=11, current_plots=1, current_couriers=1,
        plot_yield_loaves=3, plot_growth_seconds=DAY,
        courier_period_seconds=DAY//4, courier_food_per_trip=1,
        hunger_seconds_per_point=3600, relief_points_per_meal=25,
        current_known_food=3, current_known_water=2,
    )
    args.update(override)
    with pytest.raises(ValueError):
        FoodCapacityParameters(**args)


@pytest.mark.parametrize("plots,couriers,days", [
    (0, 1, 3), (1, -1, 3), (1, 1, 0), (True, 1, 3),
])
def test_capacity_envelope_rejects_impossible_population_inputs(plots, couriers, days):
    e = FoodCapacityParameters(
        original_npcs=11, current_plots=1, current_couriers=1,
        plot_yield_loaves=3, plot_growth_seconds=DAY,
        courier_period_seconds=DAY//4, courier_food_per_trip=1,
        hunger_seconds_per_point=3600, relief_points_per_meal=25,
        current_known_food=3, current_known_water=2,
    )
    with pytest.raises(ValueError):
        e.evaluate(plots, couriers, horizon_days=days)
