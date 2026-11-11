"""PLAY-48W: two explicitly signed market couriers, genuine food payroll.

Different ownership-at-genesis from PLAY-48U, but both W A/B branches start
EXACTLY equal: all 3 historical bread loaves market-owned, 2 placed into real
escrow (one for each physically working courier), 1 remains for public sale.
The same owner pre-authorizes a hard 3-meal ceiling for each. Real later wages
must come from that market's recorded surplus bread; no food or coin printing.
This is a counterfactual employer contracting arrangement, NOT migration.
"""
from __future__ import annotations

import json

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import WORLD, DAY
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _run, _conserve
from test_play48s_authentic_courier_food_wages import _stats
from test_play48u_signed_market_refill import _read_receipts
import test_play38_multi_farm_couriers as east


def _three_real_opening_market_loaves(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3, site_payroll_enabled=True,
        site_payroll_wage_coin=2, wood_charcoal_jobs_enabled=True,
        farm_opening_food_wage=False,
    )


def _seed_both_market_couriers(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True, harvest_wage_copper=2,
            bootstrap=_three_real_opening_market_loaves,
        )
        state = db.load(WORLD)
        assert len(state.npcs) == 13
        assert state.resources["market"]["food"] == 3
        assert state.resources["lumberyard"]["standing_timber"] == 3
        state = db.append(WORLD, "w:bounded-rain-and-hunger", state.revision, [
            DomainEvent("WaterSourceConfigured", None, "same finite weather", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "normal hunger", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        contracts = [
            DomainEvent("CourierProvisionConfigured", None,
                        "merchant's actual pre-owned bread and explicit worker agreement",
                        0, {"id": f"market-courier-{who}", "courier_id": who,
                            "payer_site": "market", "units": 1,
                            "authorized_total_units": 3})
            for who in ("huda", "hana")
        ]
        signed = db.append(WORLD, "w:merchant-signs-two-workers",
                           state.revision, contracts, bootstrap=True)
        assert signed.resources["market"]["food"] == 1
        assert sum(c["remaining"] for c in signed.courier_provisions.values()) == 2
        assert all(c["authorized_total_units"] == 3
                   for c in signed.courier_provisions.values())
        assert audit_npc_economy(signed)["copper_known_total"] == 12
        assert _conserve(signed) == 2
        assert db.verify(WORLD).to_dict() == signed.to_dict()
        return signed


def test_genuine_two_courier_employer_signing_from_same_three_loaves(tmp_path):
    s = _seed_both_market_couriers(tmp_path / "w-real-genesis.sqlite")
    assert s.schema_version == 44 and s.rules_version == 59
    assert len(s.courier_provisions) == 2
    assert s.resources["market"]["food"] == 1
    assert s.resources["huda"]["food"] == 0
    assert s.resources["hana"]["food"] == 0
    assert len(s.npcs) == 13
    assert sum(v.get("food", 0) for v in s.resources.values()) + sum(
        c["remaining"] for c in s.courier_provisions.values()
    ) == 3
    assert all(c["total_units"] == 1 and c["authorized_total_units"] == 3
               for c in s.courier_provisions.values())


def test_true_48h_13npc_two_signed_market_couriers_counterfactual(tmp_path):
    control_path = tmp_path / "w-control-1-meal-each.sqlite"
    renew_path = tmp_path / "w-real-merchant-payroll.sqlite"
    old = _seed_both_market_couriers(control_path)
    new = _seed_both_market_couriers(renew_path)
    assert old.to_dict() == new.to_dict()
    checkpoints = []
    for day in (1, 2):
        a, _ = _run(control_path, day * DAY, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    market_sourced_wage_refill_enabled=False)
        b, _ = _run(renew_path, day * DAY, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    market_sourced_wage_refill_enabled=True)
        assert a.time == b.time == day * DAY
        assert _conserve(a) >= 0 and _conserve(b) >= 0
        assert audit_npc_economy(a)["copper_known_total"] == 12
        assert audit_npc_economy(b)["copper_known_total"] == 12
        assert len(a.npcs) == len(b.npcs) == 13
        for path, state in ((control_path, a), (renew_path, b)):
            with SQLiteEventStore(path) as db:
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        checkpoints.append({
            "day": day, "original_signed_one_off": _stats(a),
            "actual_employer_funded": _stats(b),
            "real_local_market_refills": _read_receipts(renew_path, b),
        })
    assert _read_receipts(control_path, a) == 0
    assert 0 <= _read_receipts(renew_path, b) <= 4
    for worker in ("huda", "hana"):
        c = b.courier_provisions[f"market-courier-{worker}"]
        assert c["total_units"] <= c["authorized_total_units"] == 3
        assert len(c["payments"]) <= 3

    print("PLAY48W_TWO_MARKET_COURIERS_REAL_48H_AB",
          json.dumps({
              "same_initial_world_inside_this_A_B": True,
              "different_from_U_initial_site_ownership_declared": True,
              "same_13_npcs_3_loaves_12_copper": True,
              "old_contracts_not_auto_renewed": True,
              "real_refills_by_48h": _read_receipts(renew_path, b),
              "days": checkpoints,
              "additional_meals_from_physical_signed_wages":
                  checkpoints[-1]["actual_employer_funded"]["real_meals"] -
                  checkpoints[-1]["original_signed_one_off"]["real_meals"],
              "post72_proven": False, "seven_day_stability_proven": False,
          }, sort_keys=True), flush=True)
