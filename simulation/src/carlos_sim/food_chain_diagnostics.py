"""Internal, read-only bottleneck audit for finite NPC food supply chains.

This is NOT a player-visible projection and never interprets unknown stock as
zero. Event ledgers and physical balances are counted separately: open market
offers never create or double-count food. No event creation or economic policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .domain import WorldState
from .food_security_audit import audit_food_security
from .supply import choose_courier_leg


@dataclass(frozen=True)
class FoodChainDiagnosis:
    logical_time: int
    hunger_at_cap: tuple[str, ...]
    high_risk_without_food: tuple[str, ...]
    food_unknown_npcs: tuple[str, ...]
    personal_food_units: int
    market_food: int | None
    bakery_food: int | None
    bakery_grain: int | None
    farm_grain: int | None
    farm_crop_ready: int | None
    farm_seed: int | None
    farm_water: int | None
    harvested_crop_lots: int
    field_growth_status: str
    field_growth_due: int | None
    completed_bread_batches: int
    completed_bread_units: int
    market_open_units: int
    trades: int
    traded_food_units: int
    eaten_food_units: int
    known_copper_total: int
    courier_deliveries: int
    courier_carry_resource: str | None
    courier_location: str
    courier_route_index: int
    courier_hunger: int
    courier_fatigue: int
    courier_leg_reason: str
    essential_workers_hunger_blocked: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _owned_amount(state: WorldState, owner_id: str, resource: str) -> int | None:
    val = state.resources.get(owner_id, {}).get(resource)
    if val is None:
        return None  # Unknown is not an assertion of physical absence.
    if type(val) is not int or val < 0:
        raise ValueError("physical ledger requires a nonnegative integer or unknown")
    return val


def audit_food_chain(
    state: WorldState, *, farm_site: str, bakery_site: str,
    market_site: str, courier_id: str,
) -> FoodChainDiagnosis:
    """Diagnose a known supply circuit without changing WorldState.

    Explicit role IDs are required: this helper never assumes that the names
    'farm'/'market' or one particular NPC are universal world constants.
    """
    if not isinstance(state, WorldState):
        raise TypeError("validated WorldState required")
    if (any(type(k) is not str or not k for k in (
            farm_site, bakery_site, market_site, courier_id))
            or len({farm_site, bakery_site, market_site}) != 3
            or any(site not in state.locations for site in (
                farm_site, bakery_site, market_site))
            or courier_id not in state.npcs):
        raise ValueError("actual distinct world sites and courier required")
    plot = state.farm_plots.get(farm_site)
    circuit = state.supply_circuits.get(courier_id)
    if plot is None or circuit is None:
        raise ValueError("configured farm plot and courier circuit required")
    food = audit_food_security(state)
    bakery_batches = tuple(
        job for job in state.production_jobs.values()
        if job["site_id"] == bakery_site and job["status"] == "completed"
        and state.production_recipes[job["recipe_id"]]["output_resource"] == "food"
    )
    units = sum(state.production_recipes[job["recipe_id"]]["output_amount"]
                for job in bakery_batches)
    # Offers are contractual claims on goods already physically owned;
    # recording them does NOT add to the known physical food inventory.
    open_units = sum(
        offer["remaining"] for offer in state.market_offers.values()
        if offer["site_id"] == market_site and offer["resource"] == "food"
        and offer["status"] == "open"
    )
    sales = tuple(t for t in state.market_trades.values()
                  if t["site_id"] == market_site and t["resource"] == "food")
    money = 0
    for balances in state.resources.values():
        val = balances.get("coin_copper")
        if val is not None:
            if type(val) is not int or val < 0:
                raise ValueError("corrupt known copper")
            money += val
    carry = circuit["carry"]
    courier = state.npcs[courier_id]
    courier_hunger = courier["needs"]["hunger"]
    courier_fatigue = courier["needs"]["fatigue"]
    if any(t["npc_id"] == courier_id and t["status"] == "traveling"
           for t in state.travels.values()):
        leg_reason = "travel_in_progress"
    elif courier_hunger >= 90:
        leg_reason = "hunger_blocks_travel"
    elif courier_fatigue >= 70:
        leg_reason = "fatigue_blocks_travel"
    elif courier["needs"]["safety"] >= 75:
        leg_reason = "safety_blocks_travel"
    elif choose_courier_leg(state, courier_id) is not None:
        leg_reason = "route_eligible"
    else:
        leg_reason = "other_route_or_duty_constraint"
    essential_roles = {
        recipe["role"] for recipe in state.production_recipes.values()
        if recipe["site_id"] in (farm_site, bakery_site)
    }
    blocked = tuple(sorted(
        who for who, npc in state.npcs.items()
        if npc["needs"]["hunger"] >= 90
        and (npc["role"] in essential_roles or who == courier_id)
    ))
    return FoodChainDiagnosis(
        logical_time=state.time,
        hunger_at_cap=food.hunger_at_cap,
        high_risk_without_food=food.high_risk_without_food,
        food_unknown_npcs=food.food_stock_unknown_npcs,
        personal_food_units=food.personal_food_units,
        market_food=_owned_amount(state, market_site, "food"),
        bakery_food=_owned_amount(state, bakery_site, "food"),
        bakery_grain=_owned_amount(state, bakery_site, "grain"),
        farm_grain=_owned_amount(state, farm_site, "grain"),
        farm_crop_ready=_owned_amount(state, farm_site, "crop_ready"),
        farm_seed=_owned_amount(state, farm_site, "seed"),
        farm_water=_owned_amount(state, farm_site, "water"),
        harvested_crop_lots=plot["matured"],
        field_growth_status=plot["status"],
        field_growth_due=plot["due"],
        completed_bread_batches=len(bakery_batches),
        completed_bread_units=units,
        market_open_units=open_units,
        trades=len(sales),
        traded_food_units=sum(t["quantity"] for t in sales),
        eaten_food_units=food.consumed_meals,
        known_copper_total=money,
        courier_deliveries=circuit["deliveries"],
        courier_carry_resource=None if carry is None else carry["resource"],
        courier_location=state.entities[courier_id]["location_id"],
        courier_route_index=circuit["index"],
        courier_hunger=courier_hunger,
        courier_fatigue=courier_fatigue,
        courier_leg_reason=leg_reason,
        essential_workers_hunger_blocked=blocked,
    )
