"""PLAY-48 G1b — the exact true shopping decision barriers before hour 72.

A read-only witness, never a planner. One authentic 13-person world, no
counterfactual initial funds, scripted physical movement, or policy edits.
Six-hour simulation steps and official event/SQLite replay are unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_autonomy import (
    BUY_HUNGER_THRESHOLD, _free, choose_local_food_purchase,
)
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.market_navigation import (
    MAX_SHOPPING_DANGER, MAX_SHOPPING_FATIGUE,
    choose_known_market_walk, choose_known_market_return, wants_local_market,
)
from carlos_sim.navigation import shortest_known_route
from test_play48aa_actual_barter_bread_return import _seed_signed_share
from test_play48h3_early_market_wage import _run, _conserve
from test_play48_13npc_post72_relay import _stats
from test_play47_closure_endurance import WORLD

CHECKPOINTS = (24, 36, 42, 48, 54, 60, 66, 72)
WATCH = ("basim", "hana", "huda", "nora", "farid", "layla", "salma")


def gate_snapshot(state, npc_id):
    profile = state.npcs[npc_id]
    needs = profile["needs"]
    holding = state.resources.get(npc_id, {})
    here = state.entities[npc_id]["location_id"]
    nav = state.navigation.get(npc_id)
    free = _free(state, npc_id)
    known_route = shortest_known_route(state, npc_id, "market")
    wants = wants_local_market(state, npc_id, repeat_errands=True)
    reasons = []
    if npc_id in state.supply_circuits:
        reasons.append("consigned_courier_cannot_personally_shop")
    if not free:
        reasons.append("currently_active_travel_action_or_job")
    if needs["hunger"] < BUY_HUNGER_THRESHOLD:
        reasons.append("hunger_below_buy_trigger")
    if needs["fatigue"] > MAX_SHOPPING_FATIGUE:
        reasons.append("fatigue_above_shopping_guard")
    if needs["safety"] > MAX_SHOPPING_DANGER:
        reasons.append("danger_above_shopping_guard")
    money = holding.get("coin_copper")
    food = holding.get("food")
    if type(money) is not int or money < 1:
        reasons.append("no_personal_initialized_copper")
    if type(food) is not int or food != 0:
        reasons.append("food_balance_unknown_or_owned")
    if nav is not None and nav["target"] is not None:
        reasons.append("explicit_navigation_target_precedence")
    if here in state.market_stalls and any(
        offer["site_id"] == here and offer["resource"] == "food"
        for offer in state.market_offers.values()
    ):
        reasons.append("already_at_food_stall_regular_local_buying")
    if (not reasons and not wants):
        reasons.append("additional_unexplained_gate")
    unblocked_walk = choose_known_market_walk(
        state, npc_id, repeat_errands=True
    )
    return_walk = choose_known_market_return(
        state, npc_id, repeat_errands=True
    )
    local = choose_local_food_purchase(state, npc_id)
    active = {
        "travels": sum(t["npc_id"] == npc_id and t["status"] == "traveling"
                       for t in state.travels.values()),
        "actions": sum(a["npc_id"] == npc_id and a["status"] == "running"
                       for a in state.actions.values()),
        "jobs": sum(j["npc_id"] == npc_id and j["status"] == "running"
                    for j in state.production_jobs.values()),
    }
    paid = [
        (j["work_wage"]["paid_at"], j["work_wage"]["amount"])
        for j in state.production_jobs.values()
        if j["npc_id"] == npc_id and "work_wage" in j
    ]
    return {
        "npc": npc_id, "place": here, "hunger": needs["hunger"],
        "fatigue": needs["fatigue"], "safety": needs["safety"],
        "personal_copper_or_custody_slot": money,
        "personal_food_or_custody_slot": food,
        "is_courier": npc_id in state.supply_circuits,
        "currently_free": free, "busy": active,
        "navigation_target": nav["target"] if nav else None,
        "known_market_road": list(known_route) if known_route else None,
        "visited_market": bool(nav and "market" in nav["visited"]),
        "last_decision": profile["last_decision"],
        "next_decision_at": profile["next_decision_at"],
        "paid_job_receipts": paid,
        "wants_local_market": wants,
        "wants_market_false_reasons": reasons,
        "walk_selector": (
            {"road": unblocked_walk.route_id,
             "destination": unblocked_walk.destination}
            if unblocked_walk else None
        ),
        "return_selector": (
            {"road": return_walk.route_id, "destination": return_walk.destination}
            if return_walk else None
        ),
        "can_buy_local_offer_now": local is not None,
    }


def main():
    with TemporaryDirectory(prefix="play48-g1b-") as root:
        path = Path(root) / "single-authentic-13-person-world.sqlite"
        original = _seed_signed_share(path, share=True, farm_refill_authority=True)
        assert len(original.npcs) == 13
        for hour in CHECKPOINTS:
            state, _ = _run(
                path, hour * 3600, early=True,
                hungry_woodcutter_work_enabled=True,
                retry_known_supplier_enabled=True,
                farm_sourced_wage_refill_enabled=True,
            )
            assert len(state.npcs) == 13
            _conserve(state)
            with SQLiteEventStore(path) as db:
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            before = state.to_dict()
            audit = audit_food_access_barriers(state)
            assert audit["npc_count"] == 13
            summary = {
                "hour": hour,
                "stats": _stats(state),
                "market_food_offers": audit["opening_food_offer_count_currently_open"],
                "watched": [gate_snapshot(state, who) for who in WATCH],
                "operator_only": True,
                "no_new_money_food_routes_or_commands": True,
                "release_no_go": True,
            }
            assert state.to_dict() == before
            print("PLAY48_AUTHENTIC_SHOPPING_GATE_AUDIT " +
                  json.dumps(summary, sort_keys=True), flush=True)
        print("PLAY48_SHOPPING_GATES_DIAGNOSIS_DONE_NOT_APPROVAL", flush=True)


if __name__ == "__main__":
    main()
