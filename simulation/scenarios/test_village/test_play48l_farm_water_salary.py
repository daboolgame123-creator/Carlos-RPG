"""PLAY48-L — employer-owned food wage at the *first productive farm stop*.

A field employer reserves ONE existing real loaf at genesis for Huda.
ONLY an authenticated on-site WATER delivery to this precise field
earns it. With a 24-hour harvest delay, paid water supply can happen
well before the hypothetical bakery-grain salary would be payable.

Same thirteen NPCs, same 12 known copper and 3 opening loaves in two
worlds. Both have field=1, market=2 BEFORE the wage debits; same
existing two funded wages (Huda farm, Hana market), same roads and weather.
Only the pay-on-authentic-delivery policy changes between A/B arms.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import WORLD, DAY
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _run, _conserve
from test_play48j_affordable_payroll import _audit
import test_play38_multi_farm_couriers as east


def _field_genesis(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(db, initial_market_food=3,
                             site_payroll_enabled=True, site_payroll_wage_coin=2,
                             farm_opening_food_wage=True)


def _seed_field_contract(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=7,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            bootstrap=_field_genesis, cash_return=True,
            waged_harvest=True, harvest_wage_copper=2,
        )
        initial = db.load(WORLD)
        assert len(initial.npcs) == 13
        assert initial.resources["farm"]["food"] == 1
        assert initial.resources["market"]["food"] == 2
        assert audit_npc_economy(initial)["copper_known_total"] == 12
        initial = db.append(WORLD, "closure-policy", initial.revision, [
            DomainEvent("WaterSourceConfigured", None, "bounded rain", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "same original policy", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        signed = db.append(WORLD, "l:both-genuine-on-site-contracts",
                           initial.revision, [
            DomainEvent("CourierProvisionConfigured", None,
                        "actual farmer employer pre-funds carried water wage", 0,
                        {"id": "field-water-huda", "courier_id": "huda",
                         "payer_site": "farm", "units": 1}),
            DomainEvent("CourierProvisionConfigured", None,
                        "actual market employer pre-funds outbound food courier", 0,
                        {"id": "market-food-hana", "courier_id": "hana",
                         "payer_site": "market", "units": 1}),
        ], bootstrap=True)
        assert signed.resources["farm"]["food"] == 0
        assert signed.resources["market"]["food"] == 1
        assert _conserve(signed) == 2
        assert db.verify(WORLD).to_dict() == signed.to_dict()
        return signed


def test_zero_service_no_courier_meal_or_ownership_forgery(tmp_path):
    path = tmp_path / "field-fake-no-water.sqlite"
    state = _seed_field_contract(path)
    with SQLiteEventStore(path) as db:
        before = db.verify(WORLD).to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            fake_pay = DomainEvent("CourierProvisionPaid", None,
                "fraud: never delivered water", state.time,
                {"id": "field-water-huda", "courier_id": "huda",
                 "service_deliveries": 1, "proof": "farm_water_delivery"})
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "l:forged-no-service", state.revision,
                          [fake_pay], supply_authorized=True)
            fake_cargo = DomainEvent("SupplyCargoDelivered", "huda",
                "forged no-water cargo", state.time,
                {"courier_id": "huda", "resource": "water"})
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "l:forged-cargo", state.revision,
                          [fake_cargo, fake_pay], supply_authorized=True)
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


def test_real_first_water_delivery_triggers_exactly_one_prepaid_field_meal(tmp_path):
    control, treated = (tmp_path / "l-control12.sqlite",
                        tmp_path / "l-field-water12.sqlite")
    _seed_field_contract(control)
    _seed_field_contract(treated)
    a, _ = _run(control, DAY // 2, early=False)
    b, _ = _run(treated, DAY // 2, early=True)
    assert a.time == b.time == DAY // 2
    assert _conserve(a) == 2
    assert _conserve(b) in (0, 1, 2)
    assert _audit(a)["cash"] == _audit(b)["cash"] == 12
    unpaid = a.courier_provisions["field-water-huda"]
    earned = b.courier_provisions["field-water-huda"]
    assert not unpaid["payments"]
    assert len(earned["payments"]) == 1, (
        "Huda must earn one bread for physical water supply, never as welfare"
    )
    assert earned["remaining"] == 0
    assert earned["payments"][0]["service_deliveries"] >= 1
    assert b.resources["huda"]["food"] + sum(
        meal["quantity"] for meal in b.consumptions.values()
        if meal["npc_id"] == "huda"
    ) >= 1
    # The actual durable event sequence, not just a mutable service count,
    # proves one EXACT same-worker earlier grain/water supply work.
    with SQLiteEventStore(treated) as db:
        rows = [json.loads(row[0]) for row in db.db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq", (WORLD,)
        )]
        wage_at = [i for i, x in enumerate(rows)
                   if x["event_type"] == "CourierProvisionPaid"
                   and x["data"]["id"] == "field-water-huda"]
        assert len(wage_at) == 1
        wage = rows[wage_at[0]]
        delivery = rows[wage_at[0]-1]
        assert delivery["event_type"] == "SupplyCargoDelivered"
        assert delivery["data"] == {"courier_id": "huda", "resource": "water"}
        assert delivery["actor_id"] == "huda"
        assert delivery["time"] == wage["time"]
        assert db.verify(WORLD).to_dict() == b.to_dict()
    print("PLAY48L_GENUINE_12H_FIELD_WATER_WAGE", json.dumps({
        "unpaid_original": len(unpaid["payments"]),
        "earned_after_water": len(earned["payments"]),
        "opening_owned_bread_total": 3,
        "known_copper_total": 12,
        "huda_hunger_original": a.npcs["huda"]["needs"]["hunger"],
        "huda_hunger_paid": b.npcs["huda"]["needs"]["hunger"],
        "huda_owned_food_original": a.resources["huda"]["food"],
        "huda_owned_food_paid": b.resources["huda"]["food"],
        "huda_water_and_goods_deliveries_original": a.supply_circuits["huda"]["deliveries"],
        "huda_water_and_goods_deliveries_paid": b.supply_circuits["huda"]["deliveries"],
        "no_resource_creation": True,
        "no_manual_worker_action": True,
        "not_recovery_proof": True,
    }, sort_keys=True), flush=True)


def test_real_field_paid_courier_genuine_96h_causal_endurance(tmp_path):
    control, treatment = (tmp_path / "l-control96.sqlite",
                          tmp_path / "l-fed-courier96.sqlite")
    _seed_field_contract(control)
    _seed_field_contract(treatment)
    a, adays = _run(control, 4 * DAY, early=False)
    b, bdays = _run(treatment, 4 * DAY, early=True)
    assert a.time == b.time == 4 * DAY
    assert len(adays) == len(bdays) == 4
    assert audit_npc_economy(a)["copper_known_total"] == 12
    assert audit_npc_economy(b)["copper_known_total"] == 12
    def delta(rows):
        x, y = rows[2]["economy"], rows[3]["economy"]
        return {
            key: y[key]-x[key] for key in ("jobs","trades","wages","meals","food_sales")
        } | {"deliveries": {
            who: y["deliveries"][who]-x["deliveries"][who]
            for who in ("huda", "hana")
        }, "hunger_100_day3": x["hunger_cap"],
           "hunger_100_day4": y["hunger_cap"]}
    activity = delta(bdays)
    print("PLAY48L_TRUE_96H_FIELD_COURIER_EMPLOYMENT", json.dumps({
        "same_three_initial_loaves_and_twelve_coins": True,
        "ordinary_wage_price": 2,
        "control_days": adays, "paid_courier_days": bdays,
        "control_post72": delta(adays),
        "paid_post72": activity,
        "control_huda_paid": len(a.courier_provisions["field-water-huda"]["payments"]),
        "treatment_huda_paid": len(b.courier_provisions["field-water-huda"]["payments"]),
        "real_post72_recovery": (
            any(v > 0 for v in activity["deliveries"].values())
            and any(activity[k] > 0
                    for k in ("jobs","trades","meals","food_sales"))
        ),
        "no_magic_food_or_cash": True, "seven_day_recovery_not_yet_claimed": True,
    }, sort_keys=True), flush=True)
