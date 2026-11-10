"""PLAY-48M — 13 real NPCs, local fixed grain target + timber/coal jobs.

No new people, free copper, bread or supply. Layla (existing resident)
takes a genuine, finite standing-timber job. Burner buys and transports real
wood to a real charcoal production recipe, then the smith may buy charcoal
only through existing locally seen offers. Wages require completed jobs and
finite employer till balances. Bakery's 3-day inventory is a TARGET: it
starts at ZERO and must arrive from existing farms/couriers; never bootstrap
three free sacks.
"""
from __future__ import annotations
import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore
from carlos_sim.bakery_buffer import bakery_buffer_status
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import WORLD, DAY, _day, _reading
from test_play47_joined_professions import _joined_bootstrap
from test_play48h3_early_market_wage import _run
from test_play48j_affordable_payroll import _seed_affordable
import test_play38_multi_farm_couriers as east


def _joined_with_new_employment(db, *, initial_market_food, **kw):
    assert initial_market_food == 3
    assert kw == {
        "water": 2, "seed": 1, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True,
        "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3, site_payroll_enabled=True,
        site_payroll_wage_coin=2, wood_charcoal_jobs_enabled=True,
    )


def _seed_employed(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=7,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            bootstrap=_joined_with_new_employment, cash_return=True,
            waged_harvest=True, harvest_wage_copper=2,
        )
        state = db.load(WORLD)
        result = db.append(WORLD, "closure-policy", state.revision, [
            DomainEvent("WaterSourceConfigured", None, "bounded observed rain", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "same actual hunger",
                        0, {"hunger_seconds_per_point": 3600,
                            "activity_hunger_percent": 20}),
        ], bootstrap=True)
        assert db.verify(WORLD).to_dict() == result.to_dict()
        return result


def _real_stats(state):
    m = audit_npc_economy(state)
    assert m["copper_scope_complete"] and m["copper_known_total"] == 12
    site = state.resources
    work = state.production_jobs
    receipts = [
        (job["npc_id"], job["recipe_id"], job["work_wage"]["amount"])
        for job in work.values() if "work_wage" in job
    ]
    return {
        "people": len(state.npcs),
        "copper_total": m["copper_known_total"],
        "wages_paid": len(receipts),
        "woodcutter_wages": sum(who == "layla" for who, _, _ in receipts),
        "coal_worker_wages": sum(who == "burner" for who, _, _ in receipts),
        "wood_jobs": sum(j["recipe_id"] == "finite-timber-cutting"
                         and j["status"] == "completed" for j in work.values()),
        "charcoal_jobs": sum(j["recipe_id"] == "finite-wood-charcoal"
                             and j["status"] == "completed" for j in work.values()),
        "wood_sales": sum(t["resource"] == "wood"
                          for t in state.market_trades.values()),
        "charcoal_sales": sum(t["resource"] == "charcoal"
                              for t in state.market_trades.values()),
        "bread_sales": sum(t["resource"] == "food"
                           for t in state.market_trades.values()),
        "meals": len(state.consumptions),
        "hunger_100": sum(n["needs"]["hunger"] == 100
                          for n in state.npcs.values()),
        "forest_timber_left": site.get("lumberyard", {}).get("standing_timber"),
        "forest_wood_stock": site.get("lumberyard", {}).get("wood"),
        "kiln_wood_stock": site["charcoal_kiln"].get("wood"),
        "kiln_charcoal_stock": site["charcoal_kiln"]["charcoal"],
        "layla_owned_copper": site["layla"]["coin_copper"],
        "burner_owned_copper": site["burner"]["coin_copper"],
        "bakery_buffer": bakery_buffer_status(state),
    }


