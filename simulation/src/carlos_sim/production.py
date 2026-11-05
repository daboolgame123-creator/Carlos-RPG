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


def configure_recipe(state: dict[str, Any], event: DomainEvent, *,
                     bootstrap: bool) -> None:
    p = event.data
    required = {"id", "site_id", "role", "input_resource", "input_amount",
                "output_resource", "output_amount", "tool_resource", "duration_seconds"}
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != required):
        raise ValueError("production recipes require trusted time-zero bootstrap")
    ident, site = p["id"], p["site_id"]
    if (not _valid_name(ident, MAX_ID) or ident in state["production_recipes"]
            or not isinstance(site, str) or site not in state["locations"]
            or not _valid_name(p["role"], MAX_NAME)
            or not all(_valid_name(p[k], MAX_NAME) for k in (
                "input_resource", "output_resource", "tool_resource"))
            or len({p["input_resource"], p["output_resource"],
                    p["tool_resource"]}) != 3
            or not _amount(p["input_amount"])
            or not _amount(p["output_amount"])
            or not _seconds(p["duration_seconds"])):
        raise ValueError("invalid recipe fields or site")
    resources = state["resources"].get(site, {})
    if not all(_known(resources.get(p[k])) for k in (
            "input_resource", "output_resource", "tool_resource")):
        raise ValueError("recipe requires initialized local materials, output and tools")
    # Recipe is a fixed, auditable configuration, not an executable callback.
    state["production_recipes"][ident] = dict(p)


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
    input_before = stocks.get(recipe["input_resource"])
    output_before = stocks.get(recipe["output_resource"])
    tool_qty = stocks.get(recipe["tool_resource"])
    if (not all(_known(v) for v in (input_before, output_before, tool_qty))
            or input_before < recipe["input_amount"]
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
    stocks[recipe["input_resource"]] = input_before - recipe["input_amount"]
    state["production_jobs"][p["id"]] = {
        "npc_id": who, "recipe_id": recipe_id, "site_id": site,
        "started_at": state["time"], "due": due, "status": "running",
        "finished_at": None, "input_before": input_before,
        "input_after": input_before - recipe["input_amount"],
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


def validate_production_state(state: dict[str, Any]) -> None:
    recipes, jobs = state["production_recipes"], state["production_jobs"]
    if not isinstance(recipes, dict) or not isinstance(jobs, dict):
        raise ValueError("production state collections must be mappings")
    for ident, rec in recipes.items():
        if (not _valid_name(ident, MAX_ID) or not isinstance(rec, dict)
                or set(rec) != {"id", "site_id", "role", "input_resource",
                               "input_amount", "output_resource", "output_amount",
                               "tool_resource", "duration_seconds"}
                or rec["id"] != ident
                or rec["site_id"] not in state["locations"]
                or not _valid_name(rec["role"], MAX_NAME)
                or not all(_valid_name(rec[k], MAX_NAME) for k in (
                    "input_resource", "output_resource", "tool_resource"))
                or len({rec["input_resource"], rec["output_resource"],
                        rec["tool_resource"]}) != 3
                or not _amount(rec["input_amount"])
                or not _amount(rec["output_amount"])
                or not _seconds(rec["duration_seconds"])):
            raise ValueError("invalid persisted recipe")
    busy: set[str] = set()
    reservation_count: dict[tuple[str, str], int] = {}
    for ident, job in jobs.items():
        if (not _valid_name(ident, MAX_ID) or not isinstance(job, dict)
                or set(job) != {"npc_id", "recipe_id", "site_id", "started_at",
                                "due", "status", "finished_at", "input_before",
                                "input_after", "tool_seen", "output_before",
                                "output_after"}):
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
