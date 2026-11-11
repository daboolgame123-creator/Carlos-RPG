"""PLAY-48Y: physical Huda FARM worksite salary, not an unreachable market contract.

Two of the same THREE existing original loaves begin physically owned by
the farm, one stays for market sale. A genuine employer signs and escrows
both farm loaves at t=0; no new bread, no extra people or funds. The control
and salary arm share EXACTLY the same genesis, and ONLY opt-in earned
farm-water-delivery wage timing differs. This is a finite emergency
income-access hypothesis, NOT renewable production or seven-day recovery.
"""
from __future__ import annotations

import json

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import DAY, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _run, _conserve
from test_play48s_authentic_courier_food_wages import _stats, _check_wage_receipts
import test_play38_multi_farm_couriers as east


def _two_existing_loaves_owned_at_farm(db, *, initial_market_food, **opts):
    assert initial_market_food == 3
    assert opts == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    # This fixture CREATES the world; it does not return an event-transformer.
    # Two farm loaves, one market loaf are physically declared at genesis.
    return _joined_bootstrap(
        db, initial_market_food=3, site_payroll_enabled=True,
        site_payroll_wage_coin=2, wood_charcoal_jobs_enabled=True,
        farm_opening_food_wage=True, farm_initial_food_loaves=2,
    )

def _seed_farm_two_prepaid(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True, harvest_wage_copper=2,
            bootstrap=_two_existing_loaves_owned_at_farm,
        )
        state = db.load(WORLD)
        assert state.resources["farm"]["food"] == 2
        assert state.resources["market"]["food"] == 1
        assert len(state.npcs) == 13
        assert audit_npc_economy(state)["copper_known_total"] == 12
        state = db.append(WORLD, "y:real-weather-and-consumption", state.revision, [
            DomainEvent("WaterSourceConfigured", None, "same finite observed rain", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "physical human hunger", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        state = db.append(WORLD, "y:employer-owned-real-farm-payroll", state.revision, [
            DomainEvent("CourierProvisionConfigured", None,
                        "two farm-owned loaves pay actual worker water deliveries", 0,
                        {"id": "farm-water-huda", "courier_id": "huda",
                         "payer_site": "farm", "units": 2}),
        ], bootstrap=True)
        assert state.resources["farm"]["food"] == 0
        assert state.resources["market"]["food"] == 1
        assert state.courier_provisions["farm-water-huda"]["total_units"] == 2
        assert state.courier_provisions["farm-water-huda"]["authorized_total_units"] == 2
        assert state.courier_provisions["farm-water-huda"]["remaining"] == 2
        assert _conserve(state) == 2
        assert db.verify(WORLD).to_dict() == state.to_dict()
        return state


def test_actual_two_farm_owned_loaves_genesis_preserves_all_resources(tmp_path):
    s = _seed_farm_two_prepaid(tmp_path / "y-genesis.sqlite")
    assert (s.schema_version, s.rules_version) == (45, 60)
    assert len(s.npcs) == 13
    assert audit_npc_economy(s)["copper_known_total"] == 12
    assert sum(v.get("food", 0) for v in s.resources.values()) + sum(
        c["remaining"] for c in s.courier_provisions.values()
    ) == 3
    assert s.resources["market"]["food"] == 1
    assert s.resources["huda"]["food"] == 0
    assert s.farm_plots["farm_east"]["growth_seconds"] == DAY
    assert s.production_recipes["east-finite-harvest"]["output_amount"] == 12


def test_authentic_13npc_48h_farm_worksite_wages_vs_identical_prepaid_control(tmp_path):
    control_path = tmp_path / "y-identical-unpaid-farm.sqlite"
    paid_path = tmp_path / "y-identical-paid-farm.sqlite"
    original = _seed_farm_two_prepaid(control_path)
    target = _seed_farm_two_prepaid(paid_path)
    assert original.to_dict() == target.to_dict()
    entries = []
    for day in (1, 2):
        control, _ = _run(
            control_path, day * DAY, early=False,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        paid, _ = _run(
            paid_path, day * DAY, early=True,
            hungry_woodcutter_work_enabled=True,
            retry_known_supplier_enabled=True,
        )
        assert control.time == paid.time == day * DAY
        assert _conserve(control) >= 0 and _conserve(paid) >= 0
        assert len(control.npcs) == len(paid.npcs) == 13
        for path, state in ((control_path, control), (paid_path, paid)):
            assert audit_npc_economy(state)["copper_known_total"] == 12
            with SQLiteEventStore(path) as db:
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        _check_wage_receipts(paid_path, paid)
        entries.append({
            "day": day, "no_early_pay": _stats(control),
            "true_farm_water_pay": _stats(paid),
        })
    old_contract = control.courier_provisions["farm-water-huda"]
    wage = paid.courier_provisions["farm-water-huda"]
    assert old_contract["remaining"] == 2 and not old_contract["payments"]
    assert wage["authorized_total_units"] == wage["total_units"] == 2
    assert 1 <= len(wage["payments"]) <= 2
    assert all(p["service_deliveries"] >= 1 for p in wage["payments"])
    print("PLAY48Y_REAL_13NPC_FARM_WORKSITE_48H_FOOD_ACCESS",
          json.dumps({
              "same_authentic_world_start": True,
              "same_initial_three_loaves_two_at_farm_one_at_market": True,
              "same_thirteen_npcs_and_twelve_real_coins": True,
              "same_finite_water_and_east_farm_crop": True,
              "only_optin_difference": "early authenticated farm-water-wage payment",
              "days": entries,
              "farm_paid_real_loaves": len(wage["payments"]),
              "additional_real_huda_meals":
                  entries[-1]["true_farm_water_pay"]["couriers"]["huda"]["food_eaten"] -
                  entries[-1]["no_early_pay"]["couriers"]["huda"]["food_eaten"],
              "signed_contract_finite_and_exhaustible": True,
              "sustainable_new_food_or_loan_injected": False,
              "post72_recovery_claimed": False,
              "seven_day_recovery_proven": False,
              "production_save_migration_approved": False,
          }, sort_keys=True), flush=True)
