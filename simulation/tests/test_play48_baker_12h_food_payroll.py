"""PLAY48 bounded baker wage cadence: paid real stock after genuine signed work."""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent
from carlos_sim.domain import WorldState
from carlos_sim.food_for_work import choose_site_food_wage, pay_site_food_wage

HOUR = 3600


def signed_jobs(*, last_paid_hours_ago: int, worker: str, site: str):
    now = 72 * HOUR
    return {
        "old": {
            "npc_id": worker, "site_id": site, "recipe_id": "signed",
            "status": "completed", "finished_at": now - (last_paid_hours_ago + 1) * HOUR,
            "food_wage": {"paid_at": now - last_paid_hours_ago * HOUR},
        },
        "new": {
            "npc_id": worker, "site_id": site, "recipe_id": "signed",
            "status": "completed", "due": now - 60, "finished_at": now - 60,
        },
    }


def world(*, hours: int, role: str = "baker", site: str = "bakery",
          stock: int = 2, quoted: int = 0):
    worker = "basim"
    return WorldState(
        "wage-boundary", time=72 * HOUR,
        entities={worker: {"location_id": site}},
        resources={worker: {"food": 0}, site: {"food": stock}},
        production_recipes={"signed": {"role": role, "wage_food": 1}},
        production_jobs=signed_jobs(last_paid_hours_ago=hours, worker=worker, site=site),
        market_offers=({"q": {"status": "open", "stock_owner_id": site,
                              "resource": "food", "remaining": quoted}} if quoted else {}),
    )


def test_baker_11h_cooldown_remains_closed():
    state = world(hours=11)
    assert choose_site_food_wage(state, "new") is None


def test_baker_12h_real_stock_can_pay_once_and_conserves_food():
    state = world(hours=12)
    assert choose_site_food_wage(state, "new") == 1
    raw = state.to_dict()
    event = DomainEvent("ProductionFoodWagePaid", None, "signed completed work",
                        state.time, {"job_id": "new", "amount": 1})
    pay_site_food_wage(raw, event, production_authorized=True)
    assert raw["resources"]["bakery"]["food"] == 1
    assert raw["resources"]["basim"]["food"] == 1
    assert raw["production_jobs"]["new"]["food_wage"]["amount"] == 1
    with pytest.raises(ValueError):
        pay_site_food_wage(raw, event, production_authorized=True)


def test_other_roles_keep_original_36h_interval():
    state = world(hours=12, role="smith", site="smithy")
    assert choose_site_food_wage(state, "new") is None
    assert choose_site_food_wage(world(hours=36, role="smith", site="smithy"), "new") == 1


def test_baker_cannot_consume_reserved_or_absent_employer_food():
    assert choose_site_food_wage(world(hours=12, stock=0), "new") is None
    assert choose_site_food_wage(world(hours=12, stock=2, quoted=2), "new") is None


def test_unauthorized_baker_payroll_is_rejected():
    state = world(hours=12)
    event = DomainEvent("ProductionFoodWagePaid", None, "unsigned caller",
                        state.time, {"job_id": "new", "amount": 1})
    with pytest.raises(ValueError):
        pay_site_food_wage(state.to_dict(), event, production_authorized=False)
