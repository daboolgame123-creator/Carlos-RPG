"""PLAY-48I — real field + bakery salary, same original thirteen NPCs.

The control and treatment both own the EXACT same 12 copper coins and initial
water, tools, grain, seed, bread, streets, and 13 people. The ONLY altered
genesis is reallocating 2 EXISTING copper belonging to Carlos into the
employer-owned farm/bakery till (one each), and signing their ordinary
completed-job 1-copper wage contracts. No scripted post-genesis transfer,
forced worker decisions or magic rescue food. The production and wage
reducers remain the existing audited engine rules.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.store import InvalidEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_security_audit import audit_food_security
from test_play47_closure_endurance import _seed, _day, WORLD, DAY
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import _reading
from test_play48_13npc_post72_relay import _stats
import test_play38_multi_farm_couriers as east


def _payroll_genesis(db, *, initial_market_food, **options):
    # Identical to the original trusted combined bootstrap, except the
    # explicit existing-Carlos-copper site payroll redistribution.
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=initial_market_food, site_payroll_enabled=True,
    )


def _seed_payroll(path):
    # Reuse the unmodified original dual-field + two-courier 13-NPC genesis,
    # same grown crops, rain capacity, and identical hunger law.
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=7,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            bootstrap=_payroll_genesis, cash_return=True,
            waged_harvest=True, harvest_wage_copper=2,
        )
        state = db.load(WORLD)
        final = db.append(WORLD, "closure-policy", state.revision, [
            DomainEvent("WaterSourceConfigured", None, "bounded observed rain", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "existing policy", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        return final


def _site_wages(state):
    return {
        site: [
            (ident, job["work_wage"])
            for ident, job in state.production_jobs.items()
            if job["site_id"] == site and "work_wage" in job
        ]
        for site in ("farm", "bakery", "farm_east")
    }


def _audit(state):
    assert len(state.npcs) == 13
    assert state.schema_version == 43 and state.rules_version == 58
    money = audit_npc_economy(state)
    assert money["copper_scope_complete"] and money["copper_known_total"] == 12
    assert all(type(n) is not int or n >= 0
               for bag in state.resources.values() for n in bag.values())
    wages = _site_wages(state)
    for site, receipts in wages.items():
        for job_id, wage in receipts:
            job = state.production_jobs[job_id]
            recipe = state.production_recipes[job["recipe_id"]]
            assert recipe["wage_coin"] == wage["amount"]
            assert wage["worker_id"] == job["npc_id"]
            assert wage["site_id"] == site
            assert job["finished_at"] <= wage["paid_at"] <= state.time
            assert wage["site_before"] - wage["site_after"] == wage["amount"]
            assert wage["worker_after"] - wage["worker_before"] == wage["amount"]
    return {
        "cash": money["copper_known_total"],
        "site_wage_receipts": {site: len(v) for site, v in wages.items()},
        "market_sales": len([t for t in state.market_trades.values()
                             if t["resource"] == "food"]),
        "meals": len(state.consumptions),
        "hunger_100": sum(
            state.npcs[who]["needs"]["hunger"] == 100 for who in state.npcs
        ),
        "courier_deliveries": {
            who: state.supply_circuits[who]["deliveries"]
            for who in ("huda", "hana")
        },
        "market_till_copper": state.resources["market"]["coin_copper"],
        "farm_till_copper": state.resources["farm"]["coin_copper"],
        "bakery_till_copper": state.resources["bakery"]["coin_copper"],
    }


def test_real_prepaid_employer_payroll_preserves_exact_original_copper(tmp_path):
    baseline = _seed(tmp_path / "unchanged-same-world.sqlite")
    treatment = _seed_payroll(tmp_path / "site-funded-13npc.sqlite")
    assert len(baseline.npcs) == len(treatment.npcs) == 13
    a, b = baseline.resources, treatment.resources
    assert a["carlos"]["coin_copper"] == 2
    assert b["carlos"]["coin_copper"] == 0
    assert a["farm"]["coin_copper"] == a["bakery"]["coin_copper"] == 0
    assert b["farm"]["coin_copper"] == b["bakery"]["coin_copper"] == 1
    assert sum(stock.get("coin_copper", 0) for stock in a.values()) == 12
    assert sum(stock.get("coin_copper", 0) for stock in b.values()) == 12
    for who in ("nora", "basim"):
        assert a[who]["coin_copper"] == b[who]["coin_copper"] == 0
    for site in ("finite-harvest", "grain-to-bread"):
        assert "wage_coin" not in baseline.production_recipes[site]
        assert treatment.production_recipes[site]["wage_coin"] == 1
    # Copper and contract terms are the only intentional genesis difference.
    for owner in a:
        for resource, amount in a[owner].items():
            if resource != "coin_copper":
                assert b[owner][resource] == amount
    for key in ("routes", "locations", "entities", "npcs", "farm_plots",
                "supply_circuits", "metabolism_policy", "hydrology_sources"):
        assert getattr(baseline, key) == getattr(treatment, key)
    assert _audit(baseline)["cash"] == _audit(treatment)["cash"]
    print("PLAY48I_PAYROLL_GENESIS", json.dumps({
        "total_known_copper": 12, "player_cash_delta": -2,
        "farm_till_delta": 1, "bakery_till_delta": 1,
        "two_signed_existing_worker_contracts": True,
        "new_cash_or_food": False,
    }, sort_keys=True))


def test_fake_salary_without_actual_completed_work_cannot_drain_farm(tmp_path):
    from carlos_sim import TimeEngine
    path = tmp_path / "invalid-unearned-payroll.sqlite"
    ready = _seed_payroll(path)
    with SQLiteEventStore(path) as db:
        before = db.verify(WORLD).to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            for job_id in ("fake-grain-harvest", "fake-baking"):
                evt = DomainEvent(
                    "ProductionWagePaid", None, "forged worker wage", 0,
                    {"job_id": job_id, "amount": 1},
                )
                with pytest.raises((ValueError, InvalidEvent)):
                    db.append(WORLD, "unearned:" + job_id,
                              ready.revision, [evt], production_authorized=True)
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


def test_two_days_of_real_autonomy_pay_real_field_and_bakery_workers(tmp_path):
    control = tmp_path / "real-control.sqlite"
    paid = tmp_path / "real-payroll.sqlite"
    _seed(control)
    _seed_payroll(paid)
    history = []
    for day in (1, 2):
        c = _day(control, day * DAY, rain=True)
        p = _day(paid, day * DAY, rain=True)
        control_audit = _audit(c)
        paid_audit = _audit(p)
        history.append({"day": day, "control": control_audit,
                        "treatment": paid_audit})
        # Real resource accounting includes the ORIGINAL opening finite food,
        # real newly matured grain, physical food and reserved jobs; no free food.
        _reading(c)
        _reading(p)
    wages = _site_wages(p)
    # We require a positive *actual* finished-work wage receipt for BOTH
    # productive roles. If the workers never earn one, the experiment FAILS.
    assert len(wages["farm"]) >= 1, history
    assert len(wages["bakery"]) >= 1, history
    for site, name in (("farm", "nora"), ("bakery", "basim")):
        assert all(row["worker_id"] == name for _, row in wages[site])
    print("PLAY48I_TWO_DAY_ACTUAL_WAGES", json.dumps({
        "history": history,
        "both_workers_were_actually_paid": True,
        "new_coin_created": False,
        "new_food_created": False,
        "no_forced_npc_actions": True,
        "sustained_village_recovery_proven": False,
    }, sort_keys=True))


def test_four_day_payroll_economy_receipt_audit_not_optimistic(tmp_path):
    control = tmp_path / "four-day-control.sqlite"
    paid = tmp_path / "four-day-payroll.sqlite"
    _seed(control)
    _seed_payroll(paid)
    by_day = []
    for day in range(1, 5):
        c = _day(control, day * DAY, rain=day <= 3)
        p = _day(paid, day * DAY, rain=day <= 3)
        by_day.append({
            "day": day, "control": _audit(c), "paid": _audit(p),
            "control_economy": _stats(c),
            "paid_economy": _stats(p),
        })
        _reading(c)
        _reading(p)
    # Crucial: never assert recovery or invent bread to make the test green.
    assert c.time == p.time == 4 * DAY
    assert p.resources["market"]["food"] >= 0
    print("PLAY48I_GENUINE_96H_PAYROLL_COUNTERFACTUAL", json.dumps({
        "days": by_day,
        "new_coin_created": False,
        "new_food_created": False,
        "operator_forced_wages": False,
        "permanent_recovery_claimed": False,
    }, sort_keys=True))
