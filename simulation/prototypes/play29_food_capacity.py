"""PLAY-29 preliminary physical food-capacity audit, pure and non-gameplay.

A deterministic upper-bound check, NOT a forecast or the real NPC planner.
Rates are taken from authenticated engine constants; no food or water changes
and no time flows except as explicit numeric input to this analysis.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction

DAY = 86400


def ceil_fraction(value: Fraction) -> int:
    return -(-value.numerator // value.denominator)


@dataclass(frozen=True)
class FoodCapacity:
    population: int
    hunger_seconds_per_point: int
    relief_points_per_food: int
    plots: int
    growth_seconds: int
    food_per_crop: int
    water_deliveries_per_day: int
    water_per_crop: int = 1

    def __post_init__(self):
        vals=(self.population,self.hunger_seconds_per_point,self.relief_points_per_food,
              self.plots,self.growth_seconds,self.food_per_crop,
              self.water_deliveries_per_day,self.water_per_crop)
        if (any(type(v) is not int for v in vals)
                or any(x <= 0 for x in (self.population, self.hunger_seconds_per_point,
                      self.relief_points_per_food, self.growth_seconds,
                      self.food_per_crop,self.water_per_crop))
                or self.plots < 0 or self.water_deliveries_per_day < 0
                or max(vals) > 2**31-1):
            raise ValueError("physical food capacity requires finite positive integer inputs")

    @property
    def steady_state_food_per_day(self) -> Fraction:
        # Continuous average over large periods; does not assume that the
        # engine serves fractional meals or overrides the hunger cap.
        return Fraction(self.population * DAY,
                        self.hunger_seconds_per_point * self.relief_points_per_food)

    @property
    def crop_supply_ceiling(self) -> Fraction:
        # Optimistic limit: assumes labor/seed/tool and field preparation
        # available without delays. Actual simulation output may be lower.
        return Fraction(self.plots * DAY * self.food_per_crop,
                        self.growth_seconds)

    @property
    def water_supply_ceiling(self) -> Fraction:
        return Fraction(self.water_deliveries_per_day * self.food_per_crop,
                        self.water_per_crop)

    @property
    def best_case_food_per_day(self) -> Fraction:
        return min(self.crop_supply_ceiling, self.water_supply_ceiling)

    @property
    def daily_shortfall_lower_bound(self) -> Fraction:
        return max(Fraction(0), self.steady_state_food_per_day
                   - self.best_case_food_per_day)

    def report(self) -> dict[str, str | int | bool]:
        return {
            "population": self.population,
            "steady_demand_ceil_rations_per_day": ceil_fraction(self.steady_state_food_per_day),
            "optimistic_production_floor_rations_per_day": self.best_case_food_per_day.numerator
              // self.best_case_food_per_day.denominator,
            "minimum_shortfall_ceil_per_day": ceil_fraction(self.daily_shortfall_lower_bound),
            "mathematically_possible_before_labor": self.best_case_food_per_day >= self.steady_state_food_per_day,
            "note": "optimistic capacity; ignores real labor, transit, hunger cap, and field preparation"
        }
