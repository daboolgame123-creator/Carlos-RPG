"""PLAY-37: deterministic closed-village food feasibility necessary bound.

A deliberately narrow, diagnostic-only experiment for the exact test village.
Not a generic food predictor; never surfaced to Carlos/player, never mutates a
world, and never claims that meeting the bound is sufficient for survival.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from carlos_sim import WorldState
from carlos_sim.consumption import HUNGER_RELIEF_PER_FOOD
from carlos_sim.survival import FATIGUE_SECONDS_PER_POINT, hunger_period

WORKERS = ("basim", "nora", "huda")
SITES = ("farm", "bakery", "market", "well")


@dataclass(frozen=True)
class ClosedVillageFeasibility:
    horizon_seconds: int
    hunger_seconds_per_point: int
    npc_count: int
    minimum_meals_to_avoid_critical_hunger: int
    minimum_meals_by_npc: dict[str, int]
    initial_food_units: int
    finite_water_units: int
    growth_seconds_per_crop: int
    physical_possible_growth_cycles: int
    physical_grain_yield_per_crop: int
    theoretical_max_food_units: int
    minimum_food_shortfall: int
    initial_time_to_critical_hunger_by_worker: dict[str, int]
    no_rest_time_to_fatigue_block_by_worker: dict[str, int]

    def to_dict(self) -> dict:
        return asdict(self)


def closed_test_village_feasibility(
    state: WorldState, *, horizon_seconds: int,
) -> ClosedVillageFeasibility:
    """Compute a *necessary* upper-supply/lower-demand feasibility test.

    Only accepts fresh, physically initialized PLAY-27-style test villages:
    one fixed-size plot, one baker route, no outside food source, rain,
    environment replenishment or stock added after t=0. A closed-world
    impossibility result here must not be applied to open ecosystems.
    """
    if not isinstance(state, WorldState):
        raise TypeError("validated WorldState expected")
    if type(horizon_seconds) is not int or horizon_seconds <= 0:
        raise ValueError("horizon_seconds must be a positive integer")
    if (state.time != 0 or state.survival_progress or state.consumptions
            or state.market_trades or state.production_jobs
            or state.hydrology_sources or state.environment_cycles
            or any(k not in state.locations for k in SITES)
            or any(k not in state.npcs for k in WORKERS)
            or len(state.farm_plots) != 1 or "farm" not in state.farm_plots
            or len(state.supply_circuits) != 1 or "huda" not in state.supply_circuits):
        raise ValueError("requires fresh closed test village without external food/water")
    plot = state.farm_plots["farm"]
    if (plot["capacity"] != 1 or plot["status"] != "idle"
            or plot["started"] != 0 or plot["matured"] != 0):
        raise ValueError("only one unchanged empty starting farm supported")

    def stock(owner, resource, *, missing_ok=False):
        if owner not in state.resources:
            raise ValueError("expected initialized physical owner")
        n = state.resources[owner].get(resource)
        if n is None and missing_ok:
            return 0
        if type(n) is not int or n < 0:
            raise ValueError("unknown or invalid physical input is not zero")
        return n

    # The scenario's only food can be in physical NPC or site-owned stock,
    # regardless of market-first or trusted staff-prepositioned allocation.
    actors = tuple(sorted(state.npcs))
    # All seven NPC food balances must be *explicitly initialized*. Missing
    # food for any NPC is UNKNOWN and is rejected, not counted as zero.
    known_food = sum(stock(site, "food") for site in ("market", "bakery"))
    known_food += sum(stock(who, "food") for who in actors)
    # This disposable world has an uninitialized player food balance by
    # default. It is not a spendable stock and no player command is run.
    # If a playable fixture initializes a balance, audit it explicitly.
    if "food" in state.resources.get("carlos", {}):
        known_food += stock("carlos", "food")
    if any(stock("farm", k) != 0 for k in ("grain", "crop_ready", "crop_seeded")):
        raise ValueError("existing crop/grain requires a different feasibility model")
    if stock("bakery", "grain") != 0:
        raise ValueError("existing bakery grain requires a different model")
    if any(bal.get("wild_food", 0) for bal in state.resources.values()):
        raise ValueError("wild food requires a separate finite-source audit")
    if any(bal.get("food", 0) not in (0, None) for who, bal in state.resources.items()
           if who not in ("market", "bakery", *actors)):
        raise ValueError("unexpected food stock outside the tested supply chain")

    available_water = sum(stock(owner, "water", missing_ok=True)
                          for owner in state.resources)
    if stock("farm", "seed") < 1:
        upper_cycles = 0
    else:
        # Maturation *returns* a seed. Water is consumed each time and here
        # has no renewable attested rain source; this is an optimistic ceiling.
        upper_cycles = min(available_water, horizon_seconds // plot["growth_seconds"])
    recipe = state.production_recipes.get("finite-harvest")
    bakery = state.production_recipes.get("grain-to-bread")
    if (recipe is None or recipe["site_id"] != "farm"
            or recipe["input_resource"] != "crop_ready"
            or recipe["input_amount"] != 1
            or recipe["output_resource"] != "grain"
            or type(recipe["output_amount"]) is not int
            or recipe["output_amount"] < 1
            or bakery is None or bakery["site_id"] != "bakery"
            or bakery["input_resource"] != "grain"
            or bakery["input_amount"] != 1
            or bakery["output_resource"] != "food"
            or bakery["output_amount"] != 1):
        raise ValueError("unrecognized crop-to-bread material recipes")
    max_total_food = known_food + upper_cycles * recipe["output_amount"]
    period = hunger_period(state.to_dict())
    increase = horizon_seconds // period
    minimum = {
        who: max(0, (npc["needs"]["hunger"] + increase - 89
                 + HUNGER_RELIEF_PER_FOOD - 1) // HUNGER_RELIEF_PER_FOOD)
        for who, npc in sorted(state.npcs.items())
    }
    # This is the *optimistic* lower bound to keep all NPC hunger <90
    # continuously. No activity costs are counted. It is invalid as a
    # proof of success even if supply >= demand due to nonlocal ownership.
    total = sum(minimum.values())
    worker_critical = {
        who: max(0, 90 - state.npcs[who]["needs"]["hunger"]) * period
        for who in WORKERS
    }
    # Focused economy-only mode has no general rest decisions. These are
    # hypothetical no-rest times, NOT a claim about full autonomous mode.
    worker_fatigue = {
        who: max(0, 70 - state.npcs[who]["needs"]["fatigue"])
             * FATIGUE_SECONDS_PER_POINT
        for who in WORKERS
    }
    return ClosedVillageFeasibility(
        horizon_seconds=horizon_seconds, hunger_seconds_per_point=period,
        npc_count=len(state.npcs),
        minimum_meals_to_avoid_critical_hunger=total,
        minimum_meals_by_npc=minimum,
        initial_food_units=known_food,
        finite_water_units=available_water,
        growth_seconds_per_crop=plot["growth_seconds"],
        physical_possible_growth_cycles=upper_cycles,
        physical_grain_yield_per_crop=recipe["output_amount"],
        theoretical_max_food_units=max_total_food,
        minimum_food_shortfall=max(0, total - max_total_food),
        initial_time_to_critical_hunger_by_worker=worker_critical,
        no_rest_time_to_fatigue_block_by_worker=worker_fatigue,
    )
