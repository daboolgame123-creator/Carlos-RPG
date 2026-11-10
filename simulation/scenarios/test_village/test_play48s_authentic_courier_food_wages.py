"""PLAY-48S: real, employer-funded courier food wages in the fertile 13-NPC village.

Zero added bread, copper, people, paths, or magic earnings. Both villages start
from an identical, authenticated trusted genesis: of the THREE existing loaves,
one is farm-owned, two market-owned; the real farm and market employers each
pre-fund ONE loaf to actual Huda/Hana. The sole treatment difference is whether
the engine pays those already-funded in-kind wages upon verified local service.
No subsequent privileged operator decisions, welfare, cargo-eating or bypass of
the hunger safety guard. This is a *finite* wage trial, not a repeatable payroll.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.store import InvalidEvent
from test_play47_closure_endurance import WORLD, DAY
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _conserve, _run
from test_play48m_finite_employment import _real_stats
import test_play38_multi_farm_couriers as east

FERTILE_YIELD = 12


def _wood_farm_employed_genesis(db, *, initial_market_food, **options):
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
        farm_opening_food_wage=True,
    )


def _seed_employed_paid_couriers(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=FERTILE_YIELD,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True, harvest_wage_copper=2,
            bootstrap=_wood_farm_employed_genesis,
        )
        initial = db.load(WORLD)
        assert len(initial.npcs) == 13
        assert initial.resources["farm"]["food"] == 1
        assert initial.resources["market"]["food"] == 2
        assert initial.resources["lumberyard"]["standing_timber"] == 3
        initial = db.append(WORLD, "closure-policy", initial.revision, [
            DomainEvent("WaterSourceConfigured", None, "bounded recorded rain", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "existing real hunger", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        signed = db.append(
            WORLD, "s:both-finite-funded-local-contracts", initial.revision, [
                DomainEvent("CourierProvisionConfigured", None,
                            "employer's existing loaf earned for real water delivery", 0,
                            {"id": "farm-water-huda", "courier_id": "huda",
                             "payer_site": "farm", "units": 1}),
                DomainEvent("CourierProvisionConfigured", None,
                            "market employer's existing loaf for delivered goods", 0,
                            {"id": "market-service-hana", "courier_id": "hana",
                             "payer_site": "market", "units": 1}),
            ], bootstrap=True,
        )
        assert signed.resources["farm"]["food"] == 0
        assert signed.resources["market"]["food"] == 1
        assert _conserve(signed) == 2
        assert audit_npc_economy(signed)["copper_known_total"] == 12
        assert db.verify(WORLD).to_dict() == signed.to_dict()
        return signed


def _stats(state):
    economy = _real_stats(state)
    escrow = {
        cid: {
            "remaining": c["remaining"],
            "paid": len(c["payments"]),
            "worker": c["courier_id"],
        }
        for cid, c in sorted(state.courier_provisions.items())
    }
    return {
        "time": state.time,
        "hunger100": economy["hunger_100"],
        "real_meals": economy["meals"],
        "food_sales": economy["bread_sales"],
        "baked_batches": sum(
            j["status"] == "completed" and
            state.production_recipes[j["recipe_id"]]["output_resource"] == "food"
            for j in state.production_jobs.values()
        ),
        "market_food": state.resources["market"]["food"],
        "copper_total": economy["copper_total"],
        "wood_sales": economy["wood_sales"],
        "charcoal_sales": economy["charcoal_sales"],
        "cash_wages": economy["wages_paid"],
        "escrow": escrow,
        "couriers": {
            who: {
                "hunger": state.npcs[who]["needs"]["hunger"],
                "food_owned": state.resources[who]["food"],
                "food_eaten": sum(
                    meal["quantity"] for meal in state.consumptions.values()
                    if meal["npc_id"] == who
                ),
                "deliveries": state.supply_circuits[who]["deliveries"],
            } for who in ("huda", "hana")
        },
    }


def _check_wage_receipts(path, state):
    with SQLiteEventStore(path) as db:
        original = state.to_dict()
        assert db.verify(WORLD).to_dict() == original
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        # The trusted reducer validates the same committed command as the
        # actual service. A legitimate ScheduledEventFired or other causal
        # event can appear between service and payment, so adjacency alone is
        # an incorrect test oracle. SQLite's command_id is durable provenance.
        rows = list(db.db.execute(
            "SELECT command_id, payload FROM events WHERE world_id=? ORDER BY seq",
            (WORLD,),
        ))
        events = [(command, json.loads(payload)) for command, payload in rows]
        payments = [i for i, (_, e) in enumerate(events)
                    if e["event_type"] == "CourierProvisionPaid"]
        assert sum(len(c["payments"]) for c in state.courier_provisions.values()) == len(payments)
        for i in payments:
            command, paid = events[i]
            assert i > 0
            who = paid["data"]["courier_id"]
            contract = state.courier_provisions[paid["data"]["id"]]
            payer = contract["payer_site"]
            proof = paid["data"].get("proof")
            allowed_resource = (
                {"water"} if payer == "farm" else
                {"grain"} if payer == "bakery" else
                {"food"} if proof is None else {"water", "grain", "food"}
            )
            same_command_service = [
                delivery for service_cmd, delivery in events[:i]
                if service_cmd == command
                and delivery["event_type"] == "SupplyCargoDelivered"
                and delivery["actor_id"] == who
                and delivery["time"] == paid["time"]
                and delivery["data"]["courier_id"] == who
                and delivery["data"]["resource"] in allowed_resource
            ]
            assert same_command_service, "No same-command genuine service for earned wage"
            assert paid["data"]["service_deliveries"] <= state.supply_circuits[who]["deliveries"]
        assert state.to_dict() == original


def test_prepaid_fertile_13npc_genesis_conserves_existing_food_and_currency(tmp_path):
    state = _seed_employed_paid_couriers(tmp_path / "s-genesis.sqlite")
    assert state.time == 0
    assert set(state.courier_provisions) == {
        "farm-water-huda", "market-service-hana"
    }
    assert len(state.npcs) == 13
    assert sum(stock.get("food", 0) for stock in state.resources.values()) == 1
    assert sum(c["remaining"] for c in state.courier_provisions.values()) == 2
    assert sum(stock.get("water", 0) for stock in state.resources.values()) == 2
    assert sum(stock.get("coin_copper", 0) for stock in state.resources.values()) == 12
    assert state.production_recipes["east-finite-harvest"]["output_amount"] == FERTILE_YIELD
    assert state.production_recipes["finite-timber-cutting"]["output_amount"] == 1


def test_early_wage_cannot_be_forged_before_real_water_delivery(tmp_path):
    path = tmp_path / "s-fake.sqlite"
    state = _seed_employed_paid_couriers(path)
    with SQLiteEventStore(path) as db:
        original = db.verify(WORLD).to_dict()
        fake = DomainEvent("CourierProvisionPaid", None,
            "forged food salary without water service", 0,
            {"id": "farm-water-huda", "courier_id": "huda",
             "service_deliveries": 1, "proof": "farm_water_delivery"})
        with pytest.raises((InvalidEvent, ValueError)):
            db.append(WORLD, "forged-pay-no-service",
                      state.revision, [fake], supply_authorized=True)
        assert db.verify(WORLD).to_dict() == original


def test_first_twelve_hours_real_water_wage_is_food_not_magic(tmp_path):
    control, paid = tmp_path / "s-twelve-unpaid.sqlite", tmp_path / "s-twelve-paid.sqlite"
    _seed_employed_paid_couriers(control)
    _seed_employed_paid_couriers(paid)
    a, _ = _run(
        control, DAY // 2, early=False,
        hungry_woodcutter_work_enabled=True, retry_known_supplier_enabled=True,
    )
    b, _ = _run(
        paid, DAY // 2, early=True,
        hungry_woodcutter_work_enabled=True, retry_known_supplier_enabled=True,
    )
    assert a.time == b.time == DAY // 2
    assert _conserve(a) >= 0 and _conserve(b) >= 0
    assert not a.courier_provisions["farm-water-huda"]["payments"]
    assert len(b.courier_provisions["farm-water-huda"]["payments"]) == 1
    assert b.resources["huda"]["food"] + sum(
        meal["quantity"] for meal in b.consumptions.values()
        if meal["npc_id"] == "huda"
    ) >= 1
    _check_wage_receipts(paid, b)
    print("PLAY48S_REAL_FUNDED_FIRST_WATER_WAGE_12H",
          json.dumps({"control": _stats(a), "salary": _stats(b),
                      "same_3_existing_initial_loaves": True,
                      "huda_employer_sanctioned_water_service": True,
                      "persistent_recovery_claimed": False},
                     sort_keys=True), flush=True)


def test_true_13npc_48h_food_wages_vs_reserved_unpaid_couriers(tmp_path):
    control, paid = tmp_path / "s-48-unpaid.sqlite", tmp_path / "s-48-paid.sqlite"
    _seed_employed_paid_couriers(control)
    _seed_employed_paid_couriers(paid)
    results = []
    for day in (1, 2):
        a, _ = _run(
            control, day * DAY, early=False,
            hungry_woodcutter_work_enabled=True, retry_known_supplier_enabled=True,
        )
        b, _ = _run(
            paid, day * DAY, early=True,
            hungry_woodcutter_work_enabled=True, retry_known_supplier_enabled=True,
        )
        assert a.time == b.time == day * DAY
        _conserve(a)
        _conserve(b)
        assert audit_npc_economy(a)["copper_known_total"] == 12
        assert audit_npc_economy(b)["copper_known_total"] == 12
        _check_wage_receipts(paid, b)
        results.append({"day": day, "same_unspent_starting_bread": True,
                        "control": _stats(a), "salary": _stats(b)})
    assert sum(x["paid"] for x in results[-1]["salary"]["escrow"].values()) <= 2
    print("PLAY48S_REAL_48H_EARNED_COURIER_FOOD_COUNTERFACTUAL",
          json.dumps({"days": results,
                      "same_real_13_people_and_12_coins": True,
                      "only_difference_after_genesis":
                          "early payment of pre-existing signed wages on real services",
                      "not_an_ongoing_wage_contract": True,
                      "not_a_seven_day_recovery_proof": True},
                     sort_keys=True), flush=True)
