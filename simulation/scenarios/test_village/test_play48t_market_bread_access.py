"""PLAY-48T operator-only 13-NPC audit: why market bread does not become meals.

Do NOT expose these omniscient audit details to NPC controllers. Uses the
real verified salary, farming, courier route, sales and autonomous hunger
behavior for 48 hours. No hand-authored interventions or added stock.
"""
from __future__ import annotations

import json
from collections import Counter

from carlos_sim import SQLiteEventStore
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.market import _present, reserved_trade_units
from test_play47_closure_endurance import DAY, WORLD
from test_play48h3_early_market_wage import _run, _conserve
from test_play48s_authentic_courier_food_wages import (
    _seed_employed_paid_couriers, _check_wage_receipts,
)


def _operator_snapshot(state):
    before = state.to_dict()
    access = audit_food_access_barriers(state)
    cash = audit_npc_economy(state)
    assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    assert access["npc_count"] == len(state.npcs) == 13

    merchant = state.market_stalls["market"]["keeper_id"]
    seller = state.npcs[merchant]
    offers = [
        {
            "id": ident, "status": offer["status"],
            "posted_at": offer["posted_at"],
            "remaining": offer["remaining"],
            "original_quantity": offer["quantity"],
            "unit_price": offer["unit_price"],
            "local_seller": offer["seller_id"] == merchant,
            "owner": offer["stock_owner_id"],
            "resource": offer["resource"],
            "seller_physically_present": _present(before, offer["seller_id"], offer["site_id"]),
        }
        for ident, offer in sorted(state.market_offers.items())
        if offer["resource"] == "food" and offer["site_id"] == "market"
    ]
    active_units = sum(
        x["remaining"] for x in offers if x["status"] == "open"
    )
    market_food = state.resources["market"]["food"]
    delivery_count = sum(
        rec["deliveries"] for rec in state.supply_circuits.values()
    )
    market_cargo_reserved = reserved_trade_units(state.supply_circuits, "market", "food")
    actually_listed = min(
        max(0, market_food - market_cargo_reserved),
        active_units,
    )
    buyers = [
        {
            "who": p["npc_id"],
            "role": p["role"],
            "where": p["location"],
            "hunger": p["hunger"],
            "fatigue": p["fatigue"],
            "personal_copper": p["personally_spendable_copper"],
            "cash_scope": p["copper_scope"],
            "owned_food": p["known_personal_food"],
            "knows_route_to_market": p["known_road_path_to_market"] is not None,
            "at_market": p["at_market"],
            "locally_affordable": p["locally_affordable_now"],
            "blocked_courier": p["courier_leg_blockers"],
            "offers_seen_at_present_site": len(p["locally_listed_food"]),
        }
        for p in access["actors"]
    ]
    starving = [p for p in buyers if p["hunger"] >= 90]
    hungry_with_personal_cash = [
        p for p in starving
        if p["personal_copper"] is not None and p["personal_copper"] >= 2
    ]
    outcome = {
        "sim_time": state.time,
        "market_on_hand_real_food": market_food,
        "market_food_reserved_for_shipment": market_cargo_reserved,
        "current_open_offer_food_units": active_units,
        "actually_saleable_now_upper_bound": actually_listed,
        "market_stall_keeper_id": merchant,
        "keeper_location": state.entities[merchant]["location_id"],
        "keeper_hunger": seller["needs"]["hunger"],
        "keeper_fatigue": seller["needs"]["fatigue"],
        "keeper_free_to_post": not any(
            (action["npc_id"] == merchant and action["status"] == "running")
            for action in state.actions.values()
        ) and not any(
            (trip["npc_id"] == merchant and trip["status"] == "traveling")
            for trip in state.travels.values()
        ),
        "all_offers": offers,
        "actual_food_sales": sum(
            trade["quantity"] for trade in state.market_trades.values()
            if trade["resource"] == "food"
        ),
        "actual_meals": sum(
            meal["quantity"] for meal in state.consumptions.values()
        ),
        "hunger_at_100": access["hunger_at_100"],
        "hunger_at_or_above_90": len(starving),
        "hunger_at_or_above_90_with_personal_2plus_copper":
            len(hungry_with_personal_cash),
        "real_courier_deliveries_cumulative": delivery_count,
        "individual_cash_food_travel_sale_context": buyers,
        "no_food_or_currency_created": True,
    }
    assert before == state.to_dict()
    return outcome


def test_real_food_access_after_48h_earned_wage_village(tmp_path):
    path = tmp_path / "read-only-real-bread-trace.sqlite"
    opening = _seed_employed_paid_couriers(path)
    assert _conserve(opening) == 2
    observed = []
    for day in (1, 2):
        final, _ = _run(
            path, day * DAY, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        assert final.time == day * DAY
        _conserve(final)
        audit = _operator_snapshot(final)
        observed.append(audit)
        with SQLiteEventStore(path) as db:
            assert db.verify(WORLD).to_dict() == final.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []

    _check_wage_receipts(path, final)
    print("PLAY48T_REAL_DAY1_DAY2_MARKET_FOOD_ACCESS_FORENSICS",
          json.dumps({
              "checkpoints": observed,
              "13_real_npcs": True,
              "unchanged_copper_total": 12,
              "initial_real_bread_including_escrow": 3,
              "no_omniscient_input_to_NPCs": True,
              "no_operator_behaviour_change": True,
              "not_a_recovery_claim": True,
          }, sort_keys=True), flush=True)
