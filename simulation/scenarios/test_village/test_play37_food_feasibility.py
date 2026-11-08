"""PLAY-37: demonstrate impossibility before changing real NPC mechanics.

All arithmetic is a *necessary* lower-demand/upper-supply bound in the
physical, closed fixture. A passing feasibility test is not survival success.
"""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from play_physical_supply import DAY, WORLD, seed_physical_supply
from play37_food_feasibility import closed_test_village_feasibility


@pytest.mark.parametrize(
    "period,expected_demand,expected_deficit",
    [(300, 232, 223), (3600, 12, 3)],
)
@pytest.mark.parametrize("staff_rations", [False, True])
def test_seven_npcs_cannot_all_avoid_critical_hunger_for_72h_with_closed_stock(
        tmp_path, period, expected_demand, expected_deficit, staff_rations):
    with SQLiteEventStore(tmp_path / f"budget-{period}-{staff_rations}.sqlite") as db:
        seed_physical_supply(
            db, personal_food=0, harvest_yield=3,
            initial_market_food=3, market_wallets=True,
            hungry_market_buyers=True, staff_provisions=staff_rations,
        )
        if period == 3600:
            before = db.load(WORLD)
            db.append(
                WORLD, "slow-metabolism-at-trusted-time-zero",
                before.revision,
                [DomainEvent(
                    "MetabolismPolicyConfigured", None,
                    "frozen realistic rate for controlled survival experiment", 0,
                    {"hunger_seconds_per_point": 3600,
                     "activity_hunger_percent": 20},
                )],
                bootstrap=True,
            )
        state = db.verify(WORLD)
        before = state.to_dict()
        audit = closed_test_village_feasibility(state, horizon_seconds=3 * DAY)
        assert audit.hunger_seconds_per_point == period
        assert audit.npc_count == 7
        assert audit.initial_food_units == 3
        assert audit.finite_water_units == 2
        assert audit.physical_possible_growth_cycles == 2
        assert audit.physical_grain_yield_per_crop == 3
        assert audit.theoretical_max_food_units == 9
        assert audit.minimum_meals_to_avoid_critical_hunger == expected_demand
        assert audit.minimum_food_shortfall == expected_deficit
        assert audit.minimum_food_shortfall > 0
        assert db.verify(WORLD).to_dict() == before
        assert state.to_dict() == before


@pytest.mark.parametrize(
    "initial_water,expected_max_food",
    [(0, 3), (1, 6), (2, 9)],
)
def test_water_and_seed_provenance_bound_total_future_food(
        tmp_path, initial_water, expected_max_food):
    with SQLiteEventStore(tmp_path / f"water-{initial_water}.sqlite") as db:
        seed_physical_supply(db, water=initial_water, initial_market_food=3,
                             harvest_yield=3, hungry_market_buyers=True)
        state = db.verify(WORLD)
        lower_upper = closed_test_village_feasibility(
            state, horizon_seconds=3 * DAY,
        )
        assert lower_upper.theoretical_max_food_units == expected_max_food
        assert lower_upper.minimum_meals_to_avoid_critical_hunger == 232
        assert lower_upper.finite_water_units == initial_water


def test_critical_hunger_and_no_rest_fatigue_arrive_before_one_day_crop(tmp_path):
    with SQLiteEventStore(tmp_path / "time-mismatch.sqlite") as db:
        seed_physical_supply(db, initial_market_food=3, harvest_yield=3,
                             hungry_market_buyers=True)
        state = db.verify(WORLD)
        result = closed_test_village_feasibility(
            state, horizon_seconds=3 * DAY)
        assert result.growth_seconds_per_crop == DAY
        assert result.initial_time_to_critical_hunger_by_worker == {
            "basim": 27000, "huda": 21000, "nora": 21000,
        }
        assert result.no_rest_time_to_fatigue_block_by_worker == {
            "basim": 42000, "huda": 39000, "nora": 39000,
        }
        assert all(t < DAY for t in
                   result.initial_time_to_critical_hunger_by_worker.values())
        assert all(t < DAY for t in
                   result.no_rest_time_to_fatigue_block_by_worker.values())
        assert state.to_dict() == db.verify(WORLD).to_dict()


def test_reject_unsound_worlds_and_horizon_without_silent_zero_assumptions(tmp_path):
    with SQLiteEventStore(tmp_path / "reject-unsound.sqlite") as db:
        seed_physical_supply(db, initial_market_food=3, harvest_yield=3)
        state = db.verify(WORLD)
        for bad in (None, False, True, 0, -1, "day", 2.0):
            with pytest.raises(ValueError, match="horizon_seconds"):
                closed_test_village_feasibility(state, horizon_seconds=bad)
        assert closed_test_village_feasibility(
            state, horizon_seconds=DAY // 2,
        ).physical_possible_growth_cycles == 0
        assert closed_test_village_feasibility(
            state, horizon_seconds=DAY,
        ).physical_possible_growth_cycles == 1
        assert state.to_dict() == db.verify(WORLD).to_dict()
