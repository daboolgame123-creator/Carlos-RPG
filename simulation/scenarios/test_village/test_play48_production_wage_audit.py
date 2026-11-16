"""Read-only accounting: unpaid contracts are not unpaid voluntary work."""
from types import SimpleNamespace

from carlos_sim.economic_diagnostics import audit_production_wages
from test_play48_deferred_bakery_grain_wages_ab import seed


def test_classifies_only_completed_signed_jobs_and_keeps_receipts_separate():
    recipes = {"cash": {"wage_coin": 2}, "food": {"wage_food": 1},
               "unpaid": {}}

    def job(recipe, status="completed", **receipt):
        return {"recipe_id": recipe, "status": status,
                "npc_id": "worker", "site_id": "worksite", **receipt}

    state = SimpleNamespace(production_recipes=recipes, production_jobs={
        "a": job("cash", work_wage={}), "b": job("cash"),
        "c": job("food", food_wage={}), "d": job("food"),
        "e": job("unpaid"), "f": job("cash", status="running"),
    })
    assert audit_production_wages(state) == {
        "coin_paid": 1, "coin_unpaid": 1, "food_paid": 1,
        "food_unpaid": 1, "without_contract": 1,
        "unpaid_jobs": [
            {"job_id": "b", "worker_id": "worker", "site_id": "worksite",
             "resource": "coin", "amount": 2},
            {"job_id": "d", "worker_id": "worker", "site_id": "worksite",
             "resource": "food", "amount": 1},
        ],
    }


def test_original_village_contracts_do_not_invent_cash_wages(tmp_path):
    state = seed(tmp_path / "original.sqlite", deferred=True)
    recipes = state.production_recipes
    assert len(state.npcs) == 13
    assert sum(bag.get("coin_copper", 0) or 0
               for bag in state.resources.values()) == 12
    assert "wage_coin" not in recipes["finite-harvest"]
    assert recipes["grain-to-bread"]["wage_food"] == 1
    assert recipes["east-finite-harvest"]["wage_coin"] == 2
    assert audit_production_wages(state)["unpaid_jobs"] == []
