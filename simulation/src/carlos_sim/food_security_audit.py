"""PLAY-29: read-only food-access diagnosis for private simulation review.

This function never emits an event, changes a resource, or exposes a player's
hidden NPC records. Do NOT add this internal report to `player_view`: it is
for development/admin auditing only. The values report owned inventories,
not magically accessible food; travel, money and labor remain relevant.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

from .domain import WorldState


@dataclass(frozen=True)
class FoodRisk:
    npc_id: str
    hunger: int
    personally_owned_food: int | None

    @property
    def no_known_food(self) -> bool:
        return self.personally_owned_food is None

    @property
    def no_personal_food(self) -> bool:
        return self.personally_owned_food == 0


@dataclass(frozen=True)
class FoodSecurityAudit:
    world_id: str
    logical_time: int
    npc_count: int
    risk_threshold: int
    high_risk: tuple[FoodRisk, ...]
    hunger_at_cap: tuple[str, ...]
    high_risk_without_food: tuple[str, ...]
    high_risk_unknown_food: tuple[str, ...]
    personal_food_units: int
    reserved_courier_food_units: int
    food_stock_unknown_npcs: tuple[str, ...]
    known_site_food_units: int
    food_stock_unknown_sites: tuple[str, ...]
    consumed_meals: int

    def to_dict(self) -> dict:
        result = asdict(self)
        # Make the report portable without exposing state objects; the
        # caller chooses any further visibility/authorization boundaries.
        result["high_risk"] = [asdict(x) for x in self.high_risk]
        for name in ("hunger_at_cap", "high_risk_without_food",
                     "high_risk_unknown_food", "food_stock_unknown_npcs",
                     "food_stock_unknown_sites"):
            result[name] = list(result[name])
        return result


def _known_food(state: WorldState, owner: str) -> int | None:
    value = state.resources.get(owner, {}).get("food")
    # None means NOT OBSERVED. Never coerce missing stock to zero.
    return value if type(value) is int else None


def audit_food_security(state: WorldState, *, risk_threshold: int = 75) -> FoodSecurityAudit:
    """Diagnose genuine owned stocks; no UI/player visibility implied.

    Food in a courier's cargo is not food available for their own meal.
    Market offers do not create new site stock. Every count uses resource
    balances once (the existing reducer validates nonnegative stocks).
    """
    if not isinstance(state, WorldState):
        raise TypeError("world snapshot required")
    if type(risk_threshold) is not int or not 1 <= risk_threshold <= 100:
        raise ValueError("risk threshold must be an integer from 1 to 100")
    risks: list[FoodRisk] = []
    at_cap: list[str] = []
    no_food: list[str] = []
    unknown_hungry: list[str] = []
    unknown_npcs: list[str] = []
    personal_food = 0
    reserved_cargo = 0

    for who, npc in sorted(state.npcs.items()):
        personal = _known_food(state, who)
        reserved = 0
        circuit = state.supply_circuits.get(who)
        if circuit is not None and circuit["carry"] is not None:
            if circuit["carry"]["resource"] == "food":
                reserved = 1
                reserved_cargo += 1
        if personal is None:
            unknown_npcs.append(who)
            accessible = None
        else:
            if personal < reserved:
                raise ValueError("courier cargo would exceed physically owned food")
            accessible = personal - reserved
            personal_food += accessible
        hunger = npc["needs"]["hunger"]
        if hunger == 100:
            at_cap.append(who)
        if hunger >= risk_threshold:
            risks.append(FoodRisk(who, hunger, accessible))
            if accessible == 0:
                no_food.append(who)
            elif accessible is None:
                unknown_hungry.append(who)

    known_site_food = 0
    unknown_sites: list[str] = []
    for site in sorted(state.locations):
        value = _known_food(state, site)
        if value is None:
            unknown_sites.append(site)
        else:
            known_site_food += value
    # Escrow remains site-owned, not personal meals or market stock.
    known_site_food += sum(p["remaining"] for p in state.courier_provisions.values())
    return FoodSecurityAudit(
        world_id=state.world_id, logical_time=state.time,
        npc_count=len(state.npcs), risk_threshold=risk_threshold,
        high_risk=tuple(risks), hunger_at_cap=tuple(at_cap),
        high_risk_without_food=tuple(no_food),
        high_risk_unknown_food=tuple(unknown_hungry),
        personal_food_units=personal_food,
        reserved_courier_food_units=reserved_cargo,
        food_stock_unknown_npcs=tuple(unknown_npcs),
        known_site_food_units=known_site_food,
        food_stock_unknown_sites=tuple(unknown_sites),
        consumed_meals=sum(m["quantity"] for m in state.consumptions.values()),
    )
