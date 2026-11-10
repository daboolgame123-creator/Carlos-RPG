"""Operator-only, read-only causal diagnostic for one physical courier.

This is NOT an NPC-planner API or a source of world state authority. It
delegates eligibility to the real supply selectors instead of simulating
invented route/cargo decisions. The caller must explicitly provide the
engine's opt-in supply flag, which is not persisted in WorldState.
"""
from __future__ import annotations

from .domain import WorldState
from .npc import _injury_rest_decision
from .supply import choose_cargo, choose_courier_leg, _lane, _traveling


def audit_courier(state: WorldState, courier_id: str, *,
                  supply_enabled: bool) -> dict:
    """Observe one actual courier, with explicit unknown stock and flag state.

    Never equate an absent balance to zero; never change a schedule, cargo,
    NPC need, inventory or funds, and never return this to an NPC decision.
    """
    if type(supply_enabled) is not bool:
        raise ValueError("supply_enabled must be a boolean")
    if (type(courier_id) is not str
            or courier_id not in state.supply_circuits
            or courier_id not in state.npcs):
        raise ValueError("must name an actual configured courier")

    rec = state.supply_circuits[courier_id]
    here = state.entities[courier_id]["location_id"]
    needs = state.npcs[courier_id]["needs"]
    cargo = rec["carry"]
    lane = _lane(
        rec, cash_enabled="coin_copper" in state.resources.get(courier_id, {})
    )
    source, destination, resource = lane if lane else (None, None, None)
    physically_owned = (
        state.resources.get(source, {}).get(resource)
        if source is not None else None
    )
    if physically_owned is not None and (
            type(physically_owned) is not int or physically_owned < 0):
        raise ValueError("courier source stock must be known, nonnegative integer")

    next_action = None
    reasons = []
    if not supply_enabled:
        reasons.append("engine_supply_flag_disabled")
    else:
        # Use the existing trusted selectors to avoid a second, inconsistent
        # model of courier route and goods eligibility.
        material_action = choose_cargo(state, courier_id)
        route_action = choose_courier_leg(state, courier_id)
        if material_action is not None:
            next_action = material_action
        elif route_action is not None:
            next_action = "NPCTravelStarted"
        else:
            if _traveling(state, courier_id):
                reasons.append("courier_busy_or_traveling")
            if needs["hunger"] >= 90:
                reasons.append("hunger_at_or_above_90")
            if needs["fatigue"] >= 70:
                reasons.append("fatigue_at_or_above_70")
            if needs["safety"] >= 75:
                reasons.append("unsafe")
            if _injury_rest_decision(state.injuries, courier_id) is not None:
                reasons.append("injury_requires_rest")
            if rec["index"] == 0 and state.time < rec["next_departure"]:
                reasons.append("waiting_for_scheduled_departure")
            if not reasons:
                reasons.append("no_eligible_authorized_courier_action")
    return {
        "courier_id": courier_id,
        "time": state.time,
        "location": here,
        "contract_index": rec["index"],
        "next_departure": rec["next_departure"],
        "loads": rec["loads"],
        "deliveries": rec["deliveries"],
        "rounds": rec["rounds"],
        "carried_resource": cargo["resource"] if cargo is not None else None,
        "expected_pickup_source": source,
        "expected_delivery_site": destination,
        "expected_pickup_resource": resource,
        "local_source_quantity_known": physically_owned,
        "local_source_is_unknown": source is not None and physically_owned is None,
        "next_action": next_action,
        "blocked_reasons": tuple(reasons),
        "needs": {
            "hunger": needs["hunger"],
            "fatigue": needs["fatigue"],
            "safety": needs["safety"],
        },
    }
