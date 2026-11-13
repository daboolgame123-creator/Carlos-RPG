"""PLAY48 Option A: bounded, fully owned food wages for genuine on-site jobs.

These pure eligibility checks and strict reducer do not create or move remote
resources. A worksite offers ONE or TWO owned loaves as an explicitly agreed wage on
a production recipe at trusted genesis; only an actually completed local job
may redeem it, once. The existing authoritative SQLite event record persists
every physical debit and worker receipt. No cargo theft, quote diversion,
wage created from unpaid debt, or hunger/route guard bypass is permitted.

This first bounded slice covers PRODUCTION ONLY; it cannot by itself feed
unemployed guards or couriers. Courier contracts are separately governed by
courier_provisions.py. Never claim a viable village from these transactions.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent, WorldState

MAX_AMOUNT = 2**31 - 1
FOOD_WAGE_COOLDOWN_SECONDS = 36 * 3600


def _available_site_food(state: WorldState | dict[str, Any], site: str) -> int:
    """Owner's currently unpromised physical food; never includes escrow."""
    if isinstance(state, WorldState):
        food = state.resources
        offers = state.market_offers
        circuits = state.supply_circuits
    else:
        food = state["resources"]
        offers = state["market_offers"]
        circuits = state["supply_circuits"]
    balance = food.get(site, {}).get("food")
    if type(balance) is not int or not 0 <= balance <= MAX_AMOUNT:
        return -1
    quoted = sum(
        q["remaining"] for q in offers.values()
        if q["status"] == "open" and q["stock_owner_id"] == site
        and q["resource"] == "food"
    )
    from .market import reserved_trade_units
    custody = reserved_trade_units(circuits, site, "food")
    # An already EARNED farm grain-for-bread barter is a first-priority
    # physical bakery obligation. This loaf has not left the bakery yet:
    # never spend it as a baker's site-funded salary.
    promised_farm_loaf = 0
    if site == "bakery":
        from .supply import _bakery_has_pending_physical_farm_claim
        promised_farm_loaf = int(_bakery_has_pending_physical_farm_claim(state))
    return balance - quoted - custody - promised_farm_loaf


def _worker_present_and_free(state: WorldState | dict[str, Any],
                             worker: str, site: str) -> bool:
    if isinstance(state, WorldState):
        entities, actions, travels, jobs = (
            state.entities, state.actions, state.travels, state.production_jobs)
    else:
        entities, actions, travels, jobs = (
            state["entities"], state["actions"], state["travels"],
            state["production_jobs"])
    return (
        worker in entities
        and entities[worker]["location_id"] == site
        and not any(t["npc_id"] == worker and t["status"] == "traveling"
                    for t in travels.values())
        and not any(a["npc_id"] == worker and a["status"] == "running"
                    for a in actions.values())
        and not any(j["npc_id"] == worker and j["status"] == "running"
                    for j in jobs.values())
    )


def _recent_worker_receipt(jobs: Any, worker: str, now: int) -> bool:
    return any(
        job["npc_id"] == worker
        and "food_wage" in job
        and now - job["food_wage"]["paid_at"] < FOOD_WAGE_COOLDOWN_SECONDS
        for job in jobs.values()
    )


def choose_site_food_wage(state: WorldState, job_id: str) -> int | None:
    """Propose the exact signed 1- or 2-portion wage; no hidden credit."""
    job = state.production_jobs.get(job_id)
    if (job is None or job["status"] != "completed"
            or "food_wage" in job or "work_wage" in job):
        return None
    recipe = state.production_recipes.get(job["recipe_id"])
    amount = recipe.get("wage_food") if recipe is not None else None
    if type(amount) is not int or amount not in (1, 2):
        return None
    worker, site = job["npc_id"], job["site_id"]
    personal = state.resources.get(worker, {}).get("food")
    if (type(personal) is not int or not 0 <= personal <= MAX_AMOUNT - amount
            or not _worker_present_and_free(state, worker, site)
            or _recent_worker_receipt(state.production_jobs, worker, state.time)
            or _available_site_food(state, site) < amount):
        return None
    return amount


def pay_site_food_wage(state: dict[str, Any], event: DomainEvent, *,
                       production_authorized: bool) -> None:
    """Atomically debit the local employer and credit their real worker."""
    p = event.data
    if (not production_authorized or event.actor_id is not None
            or set(p) != {"job_id", "amount"}
            or type(p.get("job_id")) is not str
            or not 0 < len(p["job_id"]) <= 64
            or type(p.get("amount")) is not int or p["amount"] not in (1, 2)):
        raise ValueError("food payroll requires an authorized exact 1/2-portion job receipt")
    job = state["production_jobs"].get(p["job_id"])
    if (job is None or job["status"] != "completed"
            or "food_wage" in job or "work_wage" in job):
        raise ValueError("food may only pay an unremunerated completed job once")
    recipe = state["production_recipes"].get(job["recipe_id"])
    if (recipe is None or recipe.get("wage_food") != p["amount"]
            or "wage_coin" in recipe
            or state["time"] < job["finished_at"]):
        raise ValueError("job lacks the original explicit food-only contract")
    worker, site = job["npc_id"], job["site_id"]
    if (not _worker_present_and_free(state, worker, site)
            or _recent_worker_receipt(state["production_jobs"], worker, state["time"])
            or _available_site_food(state, site) < p["amount"]):
        raise ValueError("food wage requires real unpromised local stock and an available worker")
    employer_stock = state["resources"].get(site, {})
    worker_stock = state["resources"].get(worker, {})
    employer_before = employer_stock.get("food")
    worker_before = worker_stock.get("food")
    if (type(employer_before) is not int or employer_before < p["amount"]
            or type(worker_before) is not int
            or not 0 <= worker_before <= MAX_AMOUNT - p["amount"]):
        raise ValueError("unknown or overdrawn food wage balance")
    employer_stock["food"] = employer_before - p["amount"]
    worker_stock["food"] = worker_before + p["amount"]
    job["food_wage"] = {
        "worker_id": worker, "site_id": site, "amount": p["amount"],
        "paid_at": state["time"],
        "site_before": employer_before,
        "site_after": employer_before - p["amount"],
        "worker_before": worker_before,
        "worker_after": worker_before + p["amount"],
    }


def valid_site_food_wage_receipt(job: dict[str, Any], recipe: dict[str, Any],
                                 now: int) -> bool:
    """Canonical persisted receipt conservation validation."""
    if "food_wage" not in job:
        return True
    q = job["food_wage"]
    return (
        job["status"] == "completed"
        and recipe.get("wage_food") in (1, 2)
        and "wage_coin" not in recipe
        and type(q) is dict
        and set(q) == {
            "worker_id", "site_id", "amount", "paid_at",
            "site_before", "site_after", "worker_before", "worker_after",
        }
        and q["worker_id"] == job["npc_id"]
        and q["site_id"] == job["site_id"]
        and type(q["amount"]) is int and q["amount"] == recipe["wage_food"]
        and type(q["paid_at"]) is int
        and job["due"] <= q["paid_at"] <= now
        and all(type(q[k]) is int and 0 <= q[k] <= MAX_AMOUNT for k in (
            "site_before", "site_after", "worker_before", "worker_after"
        ))
        and q["site_before"] - q["site_after"] == q["amount"]
        and q["worker_after"] - q["worker_before"] == q["amount"]
    )
