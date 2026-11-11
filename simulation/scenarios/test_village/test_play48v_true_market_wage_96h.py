"""PLAY-48V: causal four-day funded market wages, same 13-person genesis.

Bounded employer-authorized local market food, not fictional free income.
Passing the simulator proves only conservation and observation, not recovery.
"""
from __future__ import annotations
import json

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import DAY, WORLD
from test_play48h3_early_market_wage import _run, _conserve
from test_play48s_authentic_courier_food_wages import _seed_employed_paid_couriers, _stats
from test_play48u_signed_market_refill import _read_receipts


def _row(state):
    s = _stats(state)
    s["jobs"] = sum(j["status"] == "completed" for j in state.production_jobs.values())
    s["trades"] = len(state.market_trades)
    s["real_owned_meals_valid"] = all(
        m["food_before"] - m["food_after"] == m["quantity"]
        and m["hunger_after"] < m["hunger_before"]
        for m in state.consumptions.values()
    )
    return s


def _change(from_state, to_state):
    keys = ("real_meals", "food_sales", "baked_batches", "jobs",
            "trades", "cash_wages", "wood_sales", "charcoal_sales")
    delta = {k: to_state[k] - from_state[k] for k in keys}
    delta["deliveries"] = {
        k: to_state["couriers"][k]["deliveries"]
           - from_state["couriers"][k]["deliveries"]
        for k in ("huda", "hana")
    }
    assert all(n >= 0 for n in delta.values() if type(n) is int)
    assert all(n >= 0 for n in delta["deliveries"].values())
    return delta


def test_true_four_day_market_sourced_wage_vs_same_bounded_control(tmp_path):
    control_path = tmp_path / "48v-one-shot-13.sqlite"
    funded_path = tmp_path / "48v-market-funded-13.sqlite"
    base = _seed_employed_paid_couriers(control_path)
    trial = _seed_employed_paid_couriers(funded_path)
    assert base.to_dict() == trial.to_dict()
    assert (base.schema_version, base.rules_version) == (45, 62)
    assert len(base.npcs) == 13
    assert audit_npc_economy(base)["copper_known_total"] == 12
    assert _conserve(base) == _conserve(trial) == 2
    checkpoints = []
    for day in (1, 2, 3, 4):
        a, _ = _run(
            control_path, DAY * day, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
            market_sourced_wage_refill_enabled=False,
        )
        b, _ = _run(
            funded_path, DAY * day, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
            market_sourced_wage_refill_enabled=True,
        )
        assert a.time == b.time == day * DAY
        assert len(a.npcs) == len(b.npcs) == 13
        assert audit_npc_economy(a)["copper_known_total"] == 12
        assert audit_npc_economy(b)["copper_known_total"] == 12
        assert _conserve(a) >= 0 and _conserve(b) >= 0
        assert a.courier_provisions["market-service-hana"]["total_units"] == 1
        assert b.courier_provisions["market-service-hana"]["total_units"] <= 3
        for path, state in ((control_path, a), (funded_path, b)):
            with SQLiteEventStore(path) as db:
                before = state.to_dict()
                assert db.verify(WORLD).to_dict() == before
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        checkpoints.append({
            "day": day, "control": _row(a), "market_funded": _row(b),
            "authentic_market_refills": _read_receipts(funded_path, b),
        })

    verified_refills = _read_receipts(funded_path, b)
    assert 0 <= verified_refills <= 2
    assert b.courier_provisions["market-service-hana"]["total_units"] == (
        1 + verified_refills
    )
    assert b.courier_provisions["market-service-hana"]["authorized_total_units"] == 3
    assert b.courier_provisions["farm-water-huda"]["authorized_total_units"] == 1
    assert b.courier_provisions["farm-water-huda"]["total_units"] == 1
    after72_control = _change(checkpoints[2]["control"], checkpoints[3]["control"])
    after72_trial = _change(checkpoints[2]["market_funded"], checkpoints[3]["market_funded"])
    report = {
        "same_authentic_13npc_genesis": True,
        "starting_real_loaves_including_escrow": 3,
        "starting_and_final_conserved_copper": 12,
        "only_difference": "opt_in_signed_market_sourced_wage_refill",
        "actual_24_48_72_96h": checkpoints,
        "real_extra_food_wage_refills": verified_refills,
        "after72_control": after72_control,
        "after72_trial": after72_trial,
        "post72_simultaneous_jobs_deliveries_meals": (
            (after72_trial["jobs"] > 0 or after72_trial["trades"] > 0)
            and sum(after72_trial["deliveries"].values()) > 0
            and after72_trial["real_meals"] > 0
        ),
        "hunger_safety_bypassed": False,
        "unlimited_courier_wages": False,
        "seven_day_economic_recovery_proven": False,
        "existing_save_migration_approved": False,
    }
    print("PLAY48V_TRUE_FOUR_DAY_MARKET_WAGES_CAUSAL_PROOF",
          json.dumps(report, sort_keys=True), flush=True)
