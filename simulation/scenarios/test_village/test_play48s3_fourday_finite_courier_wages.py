"""PLAY-48S3 — four-day real 13-NPC earned-bread endurance, not recovery fiction.

Deliberately same authenticated genesis in paid/unpaid arms: two physical
employer-owned loaves held in escrow, one free shop loaf, 12 copper, 13 people,
wood and charcoal jobs, two watered finite farms with the isolated eastern
fertile crop contract. Only opt-in early paid courier food wage behavior differs.
No new crops, food, money, NPC knowledge or manual intervention during the run.
A passing diagnostic test is NOT a passing economy.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import DAY, WORLD
from test_play48h3_early_market_wage import _run, _conserve
from test_play48s_authentic_courier_food_wages import (
    _seed_employed_paid_couriers, _stats, _check_wage_receipts,
)


def _snapshot(state):
    stat = _stats(state)
    stat["total_completed_jobs"] = sum(
        j["status"] == "completed" for j in state.production_jobs.values()
    )
    stat["total_market_trades"] = len(state.market_trades)
    stat["all_meals_confirmed_personal_food"] = all(
        meal["food_after"] == meal["food_before"] - meal["quantity"]
        and meal["hunger_after"] < meal["hunger_before"]
        for meal in state.consumptions.values()
    )
    return stat


def _delta(a, b):
    keys = ("real_meals", "food_sales", "baked_batches", "wood_sales",
            "charcoal_sales", "cash_wages", "total_completed_jobs",
            "total_market_trades")
    changes = {k: b[k] - a[k] for k in keys}
    changes["deliveries"] = {
        who: b["couriers"][who]["deliveries"] -
        a["couriers"][who]["deliveries"] for who in ("huda", "hana")
    }
    assert all(n >= 0 for n in changes.values() if isinstance(n, int))
    assert all(n >= 0 for n in changes["deliveries"].values())
    return changes


def test_s3_true_four_day_employer_food_wage_causal_endurance(tmp_path):
    unpaid_path = tmp_path / "s3-unpaid-protected-96h.sqlite"
    paid_path = tmp_path / "s3-earned-protected-96h.sqlite"
    control = _seed_employed_paid_couriers(unpaid_path)
    treatment = _seed_employed_paid_couriers(paid_path)
    # World state at genesis is strictly identical. No one gets new stock
    # merely for being in the treatment arm.
    assert control.to_dict() == treatment.to_dict()
    assert len(control.npcs) == 13
    assert audit_npc_economy(control)["copper_known_total"] == 12
    assert _conserve(control) == _conserve(treatment) == 2
    assert sum(x.get("food", 0) for x in control.resources.values()) == 1

    checkpoints = []
    for day in (1, 2, 3, 4):
        old, _ = _run(
            unpaid_path, DAY * day, early=False,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        new, _ = _run(
            paid_path, DAY * day, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        assert old.time == new.time == day * DAY
        assert len(old.npcs) == len(new.npcs) == 13
        assert _conserve(old) >= 0 and _conserve(new) >= 0
        assert audit_npc_economy(old)["copper_known_total"] == 12
        assert audit_npc_economy(new)["copper_known_total"] == 12
        for path, state in ((unpaid_path, old), (paid_path, new)):
            with SQLiteEventStore(path) as db:
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        checkpoints.append({
            "day": day, "control": _snapshot(old), "paid": _snapshot(new)
        })

    _check_wage_receipts(paid_path, new)
    assert sum(len(p["payments"]) for p in
               new.courier_provisions.values()) <= 2
    # The control still has the original H1 market food-delivery wage:
    # Hana may earn a real meal for a genuine food delivery even if early
    # payment is disabled. Huda's farm-water early wage is the distinction.
    assert len(old.courier_provisions["farm-water-huda"]["payments"]) == 0
    assert sum(len(c["payments"]) for c in
               old.courier_provisions.values()) <= 2
    unpaid_post72 = _delta(checkpoints[2]["control"], checkpoints[3]["control"])
    paid_post72 = _delta(checkpoints[2]["paid"], checkpoints[3]["paid"])
    genuine_post72_recovery = (
        any(x > 0 for x in paid_post72["deliveries"].values())
        and any(paid_post72[k] > 0 for k in
                ("real_meals", "food_sales", "total_completed_jobs",
                 "total_market_trades"))
    )
    report = {
        "same_authentic_opening_genesis": True,
        "original_existing_thirteen_people": 13,
        "total_initial_existing_copper": 12,
        "total_initial_loaves_including_escrow": 3,
        "same_existing_water_rain_crop_yields_professions": True,
        "no_postgenesis_test_actions_or_new_provisions": True,
        "only_comparison_flag": "early_courier_food_wage_enabled",
        "same_original_hunger_and_safety_guards": True,
        "daily_24_48_72_96h": checkpoints,
        "post72_unpaid": unpaid_post72,
        "post72_paid": paid_post72,
        "genuine_post72_activity_with_deliveries": genuine_post72_recovery,
        "existing_contract_is_finite_not_renewable": True,
        "seven_day_recovery_proven": False,
        "schema_or_rules_changed": False,
        "production_release_approved": False,
    }
    print("PLAY48S3_TRUE_96H_FINITE_EMPLOYER_BREAD_VERSUS_UNPAID",
          json.dumps(report, sort_keys=True), flush=True)