def test_only_real_12_copper_and_same_three_loaves_with_fixed_target(tmp_path):
    a = _seed_affordable(tmp_path / "13-original.sqlite")
    b = _seed_employed(tmp_path / "13-new-professions.sqlite")
    assert len(a.npcs) == len(b.npcs) == 13
    assert sum(s.get("coin_copper", 0) for s in a.resources.values()) == 12
    assert sum(s.get("coin_copper", 0) for s in b.resources.values()) == 12
    assert sum(s.get("food", 0) for s in a.resources.values()) == 3
    assert sum(s.get("food", 0) for s in b.resources.values()) == 3
    assert b.resources["bakery"]["grain"] == 0
    status = bakery_buffer_status(b)
    assert status == {
        "target_days": 3, "planned_grain_per_day": 1,
        "target_grain": 3, "owned_local_grain": 0,
        "missing_grain": 3, "coverage_full_days": 0,
        "needs_restock": True, "can_bake_one_batch_now": False,
        "stock_filled": False,
    }
    assert b.npcs["layla"]["role"] == "woodcutter"
    assert b.npcs["layla"]["needs"]["hunger"] == 80  # No fake hunger reset
    assert b.resources["lumberyard"]["standing_timber"] == 3
    assert b.resources["lumberyard"]["wood"] == 0
    assert b.resources["charcoal_kiln"]["charcoal"] == 0
    assert b.production_recipes["finite-timber-cutting"]["wage_coin"] == 2
    assert b.production_recipes["finite-wood-charcoal"]["wage_coin"] == 1
    assert b.routes["kiln-lumberyard"]["seconds"] == 35
    assert db_guard_not_needed(b)
    for bad in (0, -1, 8, 1.5, True):
        with pytest.raises(ValueError):
            bakery_buffer_status(b, target_days=bad)
    print("PLAY48M_FINITE_EMPLOYMENT_GENESIS", json.dumps({
        "baseline": _real_stats(a),
        "new_world": _real_stats(b),
        "new_real_npcs": 0, "new_copper": 0,
        "new_initial_bread": 0,
        "fixed_grain_target_is_not_free_grain": True,
    }, sort_keys=True), flush=True)


def db_guard_not_needed(state):
    return (state.schema_version == 43 and state.rules_version == 58)


def test_actual_twelve_hours_timbers_wages_and_material_trade(tmp_path):
    path = tmp_path / "real-13npc-work-money.sqlite"
    _seed_employed(path)
    result, _ = _run(path, DAY // 2, early=False,
                     hungry_woodcutter_work_enabled=True)
    assert result.time == DAY//2
    s = _real_stats(result)
    assert s["people"] == 13
    assert s["copper_total"] == 12
    assert s["wood_jobs"] >= 1, s
    assert s["woodcutter_wages"] >= 1, s
    assert s["forest_timber_left"] <= 2
    assert s["forest_timber_left"] + s["wood_jobs"] == 3
    assert all(v >= 0 for st in result.resources.values()
               for v in st.values() if type(v) is int)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == result.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    print("PLAY48M_TRUE_12H_WOOD_JOB_WAGE",json.dumps(s,sort_keys=True),flush=True)


def test_real_two_day_extended_professions_vs_unemployed_resident(tmp_path):
    path_a = tmp_path / "old-13.sqlite"
    path_b = tmp_path / "new-13.sqlite"
    _seed_affordable(path_a)
    _seed_employed(path_b)
    report = []
    for day in (1, 2):
        a, _ = _run(path_a, day*DAY, early=False)
        b, _ = _run(path_b, day*DAY, early=False,
                    hungry_woodcutter_work_enabled=True)
        _reading(a)
        _reading(b)
        old, new = _real_stats(a), _real_stats(b)
        assert old["people"] == new["people"] == 13
        assert old["copper_total"] == new["copper_total"] == 12
        assert new["forest_timber_left"] + new["wood_jobs"] == 3
        assert new["woodcutter_wages"] <= new["wood_jobs"]
        assert new["coal_worker_wages"] <= new["charcoal_jobs"]
        report.append({"day": day,"baseline": old, "employed": new})
    print("PLAY48M_REAL_TWO_DAY_MULTI_JOB_ECONOMY",
          json.dumps({"days":report,"automatic_wood_or_fuel_sales_claimed":False,
                      "baker_has_three_days_of_grain_claimed":False,
                      "full_13_npc_7day_recovery_claimed":False,
                      "new_cash_or_food_created":False},sort_keys=True),flush=True)
