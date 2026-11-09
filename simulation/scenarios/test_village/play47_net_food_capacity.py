"""PLAY-47 read-only *necessary* food capacity envelope with labor feedback.

Do not pass this operator-only planning model to an NPC. It predicts neither
successful physical journeys nor actual harvests, starvation, prices or wages.
It does not authorize any resource creation, rain, new worker, or saved-state
migration. Every extra field and courier in the model needs one *additional*
full food-consuming resident; no free labor is assumed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

DAY = 86_400


def _positive(name: str, number: int) -> None:
    if type(number) is not int or number < 1:
        raise ValueError(f"{name} must be a positive integer")


def _nonnegative(name: str, number: int) -> None:
    if type(number) is not int or number < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _ceil_div(n: int, d: int) -> int:
    return (n + d - 1) // d


@dataclass(frozen=True)
class NetCapacity:
    plots: int
    couriers: int
    npc_count: int
    added_npcs: int
    daily_minimum_meals: int
    daily_plot_upper_loaves: int
    daily_transport_upper_loaves: int
    daily_market_upper_loaves: int
    daily_shortfall_lower_bound: int
    model_passes_steady_daily_throughput: bool
    horizon_days: int
    water_observed_at_t0: int
    hypothetical_future_water: int
    water_scenario_total: int
    water_for_full_plot_utilization: int
    water_missing_for_full_utilization: int
    horizon_crop_upper_loaves_with_water: int
    horizon_market_upper_loaves_with_water: int

    @property
    def theoretical_steady_feasible(self) -> bool:
        return self.model_passes_steady_daily_throughput


@dataclass(frozen=True)
class FoodCapacityParameters:
    original_npcs: int
    current_plots: int
    current_couriers: int
    plot_yield_loaves: int
    plot_growth_seconds: int
    courier_period_seconds: int
    courier_food_per_trip: int
    hunger_seconds_per_point: int
    relief_points_per_meal: int
    current_known_food: int
    current_known_water: int
    hypothetical_future_water: int = 0

    def __post_init__(self) -> None:
        for key in (
            "original_npcs", "current_plots", "current_couriers",
            "plot_yield_loaves", "plot_growth_seconds",
            "courier_period_seconds", "courier_food_per_trip",
            "hunger_seconds_per_point", "relief_points_per_meal",
        ):
            _positive(key, getattr(self, key))
        for key in ("current_known_food", "current_known_water",
                    "hypothetical_future_water"):
            _nonnegative(key, getattr(self, key))
        if self.original_npcs < self.current_plots + self.current_couriers:
            raise ValueError("original population cannot be smaller than assigned farm and delivery workforce")

    def evaluate(self, plots: int, couriers: int, *, horizon_days: int = 3) -> NetCapacity:
        _positive("plots", plots)
        _positive("couriers", couriers)
        _positive("horizon_days", horizon_days)
        if plots < self.current_plots or couriers < self.current_couriers:
            raise ValueError("cannot shrink an existing village in a capacity addition")
        added_npcs = (plots - self.current_plots) + (couriers - self.current_couriers)
        population = self.original_npcs + added_npcs
        daily_food = _ceil_div(
            population * DAY,
            self.hunger_seconds_per_point * self.relief_points_per_meal,
        )
        plot_daily = (DAY // self.plot_growth_seconds) * self.plot_yield_loaves * plots
        courier_daily = (DAY // self.courier_period_seconds) * self.courier_food_per_trip * couriers
        # One configured circuit serves one field. Surplus capacity on
        # another field's circuit cannot move an unserved field's grain.
        served_plots = min(plots, couriers)
        served_plot_daily = (
            (DAY // self.plot_growth_seconds) * self.plot_yield_loaves * served_plots
        )
        local_daily = min(served_plot_daily, courier_daily)
        all_possible_cycles = (horizon_days * DAY // self.plot_growth_seconds) * plots
        water = self.current_known_water + self.hypothetical_future_water
        crop_upper = min(all_possible_cycles, water) * self.plot_yield_loaves
        served_crop_upper = min(
            (horizon_days * DAY // self.plot_growth_seconds) * served_plots, water,
        ) * self.plot_yield_loaves
        transported_upper = (
            horizon_days * DAY // self.courier_period_seconds
        ) * self.courier_food_per_trip * couriers
        return NetCapacity(
            plots=plots,
            couriers=couriers,
            npc_count=population,
            added_npcs=added_npcs,
            daily_minimum_meals=daily_food,
            daily_plot_upper_loaves=plot_daily,
            daily_transport_upper_loaves=courier_daily,
            daily_market_upper_loaves=local_daily,
            daily_shortfall_lower_bound=max(0, daily_food - local_daily),
            model_passes_steady_daily_throughput=local_daily >= daily_food,
            horizon_days=horizon_days,
            water_observed_at_t0=self.current_known_water,
            hypothetical_future_water=self.hypothetical_future_water,
            water_scenario_total=water,
            water_for_full_plot_utilization=all_possible_cycles,
            water_missing_for_full_utilization=max(0, all_possible_cycles - water),
            horizon_crop_upper_loaves_with_water=crop_upper,
            horizon_market_upper_loaves_with_water=(
                self.current_known_food + min(served_crop_upper, transported_upper)
            ),
        )

    def fewest_additional_workers_candidate(
        self, *, max_plots: int, max_couriers: int, horizon_days: int = 3,
    ) -> Optional[NetCapacity]:
        """Search bounded theoretical throughput only; DOES NOT invent workers.

        A returned candidate includes the demand of all hypothetical workers.
        It is not authorization to seed them or evidence of feasible ownership,
        roads, water, crop delays, baker labor or household food distribution.
        """
        _positive("max_plots", max_plots)
        _positive("max_couriers", max_couriers)
        _positive("horizon_days", horizon_days)
        if max_plots < self.current_plots or max_couriers < self.current_couriers:
            raise ValueError("capacity search must include the actual baseline")
        best: NetCapacity | None = None
        for plots in range(self.current_plots, max_plots + 1):
            for couriers in range(self.current_couriers, max_couriers + 1):
                candidate = self.evaluate(
                    plots, couriers, horizon_days=horizon_days
                )
                if not candidate.theoretical_steady_feasible:
                    continue
                if best is None or (
                    candidate.added_npcs, candidate.plots, candidate.couriers
                ) < (best.added_npcs, best.plots, best.couriers):
                    best = candidate
        return best
