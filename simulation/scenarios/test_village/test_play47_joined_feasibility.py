"""PLAY-47 feasibility: honest lower food needs vs upper physical capacity.

All assertions are applied to the actual 11-NPC joined genesis world.
The historical, narrow PLAY-37 arithmetic is a necessary bound only, not a
general scheduler or a claim that sufficient food can reach every resident.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play_physical_supply import DAY, WORLD
from play37_food_feasibility import closed_test_village_feasibility
from test_play47_joined_professions import _joined_bootstrap


@pytest.mark.parametrize(
    "days, meals, upper_loaves, minimum_shortfall",
    [(1, 107, 6, 101), (3, 360, 9, 351)],
)
def test_joined_eleven_person_closed_world_is_physically_short(
    tmp_path, days, meals, upper_loaves, minimum_shortfall,
):
    with SQLiteEventStore(tmp_path / f"joined-{days}d.sqlite") as db:
        original = _joined_bootstrap(db)
        unchanged = original.to_dict()
        result = closed_test_village_feasibility(
            original, horizon_seconds=days * DAY
        )
        assert result.npc_count == 11
        assert result.hunger_seconds_per_point == 300
        assert result.initial_food_units == 3
        assert result.finite_water_units == 2
        assert result.minimum_meals_to_avoid_critical_hunger == meals
        assert result.theoretical_max_food_units == upper_loaves
        assert result.minimum_food_shortfall == minimum_shortfall
        assert result.ideal_minimum_daily_meals_at_steady_state == 127
        assert result.ideal_max_field_loaves_per_day == 3
        assert result.ideal_max_market_delivery_loaves_per_day == 4
        assert result.ideal_max_local_market_loaves_per_day == 3
        assert result.ideal_daily_market_loaf_deficit == 124
        cash = audit_npc_economy(original)
        assert cash["copper_scope_complete"]
        assert cash["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == unchanged
        assert original.to_dict() == unchanged
        print("PLAY47_ELEVEN_NPC_FOOD_FEASIBILITY", json.dumps(
            {"days": days, "minimum_meals": meals,
             "theoretical_max_loaves": upper_loaves,
             "minimum_shortfall": minimum_shortfall,
             "daily_demand": result.ideal_minimum_daily_meals_at_steady_state,
             "daily_local_max": result.ideal_max_local_market_loaves_per_day},
            sort_keys=True,
        ))


def test_drought_reduces_optimistic_upper_bound_without_creating_water(tmp_path):
    """A finite 0-water negative world has exactly its three starting loaves."""
    with SQLiteEventStore(tmp_path / "dry-joined.sqlite") as db:
        # The fixture's explicit scarcity is a trusted t=0 input, not a
        # runtime intervention in an already-running survival experiment.
        state = _joined_bootstrap(db, water=0)
        result = closed_test_village_feasibility(
            state, horizon_seconds=3 * DAY
        )
        assert result.npc_count == 11
        assert result.finite_water_units == 0
        assert result.physical_possible_growth_cycles == 0
        assert result.theoretical_max_food_units == 3
        assert result.minimum_meals_to_avoid_critical_hunger == 360
        assert result.minimum_food_shortfall == 357
        assert db.verify(WORLD).to_dict() == state.to_dict()


def test_valid_slower_metabolism_still_exceeds_one_plot_daily_throughput(tmp_path):
    """Existing declared 3600s policy changes demand, not physical supply."""
    with SQLiteEventStore(tmp_path / "slower-joined.sqlite") as db:
        first = _joined_bootstrap(db)
        calibrated = db.append(
            WORLD, "play47:existing-slower-physiology", first.revision,
            [DomainEvent(
                "MetabolismPolicyConfigured", None,
                "trusted counterfactual with an existing registered rule", 0,
                {"hunger_seconds_per_point": 3600,
                 "activity_hunger_percent": 20},
            )],
            bootstrap=True,
        )
        result = closed_test_village_feasibility(
            calibrated, horizon_seconds=3 * DAY
        )
        assert result.npc_count == 11
        assert result.hunger_seconds_per_point == 3600
        assert result.ideal_minimum_daily_meals_at_steady_state == 11
        assert result.ideal_max_local_market_loaves_per_day == 3
        assert result.ideal_daily_market_loaf_deficit == 8
        assert result.theoretical_max_food_units == 9
        assert result.minimum_meals_to_avoid_critical_hunger == 12
        assert result.minimum_food_shortfall == 3
        assert db.verify(WORLD).to_dict() == calibrated.to_dict()
