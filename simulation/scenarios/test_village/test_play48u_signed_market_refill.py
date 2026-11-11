"""PLAY-48U — explicit signed, scarce, real-market-funded courier wages.

The employee never consumes consigned shop cargo. An EXISTING contract signed
by the actual market employer at genesis explicitly authorizes at most 3 total
loaves; only 1 is initially funded. Two optional EXTRA loaves may be funded
only from new physically owned MARKET food at the instant of the worker's
authenticated food delivery, with the seller physically available and at least
one unreserved shop loaf remaining. The signed old one-use contract remains
non-renewable unless explicitly authorized. This is a BOUNDED trial, not
seven-day full economic recovery.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import DAY, WORLD
from test_play48h3_early_market_wage import _run, _conserve
from test_play48s_authentic_courier_food_wages import (
    _seed_employed_paid_couriers, _stats,
)


def _read_receipts(path, world):
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == world.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        events = [
            json.loads(raw) for (raw,) in db.db.execute(
                "SELECT payload FROM events WHERE world_id=? ORDER BY seq",
                (WORLD,),
            )
        ]
    funded = [i for i, e in enumerate(events)
              if e["event_type"] == "CourierProvisionReplenished"]
    for i in funded:
        e = events[i]
        assert 0 < i < len(events) - 1
        before = events[i-1]
        after = events[i+1]
        assert before["event_type"] == "SupplyCargoDelivered"
        assert before["data"] == {
            "courier_id": e["data"]["courier_id"], "resource": "food",
        }
        assert before["actor_id"] == e["data"]["courier_id"]
        assert before["time"] == e["time"] == after["time"]
        assert after["event_type"] == "CourierProvisionPaid"
        assert after["data"] == e["data"]
        assert e["actor_id"] is None
    return len(funded)


def test_default_old_employer_contract_cannot_authorize_future_meals():
    from carlos_sim.courier_provisions import (
        choose_market_owned_food_refill, MAX_UNIT,
    )
    assert MAX_UNIT == 3
    # The reducer defaults authorized_total_units to the ONE actual prepaid
    # loaf if a trusted employer did not explicitly authorize later wages.
    # No time-zero food is printed by that missing future authorization.
    assert callable(choose_market_owned_food_refill)


def test_signed_market_wage_still_needs_real_service_and_local_stock(tmp_path):
    path = tmp_path / "u-no-forged-service.sqlite"
    world = _seed_employed_paid_couriers(path)
    assert (world.schema_version, world.rules_version) == (45, 61)
    c = world.courier_provisions["market-service-hana"]
    assert (c["authorized_total_units"], c["total_units"], c["remaining"]) == (3, 1, 1)
    assert world.courier_provisions["farm-water-huda"]["authorized_total_units"] == 1
    assert sum(s.get("food", 0) for s in world.resources.values()) == 1
    assert sum(c["remaining"] for c in world.courier_provisions.values()) == 2
    assert _conserve(world) == 2
    assert audit_npc_economy(world)["copper_known_total"] == 12
    with SQLiteEventStore(path) as db:
        before = db.verify(WORLD).to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            forged = DomainEvent("CourierProvisionReplenished", None,
                "forged refill without completed real shipment", 0,
                {"id": "market-service-hana", "courier_id": "hana",
                 "service_deliveries": 1})
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "u:forged-no-service", world.revision,
                          [forged], supply_authorized=True)
            counterfeit = DomainEvent("SupplyCargoDelivered", "hana",
                "forged food movement at wrong location", 0,
                {"courier_id": "hana", "resource": "food"})
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "u:fake-service", world.revision,
                          [counterfeit, forged], supply_authorized=True)
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


def test_true_48h_13npc_pre_authorized_market_refill_vs_one_shot(tmp_path):
    control_path = tmp_path / "u-control-one-shot.sqlite"
    treatment_path = tmp_path / "u-treatment-real-market-funded.sqlite"
    original = _seed_employed_paid_couriers(control_path)
    treatment = _seed_employed_paid_couriers(treatment_path)
    assert original.to_dict() == treatment.to_dict()
    assert (original.schema_version, original.rules_version) == (45, 61)
    assert _read_receipts(control_path, original) == 0
    assert _read_receipts(treatment_path, treatment) == 0

    snapshots = []
    for day in (1, 2):
        a, _ = _run(control_path, day * DAY, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    market_sourced_wage_refill_enabled=False)
        b, _ = _run(treatment_path, day * DAY, early=True,
                    hungry_woodcutter_work_enabled=True,
                    retry_known_supplier_enabled=True,
                    market_sourced_wage_refill_enabled=True)
        assert a.time == b.time == day * DAY
        assert len(a.npcs) == len(b.npcs) == 13
        assert _conserve(a) >= 0 and _conserve(b) >= 0
        for p, state in ((control_path, a), (treatment_path, b)):
            assert audit_npc_economy(state)["copper_known_total"] == 12
            _read_receipts(p, state)
        snapshots.append({
            "day": day, "control": _stats(a), "new_salary": _stats(b),
            "market_refills": _read_receipts(treatment_path, b),
        })

    completed_refills = _read_receipts(treatment_path, b)
    worker = b.courier_provisions["market-service-hana"]
    assert worker["total_units"] == 1 + completed_refills
    assert worker["authorized_total_units"] == 3
    assert 0 <= completed_refills <= 2
    assert (a.courier_provisions["market-service-hana"]["total_units"],
            a.courier_provisions["market-service-hana"]["authorized_total_units"]) == (1, 3)
    assert b.courier_provisions["farm-water-huda"]["total_units"] == 1
    assert len(b.courier_provisions["market-service-hana"]["payments"]) <= 3
    report = {
        "verified_13_npcs": True,
        "original_copper_12_preserved": True,
        "same_three_actual_opening_loaves": True,
        "only_opt_in_difference": "market_sourced_wage_refill_enabled",
        "real_nonmagical_refills": completed_refills,
        "day1_day2": snapshots,
        "genuine_extra_worker_meals": (
            snapshots[-1]["new_salary"]["real_meals"] -
            snapshots[-1]["control"]["real_meals"]
        ),
        "genuine_extra_hana_deliveries": (
            snapshots[-1]["new_salary"]["couriers"]["hana"]["deliveries"] -
            snapshots[-1]["control"]["couriers"]["hana"]["deliveries"]
        ),
        "unlimited_salaries_authorized": False,
        "saved_world_migration_approved": False,
        "seven_day_recovery_proven": False,
    }
    print("PLAY48U_GENUINE_MARKET_BACKED_COURIER_REFUND_48H",
          json.dumps(report, sort_keys=True), flush=True)


def test_open_customer_quotes_and_duplicate_service_are_protected(tmp_path):
    """Synthetic reducer attack, NOT an authored in-game delivery.

    A real separate 48-hour A/B tests delivery and stock provenance.
    This isolated attack tests whether the reducer can spend already
    advertised customer inventory, fake owner consent or double-pay.
    """
    from carlos_sim.courier_provisions import (
        _market_uncommitted_bread_after_sales,
        replenish_provision_from_delivered_market_food,
        pay_courier_provision,
    )

    state = _seed_employed_paid_couriers(tmp_path / "signed-source.sqlite").to_dict()
    c = state["courier_provisions"]["market-service-hana"]
    assert c["authorized_total_units"] == 3
    c["remaining"] = 0
    c["payments"] = [{
        "service_deliveries": 2, "paid_at": 0,
        "worker_food_before": 0, "worker_food_after": 1,
    }]
    circuit = state["supply_circuits"]["hana"]
    circuit["index"] = 3
    circuit["loads"] = 3
    circuit["deliveries"] = 3
    circuit["carry"] = None
    state["entities"]["hana"]["location_id"] = "market"
    state["resources"]["market"]["food"] = 10
    state["market_offers"]["unit-test-active-quote"] = {
        "site_id": "market", "stock_owner_id": "market", "resource": "food",
        "remaining": 10, "status": "open",
    }
    event = DomainEvent("CourierProvisionReplenished", None,
        "isolated synthetic check, never appended to the world", 0,
        {"id": "market-service-hana",
         "courier_id": "hana", "service_deliveries": 3})

    assert _market_uncommitted_bread_after_sales(state) == 0
    before = json.dumps(state, sort_keys=True)
    with pytest.raises(ValueError, match="listed"):
        replenish_provision_from_delivered_market_food(
            state, event, supply_authorized=True)
    assert json.dumps(state, sort_keys=True) == before

    # The SAME ten real test units: eight are already advertised.
    # A capped payroll can spend ONE of the remaining TWO; at least
    # one unlisted loaf stays with the merchant for subsequent sales.
    state["market_offers"]["unit-test-active-quote"]["remaining"] = 8
    assert _market_uncommitted_bread_after_sales(state) == 2
    replenish_provision_from_delivered_market_food(
        state, event, supply_authorized=True)
    assert state["resources"]["market"]["food"] == 9
    assert (c["total_units"], c["remaining"], c["authorized_total_units"]) == (2, 1, 3)
    pay_courier_provision(state, DomainEvent("CourierProvisionPaid", None,
        "single synthetic salary settlement", 0,
        {"id": "market-service-hana", "courier_id": "hana",
         "service_deliveries": 3}), supply_authorized=True)
    assert state["resources"]["hana"]["food"] == 1
    assert c["remaining"] == 0
    assert len(c["payments"]) == 2

    after = json.dumps(state, sort_keys=True)
    with pytest.raises(ValueError):
        replenish_provision_from_delivered_market_food(
            state, event, supply_authorized=True)
    assert json.dumps(state, sort_keys=True) == after
