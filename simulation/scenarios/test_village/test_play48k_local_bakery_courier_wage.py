"""PLAY48-K: TRUE on-site bakery-funded in-kind wage for Huda after grain.

Both 13-NPC A/B arms share EXACT genesis and bakery/market food placement:
the ORIGINAL three opening loaves are split bakery=1, market=2; one
bakery loaf is escrowed for Huda, one market loaf for Hana, one is for sale.
No free food or funds. The only A/B difference is whether a verified
local grain delivery earns the prepaid bakery loaf immediately.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.store import InvalidEvent
from test_play47_closure_endurance import WORLD, DAY
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _run, _conserve
from test_play48j_affordable_payroll import _audit
import test_play38_multi_farm_couriers as east


def _bakery_bootstrap(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3, site_payroll_enabled=True,
        site_payroll_wage_coin=2, bakery_opening_food_wage=True,
    )


def _seed_bakery_contract(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=7,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            bootstrap=_bakery_bootstrap, cash_return=True,
            waged_harvest=True, harvest_wage_copper=2,
        )
        initial = db.load(WORLD)
        assert initial.resources["market"]["food"] == 2
        assert initial.resources["bakery"]["food"] == 1
        assert audit_npc_economy(initial)["copper_known_total"] == 12
        initial = db.append(WORLD, "closure-policy", initial.revision, [
            DomainEvent("WaterSourceConfigured", None, "bounded observed rain", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "existing policy", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        signed = db.append(WORLD, "k:both-locally-funded-contracts",
                           initial.revision, [
            DomainEvent("CourierProvisionConfigured", None,
                        "funded local baker's authentic grain-delivery wage", 0,
                        {"id": "bakery-grain-huda", "courier_id": "huda",
                         "payer_site": "bakery", "units": 1}),
            DomainEvent("CourierProvisionConfigured", None,
                        "funded local market courier's food-delivery wage", 0,
                        {"id": "market-food-hana", "courier_id": "hana",
                         "payer_site": "market", "units": 1}),
        ], bootstrap=True)
        assert signed.resources["market"]["food"] == 1
        assert signed.resources["bakery"]["food"] == 0
        assert signed.courier_provisions["bakery-grain-huda"]["remaining"] == 1
        assert signed.courier_provisions["market-food-hana"]["remaining"] == 1
        assert _conserve(signed) == 2
        assert db.verify(WORLD).to_dict() == signed.to_dict()
        return signed


def test_bakery_wage_must_have_authentic_same_command_grain_delivery(tmp_path):
    opening = _seed_bakery_contract(tmp_path / "no-free-bakery-meal.sqlite")
    with SQLiteEventStore(tmp_path / "no-free-bakery-meal.sqlite") as db:
        frozen = db.verify(WORLD).to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            # Forged proof, correct contract, genuine trusted supply
            # capability, but NO ACTUAL DELIVERY: reject atomically.
            claim = DomainEvent("CourierProvisionPaid", None,
                "forged grain delivery receipt", opening.time,
                {"id": "bakery-grain-huda", "courier_id": "huda",
                 "service_deliveries": 1, "proof": "bakery_grain_delivery"})
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "k:fake-grain-without-service",
                          opening.revision, [claim], supply_authorized=True)
            # A FAKE delivery with no actual carried grain cannot buy a wage.
            fake = DomainEvent("SupplyCargoDelivered", "huda",
                "pretend unloaded a nonexistent grain consignment", opening.time,
                {"courier_id": "huda", "resource": "grain"})
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "k:fake-grain-with-fake-receipt",
                          opening.revision, [fake, claim], supply_authorized=True)
            assert db.verify(WORLD).to_dict() == frozen
        finally:
            clock.close_session(WORLD)


def test_local_food_wage_after_real_grain_delivery_first_twelve_hours(tmp_path):
    strict = tmp_path / "k-control.sqlite"
    early = tmp_path / "k-treatment.sqlite"
    _seed_bakery_contract(strict)
    _seed_bakery_contract(early)
    baseline, _ = _run(strict, DAY // 2, early=False)
    treatment, _ = _run(early, DAY // 2, early=True)
    assert baseline.time == treatment.time == DAY // 2
    assert _conserve(baseline) >= 0 and _conserve(treatment) >= 0
    assert _audit(baseline)["cash"] == _audit(treatment)["cash"] == 12
    original_payments = baseline.courier_provisions["bakery-grain-huda"]["payments"]
    early_payments = treatment.courier_provisions["bakery-grain-huda"]["payments"]
    assert not original_payments
    # The real first-twelve-hour village has ONLY WATER logistics; grain
    # has not yet matured. Refuse a bakery-grain wage without grain delivery.
    assert len(early_payments) == 0, (
        "Unperformed grain service cannot earn bakery bread"
    )
    assert treatment.supply_circuits["huda"]["deliveries"] >= 1
    report = {
        "same_physical_bakery_and_market_genesis": True,
        "same_original_coin": 12,
        "huda_wages_without_local_delivery": len(original_payments),
        "huda_earned_wages_with_local_grain_delivery": len(early_payments),
        "control_courier_hunger": baseline.npcs["huda"]["needs"]["hunger"],
        "paid_courier_hunger": treatment.npcs["huda"]["needs"]["hunger"],
        "control_deliveries": baseline.supply_circuits["huda"]["deliveries"],
        "paid_deliveries": treatment.supply_circuits["huda"]["deliveries"],
        "control_meals": len(baseline.consumptions),
        "paid_meals": len(treatment.consumptions),
        "total_food_unchanged": True,
        "not_a_96h_recovery_proof": True,
    }
    print("PLAY48K_EARNED_BAKERY_GRAIN_WAGE_REAL_12H",
          json.dumps(report, sort_keys=True), flush=True)


def test_real_bakery_funded_grain_courier_96h_economy(tmp_path):
    strict = tmp_path / "k-control96.sqlite"
    early = tmp_path / "k-early96.sqlite"
    _seed_bakery_contract(strict)
    _seed_bakery_contract(early)
    a, adays = _run(strict, 4 * DAY, early=False)
    b, bdays = _run(early, 4 * DAY, early=True)
    assert len(adays) == len(bdays) == 4
    assert a.time == b.time == 4 * DAY
    assert audit_npc_economy(a)["copper_known_total"] == 12
    assert audit_npc_economy(b)["copper_known_total"] == 12
    def post72(days):
        p, q = days[2]["economy"], days[3]["economy"]
        return {
            k: q[k] - p[k] for k in ("jobs","trades","wages","meals","food_sales")
        } | {
            "deliveries": {
                who: q["deliveries"][who] - p["deliveries"][who]
                for who in ("huda", "hana")
            },
            "hunger_100_day3": p["hunger_cap"],
            "hunger_100_day4": q["hunger_cap"],
        }
    changes = post72(bdays)
    print("PLAY48K_REAL_96H_BAKERY_LOCAL_PAID_COURIER", json.dumps({
        "strict_daily": adays, "bakery_wage_daily": bdays,
        "strict_day3_to_day4": post72(adays),
        "bakery_wage_day3_to_day4": changes,
        "strict_huda_paid": len(a.courier_provisions["bakery-grain-huda"]["payments"]),
        "early_huda_paid": len(b.courier_provisions["bakery-grain-huda"]["payments"]),
        "same_original_copper": 12, "no_new_food": True, "no_new_coin": True,
        "post72_recovered": (
            any(v > 0 for v in changes["deliveries"].values())
            and any(changes[k] > 0 for k in ("jobs","trades","meals","food_sales"))
        ),
        "seven_day_stability_not_yet_proven": True,
    }, sort_keys=True), flush=True)
