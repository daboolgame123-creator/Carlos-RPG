"""Pure PLAY-29 economy sizing: no claim of long-term simulation success."""
from fractions import Fraction
import pytest
from prototypes.play29_food_capacity import DAY, FoodCapacity, ceil_fraction

def model(*, seconds=300, plots=1, water=1, output=1):
    return FoodCapacity(population=7, hunger_seconds_per_point=seconds,
                        relief_points_per_food=25, plots=plots,
                        growth_seconds=DAY, food_per_crop=output,
                        water_deliveries_per_day=water)

def test_actual_engine_current_hunger_rate_implies_structural_shortfall():
    m=model()
    assert m.steady_state_food_per_day == Fraction(2016,25)
    assert ceil_fraction(m.steady_state_food_per_day) == 81
    assert m.best_case_food_per_day == 1
    assert m.daily_shortfall_lower_bound == Fraction(1991,25)
    assert m.report()["mathematically_possible_before_labor"] is False

def test_rain_fixes_a_real_water_limit_not_automatically_nutrition():
    dry=model(plots=2,water=1)
    rainy=model(plots=2,water=2)
    assert dry.best_case_food_per_day == 1
    assert rainy.best_case_food_per_day == 2
    assert rainy.daily_shortfall_lower_bound > 0
    assert rainy.best_case_food_per_day > dry.best_case_food_per_day

def test_no_water_means_no_crops_even_with_hundred_plots():
    m=model(plots=100,water=0)
    assert m.best_case_food_per_day == 0
    assert m.report()["minimum_shortfall_ceil_per_day"] == 81

def test_no_land_means_no_crops_even_with_hundred_rainfall_units():
    assert model(plots=0,water=100).best_case_food_per_day == 0

def test_hypothetical_slower_metabolism_still_needs_real_land_and_water():
    one=model(seconds=3600,plots=1,water=1)
    seven=model(seconds=3600,plots=7,water=7)
    assert one.steady_state_food_per_day == Fraction(168,25)
    assert one.best_case_food_per_day == 1
    assert seven.best_case_food_per_day == 7
    assert seven.report()["mathematically_possible_before_labor"] is True
    # This does NOT change the engine's HUNGER_SECONDS_PER_POINT=300.

def test_higher_yield_must_still_use_real_plots_and_water():
    m=model(plots=2,water=1,output=2)
    assert m.best_case_food_per_day == 2
    assert m.crop_supply_ceiling == 4
    assert m.water_supply_ceiling == 2

def test_partial_day_maturation_is_not_instant_production():
    m=FoodCapacity(population=7,hunger_seconds_per_point=300,relief_points_per_food=25,
                   plots=1,growth_seconds=2*DAY,food_per_crop=1,
                   water_deliveries_per_day=10)
    assert m.best_case_food_per_day == Fraction(1,2)

@pytest.mark.parametrize("bad",[-1,True,1.5,None,"3"])
def test_invalid_population_is_rejected(bad):
    with pytest.raises(ValueError):
        FoodCapacity(population=bad,hunger_seconds_per_point=300,
                     relief_points_per_food=25,plots=1,growth_seconds=DAY,
                     food_per_crop=1,water_deliveries_per_day=1)

def test_report_is_stable_and_does_not_mutate_the_game():
    x=model()
    assert x.report() == x.report()
    assert "ignores real labor" in x.report()["note"]
