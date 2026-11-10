"""PLAY-48J2: actual combination of independently approved economic ideas.

A 13-resident village with the SAME 2-copper employer wages in both arms.
Both start with market-owner-reserved food wages for the TWO real couriers.
One uses H1's strict food-delivery payday, the other H3's earlier genuine
market service payday. No NPC moves without a route and real inventory;
no payroll happens without completed recorded physical service.

This is a falsifiable counterfactual. A food wage or more meals in the first
day is not enough; compare activity and incapacitated labor after 72h.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply_diagnostics import audit_courier
from test_play47_closure_endurance import WORLD, DAY
from test_play48h1_funded_courier_provision import _sign
from test_play48h3_early_market_wage import _run, _conserve
from test_play48j_affordable_payroll import _seed_affordable

COURIERS = ("huda", "hana")


def _same_paid_contract_pair(tmp_path):
    old = tmp_path / "wages2-h1-pay-on-food.sqlite"
    early = tmp_path / "wages2-h3-pay-on-finished-service.sqlite"
    for path in (old, early):
        opening = _seed_affordable(path)
        assert len(opening.npcs) == 13
        assert audit_npc_economy(opening)["copper_known_total"] == 12
        with SQLiteEventStore(path) as db:
            state = _sign(db)
            assert state.resources["market"]["food"] == 1
            assert _conserve(state) == 2
            assert all(state.courier_provisions["food-wage-" + who]["remaining"] == 1
                       for who in COURIERS)
            assert db.verify(WORLD).to_dict() == state.to_dict()
    return old, early


def _receipt_report(state):
    assert audit_npc_economy(state)["copper_known_total"] == 12
    loans = {}
    for who in ("nora", "basim", "farid", "huda", "hana"):
        stock = state.resources[who]
        loans[who] = {
            "hunger": state.npcs[who]["needs"]["hunger"],
            "fatigue": state.npcs[who]["needs"]["fatigue"],
            "food_owned": stock.get("food", 0),
            "copper_owned": stock.get("coin_copper", None),
            "location": state.entities[who]["location_id"],
        }
    wage_counts = {
        site: len([job for job in state.production_jobs.values()
                   if job["site_id"] == site and "work_wage" in job])
        for site in ("farm", "farm_east", "bakery")
    }
    food_contracts = {
        who: {
            "paid": len(state.courier_provisions["food-wage-" + who]["payments"]),
            "escrow": state.courier_provisions["food-wage-" + who]["remaining"],
            "blocked": audit_courier(state, who, supply_enabled=True)["blocked_reasons"],
        }
        for who in COURIERS
    }
    wallets = {
        owner: bag["coin_copper"]
        for owner, bag in sorted(state.resources.items())
        if type(bag.get("coin_copper")) is int and bag["coin_copper"] > 0
    }
    assert sum(wallets.values()) == 12
    return {
        "time": state.time,
        "cash_by_actual_owner": wallets,
        "workers": loans,
        "production_wage_receipts": wage_counts,
        "courier_earned_food_wages": food_contracts,
        "meals": len(state.consumptions),
        "food_sales": sum(trade["resource"] == "food"
                          for trade in state.market_trades.values()),
        "completed_jobs": sum(job["status"] == "completed"
                              for job in state.production_jobs.values()),
        "deliveries": {who: state.supply_circuits[who]["deliveries"]
                        for who in COURIERS},
        "hunger_100": sum(npc["needs"]["hunger"] == 100
                          for npc in state.npcs.values()),
        "market_loaves": state.resources["market"]["food"],
        "reserved_market_loaves": sum(
            x["remaining"] for x in state.courier_provisions.values()
        ),
    }


def test_same_funded_two_coin_and_two_courier_food_wages_first_twelve_hours(tmp_path):
    old, early = _same_paid_contract_pair(tmp_path)
    a, ah = _run(old, DAY // 2, early=False)
    b, bh = _run(early, DAY // 2, early=True)
    _conserve(a)
    _conserve(b)
    first, new = _receipt_report(a), _receipt_report(b)
    assert first["time"] == new["time"] == DAY // 2
    assert (first["reserved_market_loaves"] +
            sum(x["paid"] for x in first["courier_earned_food_wages"].values())) == 2
    assert (new["reserved_market_loaves"] +
            sum(x["paid"] for x in new["courier_earned_food_wages"].values())) == 2
    print("PLAY48J2_REAL_12H_COURIER_WAGES_WITH_SITE_PAYROLL",
          json.dumps({"strict_food_delivery": first,
                      "early_real_service": new,
                      "same_genesis_and_cash": True,
                      "recovery_claimed": False}, sort_keys=True), flush=True)


def test_same_funded_two_coin_and_courier_food_wages_96h_causal_outcome(tmp_path):
    old, early = _same_paid_contract_pair(tmp_path)
    a, ah = _run(old, 4 * DAY, early=False)
    b, bh = _run(early, 4 * DAY, early=True)
    first, new = _receipt_report(a), _receipt_report(b)
    assert first["time"] == new["time"] == 4 * DAY
    assert len(ah) == len(bh) == 4
    def changes(history):
        t72 = history[2]["economy"]
        t96 = history[3]["economy"]
        return {
            metric: t96[metric] - t72[metric]
            for metric in ("meals", "jobs", "trades", "wages", "food_sales")
        } | {
            "new_courier_deliveries": {
                who: t96["deliveries"][who] - t72["deliveries"][who]
                for who in COURIERS
            },
            "hunger_cap_72h": t72["hunger_cap"],
            "hunger_cap_96h": t96["hunger_cap"],
        }
    old_growth = changes(ah)
    new_growth = changes(bh)
    report = {
        "with_same_true_initial_money": 12,
        "strict_market_food_payroll": first,
        "earlier_funded_market_service_payroll": new,
        "strict_daily": ah,
        "early_daily": bh,
        "strict_post72_activity": old_growth,
        "early_post72_activity": new_growth,
        "earlier_service_recovered_72_96": (
            any(v > 0 for v in new_growth["new_courier_deliveries"].values())
            and any(new_growth[k] > 0
                    for k in ("meals", "jobs", "trades", "food_sales"))
        ),
        "no_magic_income_or_food": True,
        "operator_did_not_force_npc_activity": True,
        "unproven_seven_day_stability": True,
    }
    # Do not gate the test on an invented prosperous outcome.
    print("PLAY48J2_REAL_96H_COURIER_AND_COIN_PAYROLL",
          json.dumps(report, sort_keys=True), flush=True)
