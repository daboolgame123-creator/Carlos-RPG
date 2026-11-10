"""PLAY-48H2: *operator-only* snapshot of local food-access blockers.

The planner MUST NOT import this module. This diagnostic may inspect the
entire verified WorldState to explain a failed economy; simulated NPCs must
continue to use only their personally acquired navigation, their own wallet
and goods actually visible at their present location.

Every value is observed at the exact current tick. Road/path reachability
does not imply a future decision, welfare guarantee or vendor availability.
"""
from __future__ import annotations

from typing import Any

from .domain import WorldState
from .navigation import shortest_known_route
from .consumption import _reserved_food
from .npc import _injury_rest_decision
from .market import _present, reserved_trade_units, trade_receipt_allowed

MONEY = "coin_copper"


def _known(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _idle(state: WorldState, who: str) -> bool:
    if any(t["npc_id"] == who and t["status"] == "traveling"
           for t in state.travels.values()):
        return False
    if any(a["npc_id"] == who and a["status"] == "running"
           for a in state.actions.values()):
        return False
    if any(j["npc_id"] == who and j["status"] == "running"
           for j in state.production_jobs.values()):
        return False
    return True


def audit_food_access_barriers(state: WorldState) -> dict[str, Any]:
    """Read-only forensic report; never a source of remote NPC omniscience.

    'locally_affordable_now' checks the real local listing and its keeper
    against PERSONAL copper only. Courier copper is consigned to its circuit
    and explicitly cannot be spent on food; missing balances stay unknown.
    """
    if not isinstance(state, WorldState):
        raise TypeError("validated WorldState required")

    market = "market"
    total_escrow = sum(c["remaining"] for c in state.courier_provisions.values())
    market_stock = _known(state.resources.get(market, {}).get("food"))
    raw = state.to_dict()  # Detached data for trusted physical-presence checks.
    market_offers = [(ident, offer) for ident, offer in
                     sorted(state.market_offers.items())
                     if offer["resource"] == "food"
                     and offer["payment_resource"] == MONEY
                     and offer["status"] == "open"]

    records = []
    for who, npc in sorted(state.npcs.items()):
        here = state.entities[who]["location_id"]
        needs = npc["needs"]
        in_circuit = who in state.supply_circuits
        holdings = state.resources.get(who, {})
        purse = _known(holdings.get(MONEY))
        own_food = _known(holdings.get("food"))
        entrusted_food = _reserved_food(state.supply_circuits, who)
        if own_food is not None and entrusted_food > own_food:
            raise ValueError("courier custody food cannot exceed the physical slot")

        personal_food = None if own_food is None else own_food - entrusted_food
        cash_scope = ("consignment_only" if in_circuit and purse is not None else
                      "unknown" if purse is None else "personal")
        # An initialized courier cash slot is an exact-custody fund, even when
        # zero. It is NEVER a personally spendable wallet.
        personal_copper = purse if cash_scope == "personal" else None

        nav = state.navigation.get(who)
        if here == market:
            path: tuple[str, ...] | None = ()
        else:
            actual_known = shortest_known_route(state, who, market)
            path = actual_known if actual_known else None
        known_seconds = (sum(state.routes[rid]["seconds"] for rid in path)
                         if path is not None else None)
        busy = not _idle(state, who)
        injury_block = _injury_rest_decision(state.injuries, who) is not None
        courier_travel_blockers = []
        if in_circuit:
            if needs["hunger"] >= 90:
                courier_travel_blockers.append("hunger_at_or_above_90")
            if needs["fatigue"] >= 70:
                courier_travel_blockers.append("fatigue_at_or_above_70")
            if needs["safety"] >= 75:
                courier_travel_blockers.append("danger_at_or_above_75")
            if injury_block:
                courier_travel_blockers.append("injury_requires_rest")
            if busy:
                courier_travel_blockers.append("already_busy_or_traveling")

        local_food_offers = []
        if not busy:
            for ident, offer in market_offers:
                if offer["site_id"] != here or offer["seller_id"] == who:
                    continue
                owner = offer["stock_owner_id"]
                actual = _known(state.resources.get(owner, {}).get("food"))
                if (actual is None or not _present(raw, offer["seller_id"], here)
                        or not trade_receipt_allowed(state.supply_circuits, owner, MONEY)):
                    continue
                sellable = max(0, actual - reserved_trade_units(
                    state.supply_circuits, owner, "food"))
                quote = min(offer["remaining"], sellable)
                if quote > 0:
                    local_food_offers.append({
                        "offer_id": ident, "site": here,
                        "unit_price": offer["unit_price"],
                        "locally_available_units": quote,
                        "personally_affordable": (
                            personal_copper is not None
                            and personal_copper >= offer["unit_price"]
                            and not in_circuit),
                    })

        signed_contract = next((
            {"id": contract_id, "remaining": c["remaining"],
             "paid_receipts": len(c["payments"])}
            for contract_id, c in sorted(state.courier_provisions.items())
            if c["courier_id"] == who
        ), None)

        records.append({
            "npc_id": who,
            "role": npc["role"],
            "location": here,
            "hunger": needs["hunger"],
            "fatigue": needs["fatigue"],
            "known_personal_food": personal_food,
            "courier_reserved_cargo_food": entrusted_food,
            "copper_slot": purse,
            "copper_scope": cash_scope,
            "personally_spendable_copper": personal_copper,
            "physically_idle": not busy,
            "known_road_path_to_market": list(path) if path is not None else None,
            "known_road_seconds_to_market": known_seconds,
            "at_market": here == market,
            "locally_listed_food": local_food_offers,
            "locally_affordable_now": any(x["personally_affordable"]
                                           for x in local_food_offers),
            "courier_leg_blockers": courier_travel_blockers,
            "signed_unearned_food_wage": signed_contract,
            "known_visited_places": (list(nav["visited"]) if nav else []),
        })

    return {
        "world_id": state.world_id,
        "sim_time": state.time,
        "schema": state.schema_version,
        "rules": state.rules_version,
        "npc_count": len(records),
        "hunger_at_100": sum(x["hunger"] == 100 for x in records),
        "market_saleable_food_known": market_stock,
        "market_site_owned_escrow_food": total_escrow,
        "opening_food_offer_count_currently_open": len(market_offers),
        "courier_custody_wallets_excluded": sum(
            x["copper_scope"] == "consignment_only" for x in records
        ),
        "actors": records,
        "scope": "operator-only; not NPC knowledge, not action permissions",
    }
