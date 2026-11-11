"""PLAY-48Y2: four-day true NPC economy, Huda wages at her farm worksite.

This is an observation, not an outcome assertion. Both 13-person worlds have
the SAME 2 farm / 1 market opening bread and 12 actual copper. Only payment
timing for a genuine WATER delivery at the farm differs. The signed wage has
TWO finite prepaid loaves. No production stock, money or new skill is spawned.
"""
from __future__ import annotations

import json
from collections import Counter

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from test_play47_closure_endurance import DAY, WORLD
from test_play48h3_early_market_wage import _run, _conserve
from test_play48y_huda_farm_worksite_food_wage import _seed_farm_two_prepaid
from test_play48s_authentic_courier_food_wages import _stats, _check_wage_receipts


def _check_snapshot(state):
    original = state.to_dict()
    diag = audit_food_access_barriers(state)
    economy = audit_npc_economy(state)
    assert economy["copper_scope_complete"]
    assert economy["copper_known_total"] == 12
    assert diag["npc_count"] == 13
    by_role = Counter()
    starving_by_role = Counter()
    personally_spendable = Counter()
    for actor in diag["actors"]:
        role = actor["role"]
        by_role[role] += 1
        if actor["hunger"] >= 90:
            starving_by_role[role] += 1
        if (actor["copper_scope"] == "personal"
                and actor["personally_spendable_copper"] is not None):
            personally_spendable[role] += actor["personally_spendable_copper"]
    worker = state.courier_provisions["farm-water-huda"]
    assert (worker["total_units"], worker["authorized_total_units"]) == (2, 2)
    assert worker["remaining"] + len(worker["payments"]) == 2
    assert state.resources["market"]["food"] >= 0
    s = _stats(state)
    s.update({
        "total_completed_jobs": sum(
            j["status"] == "completed" for j in state.production_jobs.values()),
        "total_market_trades": len(state.market_trades),
        "workforce_by_role": dict(sorted(by_role.items())),
        "starving_90_by_role": dict(sorted(starving_by_role.items())),
        "real_personal_copper_by_role": dict(sorted(personally_spendable.items())),
        "market_food_open_offers": diag["opening_food_offer_count_currently_open"],
        "market_food_for_sale_at_site": diag["market_saleable_food_known"],
        "personally_funded_hungry_buyers_at_site": sum(
            a["hunger"] >= 90 and a["locally_affordable_now"]
            for a in diag["actors"]
        ),
        "hungry_with_no_personal_copper": sum(
            a["hunger"] >= 90 and
            (a["personally_spendable_copper"] is None or
             a["personally_spendable_copper"] == 0)
            for a in diag["actors"]
        ),
        "huda_at_or_beyond_courier_hunger_guard": (
            state.npcs["huda"]["needs"]["hunger"] >= 90
        ),
        "huda_remaining_prepaid_real_loaves": worker["remaining"],
    })
    assert state.to_dict() == original, "operator audit must NEVER change NPC data"
    return s


def _after72(a, b):
    fields = ("real_meals", "food_sales", "baked_batches", "cash_wages",
              "wood_sales", "charcoal_sales", "total_completed_jobs",
              "total_market_trades")
    delta = {k: b[k] - a[k] for k in fields}
    delta["deliveries"] = {
        who: b["couriers"][who]["deliveries"] -
             a["couriers"][who]["deliveries"]
        for who in ("huda", "hana")
    }
    assert all(n >= 0 for n in delta.values() if type(n) is int)
    assert all(n >= 0 for n in delta["deliveries"].values())
    return delta


def test_96h_huda_farm_wages_vs_true_identical_unpaid_world(tmp_path):
    unpaid_path = tmp_path / "farm-96h-control.sqlite"
    farm_paid_path = tmp_path / "farm-96h-paid.sqlite"
    control = _seed_farm_two_prepaid(unpaid_path)
    paid = _seed_farm_two_prepaid(farm_paid_path)
    assert control.to_dict() == paid.to_dict()
    assert (control.schema_version, control.rules_version) == (45, 62)
    assert len(control.npcs) == 13
    assert _conserve(control) == _conserve(paid) == 2

    days = []
    for day in (1, 2, 3, 4):
        a, _ = _run(
            unpaid_path, day * DAY,
            early=False, hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        b, _ = _run(
            farm_paid_path, day * DAY,
            early=True, hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        assert a.time == b.time == day * DAY
        assert len(a.npcs) == len(b.npcs) == 13
        assert _conserve(a) >= 0 and _conserve(b) >= 0
        for path, state in ((unpaid_path, a), (farm_paid_path, b)):
            with SQLiteEventStore(path) as db:
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        days.append({
            "day": day, "unpaid": _check_snapshot(a),
            "farm_paid": _check_snapshot(b),
        })

    _check_wage_receipts(farm_paid_path, b)
    assert len(a.courier_provisions["farm-water-huda"]["payments"]) == 0
    assert len(b.courier_provisions["farm-water-huda"]["payments"]) <= 2
    if days[1]["farm_paid"]["couriers"]["huda"]["food_eaten"] > 0:
        assert len(b.courier_provisions["farm-water-huda"]["payments"]) >= 1

    post72_unpaid = _after72(days[2]["unpaid"], days[3]["unpaid"])
    post72_farm = _after72(days[2]["farm_paid"], days[3]["farm_paid"])
    actual_post72_recovery = (
        sum(post72_farm["deliveries"].values()) > 0
        and post72_farm["real_meals"] > 0
        and (post72_farm["total_completed_jobs"] > 0
             or post72_farm["total_market_trades"] > 0)
    )
    print("PLAY48Y2_AUTHENTIC_96H_HUDA_FARM_WAGE_AND_THIRTEEN_INCOMES",
          json.dumps({
              "same_genesis_thirteen_people": True,
              "same_starting_three_real_loaves": True,
              "same_twelve_existing_copper_every_day": True,
              "strict_finite_two_loaf_prepaid_farm_employer": True,
              "same_real_water_rain_crops_wood_charcoal": True,
              "no_runtime_operator_spawning_or_manual_npc_commands": True,
              "daily_24_48_72_96": days,
              "after72_control": post72_unpaid,
              "after72_paid": post72_farm,
              "post72_genuine_simultaneous_recovery_observed": actual_post72_recovery,
              "seven_day_stable_economy_claimed": False,
              "new_farm_food_replenishment_implemented": False,
              "save_migration_approved": False,
              "phase48_release_approved": False,
          }, sort_keys=True), flush=True)
