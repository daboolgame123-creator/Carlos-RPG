"""PLAY-48J: market affordability and genuine employer payroll priority.

Do not assume bigger wages fix a village. Compare the exact thirteen-NPC
world with already-signed 1 copper jobs against alternate 2-copper jobs. Both
start with exactly the same 12 copper, real job contracts, roads and food.
A local employer pays from a FINITE cash till; the scheduled bakery→field
remittance cannot seize coins already owed for *finished* bakery work.
"""
from __future__ import annotations

import json

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.economic_autonomy import TEST_FOOD_PRICE_COPPER
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply import _bakery_cash_remittance_minimum
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY, WORLD, _day, _reading
from test_play48i_site_payroll import _seed_payroll, _audit, _site_wages
import test_play38_multi_farm_couriers as east


def _bootstrap_two_coin(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    _joined_bootstrap(
        db, initial_market_food=3, site_payroll_enabled=True,
        site_payroll_wage_coin=TEST_FOOD_PRICE_COPPER,
    )


def _seed_affordable(path):
    assert TEST_FOOD_PRICE_COPPER == 2
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=7,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            bootstrap=_bootstrap_two_coin, cash_return=True,
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


def test_bakery_profit_courier_keeps_only_cash_after_completed_wages(tmp_path):
    original = _seed_affordable(tmp_path / "true-13npc-two-coin.sqlite")
    raw = original.to_dict()
    assert raw["production_recipes"]["grain-to-bread"]["wage_coin"] == 2
    # Read-only cash selection proof. The invented diagnostic job is NEVER
    # appended to an event stream; authentic salaries remain event-only.
    circuit = dict(raw["supply_circuits"]["huda"])
    circuit["index"] = 4
    assert _bakery_cash_remittance_minimum(raw, circuit) == 2
    raw["production_jobs"]["diagnostic-completed-job"] = {
        "site_id": "bakery", "status": "completed",
        "recipe_id": "grain-to-bread",
    }
    assert _bakery_cash_remittance_minimum(raw, circuit) == 3
    # If a real paid receipt exists, the cash is already the employee's:
    # the remittance reserve is no longer needed for that job.
    raw["production_jobs"]["diagnostic-completed-job"]["work_wage"] = {
        "paid_at": 100, "worker_id": "basim", "amount": 2,
    }
    assert _bakery_cash_remittance_minimum(raw, circuit) == 2
    circuit["index"] = 3
    assert _bakery_cash_remittance_minimum(raw, circuit) == 1
    assert sum(st.get("coin_copper", 0) for st in original.resources.values()) == 12


def test_affordable_two_coin_employer_terms_do_not_invent_resources(tmp_path):
    old = _seed_payroll(tmp_path / "one-copper-original.sqlite")
    new = _seed_affordable(tmp_path / "two-copper-terms.sqlite")
    assert len(new.npcs) == len(old.npcs) == 13
    assert audit_npc_economy(new)["copper_known_total"] == 12
    assert new.resources == old.resources
    assert new.routes == old.routes
    assert new.npcs == old.npcs
    for name in ("grain-to-bread", "finite-harvest"):
        assert old.production_recipes[name]["wage_coin"] == 1
        assert new.production_recipes[name]["wage_coin"] == 2
    for site in ("farm", "bakery"):
        # Each owner initially holds ONE genuine coin, so an unaffordable
        # two-copper salary must NOT be paid until the missing coin
        # arrives as actual market revenue along the logged courier route.
        assert new.resources[site]["coin_copper"] == 1
    print("PLAY48J_AFFORDABLE_WAGE_GENESIS", json.dumps({
        "market_bread_price": TEST_FOOD_PRICE_COPPER,
        "former_work_wage": 1, "revised_work_wage": 2,
        "funds_at_each_site": 1, "initial_cash_total": 12,
        "can_pay_without_real_revenue": False,
    }, sort_keys=True))


def test_actual_13npc_two_day_affordability_against_one_copper(tmp_path):
    baseline = tmp_path / "same-coin-one-copper-wages.sqlite"
    doubled = tmp_path / "same-coin-affordable-wages.sqlite"
    _seed_payroll(baseline)
    _seed_affordable(doubled)
    report = []
    for day in (1, 2):
        a = _day(baseline, day * DAY, rain=True)
        b = _day(doubled, day * DAY, rain=True)
        row_a, row_b = _audit(a), _audit(b)
        _reading(a)
        _reading(b)
        assert row_a["cash"] == row_b["cash"] == 12
        assert all(n >= 0 for stock in b.resources.values()
                   for n in stock.values() if type(n) is int)
        report.append({"day": day, "one_coin": row_a,
                       "affordable_two_coin": row_b})
    signed = {r["work_wage"]["amount"] for r in b.production_jobs.values()
              if r["site_id"] in ("farm", "bakery") and "work_wage" in r}
    assert signed.issubset({2})  # Never silently pay an unagreed one coin.
    print("PLAY48J_ACTUAL_TWO_DAY_FUNDED_AFFORDABILITY", json.dumps({
        "days": report, "market_food_price": 2,
        "payment_from_market_returns_only": True,
        "no_cash_created": True,
        "no_food_created": True,
        "successfully_sustained_economy_claimed": False,
    }, sort_keys=True))
