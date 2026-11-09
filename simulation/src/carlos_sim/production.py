"""Phase 02-B: opt-in, finite and traceable local NPC production.

A recipe converts *known, site-owned* materials into finished site-owned
goods after a scheduled in-world duration. The stationary tool is checked but
not consumed. Only a trusted production capability can start a job; the
trusted clock is responsible for finishing it. No market, wage or NPC
production planner is implied. All figures are disposable test-world inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

MAX_QUANTITY = 2**31 - 1
MAX_BATCH = 1000
MAX_DURATION = 86_400
MAX_ID = 64
MAX_NAME = 40


def _valid_name(item: Any, limit: int) -> bool:
    return (isinstance(item, str) and 0 < len(item) <= limit
            and item.isascii()
            and all(c.isalnum() or c in "._-" for c in item))


def _known(item: Any) -> bool:
    return type(item) is int and 0 <= item <= MAX_QUANTITY


def _amount(item: Any) -> bool:
    return type(item) is int and 0 < item <= MAX_BATCH


def _seconds(item: Any) -> bool:
    return type(item) is int and 0 < item <= MAX_DURATION


def _sid(job_id: str) -> str:
    return "production:" + job_id


def is_producing(state: dict[str, Any], npc_id: str) -> bool:
    """Known job reservation, not an inferred profession or hidden intent."""
    return any(job["npc_id"] == npc_id and job["status"] == "running"
               for job in state["production_jobs"].values())



# v42/57: old scalar receipts remain unchanged; compound jobs have per-input
# receipts. Currency and nontradeable pseudo-resources cannot become fuel.
_COMPOUND_DENIED = {"coin_copper", "labor_units", "investigation_attempts",
                    "regrowth_reserve", "wild_food"}
_RECIPE_BASE = {"id", "site_id", "role", "output_resource", "output_amount",
                "tool_resource", "duration_seconds"}
_RECIPE_LEGACY = _RECIPE_BASE | {"input_resource", "input_amount"}
_RECIPE_COMPOUND = _RECIPE_BASE | {"inputs"}
_JOB_BASE = {"npc_id", "recipe_id", "site_id", "started_at", "due", "status",
             "finished_at", "tool_seen", "output_before", "output_after"}
_JOB_LEGACY = _JOB_BASE | {"input_before", "input_after"}
_JOB_COMPOUND = _JOB_BASE | {"input_before_by_resource",
                             "input_after_by_resource"}


def recipe_inputs(recipe: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    """Validated normalized view of a legacy or compound recipe."""
    if "inputs" in recipe:
        return tuple((part["resource"], part["amount"])
                     for part in recipe["inputs"])
    return ((recipe["input_resource"], recipe["input_amount"]),)


def recipe_shape_ok(recipe: Any, locations: dict[str, Any],
                    resources: dict[str, Any]) -> bool:
    if not isinstance(recipe, dict):
        return False
    compound = "inputs" in recipe
    expected = _RECIPE_COMPOUND if compound else _RECIPE_LEGACY
    if set(recipe) not in (expected, expected | {"wage_coin"}):
        return False
    if (not _valid_name(recipe["id"], MAX_ID)
            or not isinstance(recipe["site_id"], str)
            or recipe["site_id"] not in locations
            or not _valid_name(recipe["role"], MAX_NAME)
            or not _valid_name(recipe["output_resource"], MAX_NAME)
            or not _valid_name(recipe["tool_resource"], MAX_NAME)
            or recipe["output_resource"] == recipe["tool_resource"]
            or not _amount(recipe["output_amount"])
            or not _seconds(recipe["duration_seconds"])):
        return False
    if compound:
        parts = recipe["inputs"]
        if type(parts) is not list or not 2 <= len(parts) <= 4:
            return False
        if any(type(part) is not dict or set(part) != {"resource", "amount"}
               or not _valid_name(part["resource"], MAX_NAME)
               or part["resource"] in _COMPOUND_DENIED
               or not _amount(part["amount"]) for part in parts):
            return False
        names = [part["resource"] for part in parts]
        if len(set(names)) != len(names):
            return False
    else:
        if (not _valid_name(recipe["input_resource"], MAX_NAME)
                or not _amount(recipe["input_amount"])):
            return False
        names = [recipe["input_resource"]]
    if any(name in (recipe["output_resource"], recipe["tool_resource"])
           for name in names):
        return False
    stocks = resources.get(recipe["site_id"], {})
    if not all(_known(stocks.get(name)) for name in
               (*names, recipe["output_resource"], recipe["tool_resource"])):
        return False
    if "wage_coin" in recipe and (
            type(recipe["wage_coin"]) is not int
            or not 1 <= recipe["wage_coin"] <= 5
            or not _known(stocks.get("coin_copper"))):
        return False
    return True

def configure_recipe(state: dict[str, Any], event: DomainEvent, *,
                     bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or not recipe_shape_ok(p, state["locations"], state["resources"])
            or p["id"] in state["production_recipes"]):
        raise ValueError("recipe requires finite, initialized time-zero materials")
    state["production_recipes"][p["id"]] = dict(p)

def start_production(state: dict[str, Any], event: DomainEvent, *,
                     production_authorized: bool) -> None:
    p = event.data
    if (not production_authorized or set(p) != {"id", "recipe_id", "npc_id"}
            or not _valid_name(p["id"], MAX_ID)
            or p["id"] in state["production_jobs"]):
        raise ValueError("production start requires trusted capability and fresh ID")
    who, recipe_id = p["npc_id"], p["recipe_id"]
    recipe = state["production_recipes"].get(recipe_id) if isinstance(recipe_id, str) else None
    if (recipe is None or not isinstance(who, str) or who not in state["npcs"]
            or event.actor_id != who
            or state["npcs"][who]["role"] != recipe["role"]):
        raise ValueError("production requires its real trained NPC worker")
    site = recipe["site_id"]
    if state["entities"][who]["location_id"] != site:
        raise ValueError("worker must be physically at the workshop")
    if (is_producing(state, who)
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state["actions"].values())
            or any(t["npc_id"] == who and t["status"] == "traveling"
                   for t in state["travels"].values())):
        raise ValueError("worker cannot work twice or produce while traveling")
    stocks = state["resources"].get(site, {})
    needs = recipe_inputs(recipe)
    before_by = {item: stocks.get(item) for item, _ in needs}
    output_before = stocks.get(recipe["output_resource"])
    tool_qty = stocks.get(recipe["tool_resource"])
    if (not all(_known(v) for v in
                (*before_by.values(), output_before, tool_qty))
            or any(before_by[item] < amount for item, amount in needs)
            or tool_qty < 1
            or output_before + recipe["output_amount"] > MAX_QUANTITY):
        raise ValueError("insufficient or unknown local production inputs/tool/output")
    # Number of simultaneous jobs sharing this *physical* tool kind at this
    # worksite cannot exceed the number of initialized tools.
    occupying = sum(
        1 for j in state["production_jobs"].values()
        if j["status"] == "running" and j["site_id"] == site
        and state["production_recipes"][j["recipe_id"]]["tool_resource"]
        == recipe["tool_resource"]
    )
    if occupying >= tool_qty:
        raise ValueError("worksite tool already reserved")
    due = state["time"] + recipe["duration_seconds"]
    if due > 2**63 - 1 or _sid(p["id"]) in state["scheduled"]:
        raise ValueError("invalid or duplicate production appointment")
    # Validate every requirement BEFORE touching any resource balance.
    for item, amount in needs:
        stocks[item] = before_by[item] - amount
    receipt = (
        {"input_before_by_resource": dict(before_by),
         "input_after_by_resource": {
             item: before_by[item] - amount for item, amount in needs
         }} if "inputs" in recipe else
        {"input_before": before_by[needs[0][0]],
         "input_after": before_by[needs[0][0]] - needs[0][1]}
    )
    state["production_jobs"][p["id"]] = {
        "npc_id": who, "recipe_id": recipe_id, "site_id": site,
        "started_at": state["time"], "due": due, "status": "running",
        "finished_at": None, **receipt,
        "tool_seen": tool_qty, "output_before": None, "output_after": None,
    }
    state["scheduled"][_sid(p["id"])] = {
        "due": due, "order": state["next_schedule_order"],
        "kind": "signal", "payload": {"__production_job": p["id"]},
        "interrupt": False,
    }
    state["next_schedule_order"] += 1


def finish_production(state: dict[str, Any], schedule_id: str,
                      job_id: Any, now: int) -> None:
    job = state["production_jobs"].get(job_id) if isinstance(job_id, str) else None
    if (job is None or job["status"] != "running"
            or schedule_id != _sid(job_id) or job["due"] != now
            or state["entities"][job["npc_id"]]["location_id"] != job["site_id"]):
        raise ValueError("production completion requires its exact due scheduled job")
    recipe = state["production_recipes"][job["recipe_id"]]
    site_stock = state["resources"][job["site_id"]]
    output_before = site_stock.get(recipe["output_resource"])
    if (not _known(output_before)
            or output_before + recipe["output_amount"] > MAX_QUANTITY):
        raise ValueError("completed product must have known, bounded site output")
    output_after = output_before + recipe["output_amount"]
    site_stock[recipe["output_resource"]] = output_after
    job["status"] = "completed"
    job["finished_at"] = now
    job["output_before"] = output_before
    job["output_after"] = output_after


def choose_local_production_wage(state: WorldState, job_id: str) -> int | None:
    """Propose a *funded* payment for one finished, on-site job.

    An unpaid job can remain unpaid indefinitely if its employer has no
    money or the worker leaves. The planner may never mint its wages.
    """
    job = state.production_jobs.get(job_id)
    if job is None or job["status"] != "completed" or "work_wage" in job:
        return None
    recipe = state.production_recipes.get(job["recipe_id"])
    if recipe is None or "wage_coin" not in recipe:
        return None
    who, site, wage = job["npc_id"], job["site_id"], recipe["wage_coin"]
    if (state.entities[who]["location_id"] != site
            or any(t["npc_id"] == who and t["status"] == "traveling"
                   for t in state.travels.values())
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state.actions.values())
            or any(j["npc_id"] == who and j["status"] == "running"
                   for j in state.production_jobs.values())):
        return None
    payer = state.resources.get(site, {}).get("coin_copper")
    receiver = state.resources.get(who, {}).get("coin_copper")
    if (not _known(payer) or not _known(receiver)
            or payer < wage or receiver + wage > MAX_QUANTITY):
        return None
    return wage


def pay_completed_production_wage(state: dict[str, Any], event: DomainEvent, *,
                                  production_authorized: bool) -> None:
    p = event.data
    if (not production_authorized or event.actor_id is not None
            or set(p) != {"job_id", "amount"}
            or not _valid_name(p["job_id"], MAX_ID)
            or type(p["amount"]) is not int):
        raise ValueError("wage payout requires a trusted, unimpersonated production receipt")
    job = state["production_jobs"].get(p["job_id"])
    if (job is None or job["status"] != "completed"
            or "work_wage" in job):
        raise ValueError("wage can be paid exactly once for a completed job")
    recipe = state["production_recipes"][job["recipe_id"]]
    wage = recipe.get("wage_coin")
    who, site = job["npc_id"], job["site_id"]
    if (type(wage) is not int or wage != p["amount"]
            or state["time"] < job["finished_at"]
            or state["entities"][who]["location_id"] != site
            or any(t["npc_id"] == who and t["status"] == "traveling"
                   for t in state["travels"].values())
            or any(a["npc_id"] == who and a["status"] == "running"
                   for a in state["actions"].values())
            or is_producing(state, who)):
        raise ValueError("wage requires agreed terms and an available on-site worker")
    payer = state["resources"].get(site, {}).get("coin_copper")
    receiver = state["resources"].get(who, {}).get("coin_copper")
    if (not _known(payer) or not _known(receiver)
            or payer < wage or receiver + wage > MAX_QUANTITY):
        raise ValueError("wage requires initialized, sufficiently funded local balances")
    state["resources"][site]["coin_copper"] = payer - wage
    state["resources"][who]["coin_copper"] = receiver + wage
    job["work_wage"] = {
        "worker_id": who, "site_id": site, "amount": wage,
        "paid_at": state["time"],
        "site_before": payer, "site_after": payer - wage,
        "worker_before": receiver, "worker_after": receiver + wage,
    }


def validate_production_state(state: dict[str, Any]) -> None:
    recipes, jobs = state["production_recipes"], state["production_jobs"]
    if not isinstance(recipes, dict) or not isinstance(jobs, dict):
        raise ValueError("production state collections must be mappings")
    for ident, rec in recipes.items():
        if (not _valid_name(ident, MAX_ID) or not isinstance(rec, dict)
                or set(rec) not in (
                    {"id", "site_id", "role", "input_resource",
                     "input_amount", "output_resource", "output_amount",
                     "tool_resource", "duration_seconds"},
                    {"id", "site_id", "role", "input_resource",
                     "input_amount", "output_resource", "output_amount",
                     "tool_resource", "duration_seconds", "wage_coin"})
                or rec["id"] != ident
                or rec["site_id"] not in state["locations"]
                or not _valid_name(rec["role"], MAX_NAME)
                or not all(_valid_name(rec[k], MAX_NAME) for k in (
                    "input_resource", "output_resource", "tool_resource"))
                or len({rec["input_resource"], rec["output_resource"],
                        rec["tool_resource"]}) != 3
                or not _amount(rec["input_amount"])
                or not _amount(rec["output_amount"])
                or not _seconds(rec["duration_seconds"])
                or ("wage_coin" in rec and (
                    type(rec["wage_coin"]) is not int
                    or not 1 <= rec["wage_coin"] <= 5
                    or not _known(state["resources"].get(rec["site_id"], {}).get("coin_copper"))))):
            raise ValueError("invalid persisted recipe")
    busy: set[str] = set()
    reservation_count: dict[tuple[str, str], int] = {}
    for ident, job in jobs.items():
        if (not _valid_name(ident, MAX_ID) or not isinstance(job, dict)
                or set(job) not in (
                    {"npc_id", "recipe_id", "site_id", "started_at",
                     "due", "status", "finished_at", "input_before",
                     "input_after", "tool_seen", "output_before", "output_after"},
                    {"npc_id", "recipe_id", "site_id", "started_at",
                     "due", "status", "finished_at", "input_before",
                     "input_after", "tool_seen", "output_before", "output_after",
                     "work_wage"})):
            raise ValueError("invalid persisted production job")
        recipe = recipes.get(job["recipe_id"]) if isinstance(job["recipe_id"], str) else None
        who = job["npc_id"]
        if (recipe is None or who not in state["npcs"]
                or state["npcs"][who]["role"] != recipe["role"]
                or job["site_id"] != recipe["site_id"]
                or type(job["started_at"]) is not int or job["started_at"] < 0
                or type(job["due"]) is not int
                or job["due"] != job["started_at"] + recipe["duration_seconds"]
                or not _known(job["input_before"])
                or not _known(job["input_after"])
                or job["input_before"] < recipe["input_amount"]
                or job["input_after"] != job["input_before"] - recipe["input_amount"]
                or not _known(job["tool_seen"]) or job["tool_seen"] < 1
                or job["status"] not in ("running", "completed")):
            raise ValueError("invalid production materials or duration/profession")
        if "work_wage" in job:
            receipt = job["work_wage"]
            if (job["status"] != "completed"
                    or "wage_coin" not in recipe
                    or type(receipt) is not dict
                    or set(receipt) != {
                        "worker_id", "site_id", "amount", "paid_at",
                        "site_before", "site_after",
                        "worker_before", "worker_after",
                    }
                    or receipt["worker_id"] != who
                    or receipt["site_id"] != job["site_id"]
                    or type(receipt["amount"]) is not int
                    or receipt["amount"] != recipe["wage_coin"]
                    or type(receipt["paid_at"]) is not int
                    or not job["due"] <= receipt["paid_at"] <= state["time"]
                    or any(not _known(receipt[k]) for k in (
                        "site_before", "site_after", "worker_before", "worker_after"))
                    or receipt["site_before"] - receipt["site_after"]
                       != receipt["amount"]
                    or receipt["worker_after"] - receipt["worker_before"]
                       != receipt["amount"]):
                raise ValueError("job wage receipt must conserve an actual completed wage")
        if job["status"] == "running":
            if (who in busy or state["time"] > job["due"]
                    or job["started_at"] > state["time"]
                    or job["finished_at"] is not None
                    or job["output_before"] is not None
                    or job["output_after"] is not None
                    or state["entities"][who]["location_id"] != job["site_id"]
                    or any(a["npc_id"] == who and a["status"] == "running"
                           for a in state["actions"].values())
                    or any(t["npc_id"] == who and t["status"] == "traveling"
                           for t in state["travels"].values())):
                raise ValueError("production worker busy elsewhere or job overdue")
            busy.add(who)
            sid = _sid(ident)
            scheduled = state["scheduled"].get(sid)
            if (scheduled is None or scheduled["due"] != job["due"]
                    or scheduled["kind"] != "signal" or scheduled["interrupt"]
                    or scheduled["payload"] != {"__production_job": ident}):
                raise ValueError("running production must have its exact completion signal")
            k = (job["site_id"], recipe["tool_resource"])
            reservation_count[k] = reservation_count.get(k, 0) + 1
        else:
            if (job["finished_at"] != job["due"]
                    or type(job["finished_at"]) is not int
                    or job["finished_at"] > state["time"]
                    or not _known(job["output_before"])
                    or not _known(job["output_after"])
                    or job["output_after"] !=
                    job["output_before"] + recipe["output_amount"]
                    or _sid(ident) in state["scheduled"]):
                raise ValueError("invalid completed product provenance")
    for (site, tool), count in reservation_count.items():
        available = state["resources"].get(site, {}).get(tool)
        if not _known(available) or count > available:
            raise ValueError("overbooked production tools")
    for ident, item in state["scheduled"].items():
        if "__production_job" in item["payload"]:
            job_id = item["payload"]["__production_job"]
            if (not isinstance(job_id, str) or ident != _sid(job_id)
                    or job_id not in jobs or jobs[job_id]["status"] != "running"):
                raise ValueError("forged or orphaned production appointment")


@dataclass(frozen=True)
class ProductionStart:
    job_id: str
    worker_id: str
    site_id: str
    due: int
    state: WorldState


class NPCProductionService:
    """Explicit trusted coordinator; does NOT autonomously choose a product."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("production, clock and SQLite store must match")
        self.store = store
        self.clock = clock

    def start(self, world_id: str, npc_id: str, recipe_id: str, job_id: str,
              *, expected_revision: int) -> ProductionStart:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if type(expected_revision) is not int or expected_revision != state.revision:
            raise RevisionConflict("stale production start revision")
        if not _valid_name(job_id, MAX_ID):
            raise ValueError("invalid production job identifier")
        # The reducer validates profession, site, materials, tools and schedules.
        evt = DomainEvent("ProductionStarted", npc_id, "trusted NPC local production",
                          state.time, {"id": job_id, "recipe_id": recipe_id,
                                       "npc_id": npc_id})
        result = self.store.append(world_id, "production-start:" + job_id,
                                   expected_revision, [evt],
                                   production_authorized=True)
        job = result.production_jobs[job_id]
        return ProductionStart(job_id, npc_id, job["site_id"], job["due"], result)
