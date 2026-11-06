"""03-A6 deterministic, resource-funded NPC recovery event projections.

Every state change comes from an authorized persisted domain event.
There is no passive healing and no arbitrary treatment efficacy.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent
from .injury_transitions import _ident, _time, compute_recovery_transition
from .market import _present

DURATION = 600
IMPROVEMENT = 10
FOOD_COST = 1
RESOURCE = "food"

_START_FIELDS = frozenset({
    "id", "injury_id", "subject_id", "caregiver_id", "site_id",
    "schedule_id", "started_at", "due_at", "resource", "quantity", "improvement",
})
_RECORD_FIELDS = _START_FIELDS | {"status"}


def validate_treatment_state(state: dict[str, Any]) -> None:
    if type(state["treatments"]) is not dict:
        raise ValueError("invalid treatments ledger")
    for ident, rec in state["treatments"].items():
        if type(rec) is not dict or set(rec) != _RECORD_FIELDS:
            raise ValueError("invalid persisted treatment shape")
        if ident != rec["id"] or not all(_ident(rec[key]) for key in (
            "id", "injury_id", "subject_id", "caregiver_id", "site_id", "schedule_id",
        )):
            raise ValueError("invalid treatment identity")
        if rec["subject_id"] not in state["npcs"] or rec["caregiver_id"] not in state["npcs"]:
            raise ValueError("treatment references non-NPC")
        if rec["site_id"] not in state["locations"] or rec["injury_id"] not in state["injuries"]:
            raise ValueError("treatment reference missing")
        if rec["subject_id"] != state["injuries"][rec["injury_id"]]["subject_id"]:
            raise ValueError("treatment subject mismatch")
        if (rec["resource"] != RESOURCE or rec["quantity"] != FOOD_COST
                or rec["improvement"] != IMPROVEMENT
                or type(rec["resource"]) is not str
                or type(rec["quantity"]) is not int
                or type(rec["improvement"]) is not int):
            raise ValueError("unfunded/unsupported treatment contract")
        if (not _time(rec["started_at"]) or not _time(rec["due_at"])
                or rec["due_at"] - rec["started_at"] != DURATION):
            raise ValueError("invalid treatment interval")
        if type(rec["status"]) is not str or rec["status"] not in (
            "pending", "completed", "interrupted",
        ):
            raise ValueError("invalid treatment status")
        if rec["started_at"] > state["time"]:
            raise ValueError("future treatment start")
        if rec["status"] == "pending" and rec["due_at"] < state["time"]:
            raise ValueError("overdue unresolved treatment")
        if rec["status"] != "pending" and rec["due_at"] > state["time"]:
            raise ValueError("future treatment completion")


def begin_recovery(state: dict[str, Any], event: DomainEvent, *,
                   recovery_authorized: bool) -> None:
    p = event.data
    if not recovery_authorized or set(p) != _START_FIELDS:
        raise ValueError("treatment requires separate trusted recovery capability")
    if (not all(_ident(p[key]) for key in (
            "id", "injury_id", "subject_id", "caregiver_id", "site_id", "schedule_id"))
            or event.actor_id != p["caregiver_id"]
            or p["id"] in state["treatments"] or p["schedule_id"] in state["scheduled"]
            or p["injury_id"] not in state["injuries"]
            or p["subject_id"] not in state["npcs"]
            or p["caregiver_id"] not in state["npcs"]
            or p["site_id"] not in state["locations"]):
        raise ValueError("invalid treatment identity, actor or location")
    if (type(p["started_at"]) is not int or p["started_at"] != state["time"]
            or not _time(p["due_at"]) or p["due_at"] - p["started_at"] != DURATION
            or type(p["resource"]) is not str or p["resource"] != RESOURCE
            or type(p["quantity"]) is not int or p["quantity"] != FOOD_COST
            or type(p["improvement"]) is not int or p["improvement"] != IMPROVEMENT):
        raise ValueError("invalid recovery duration, material or efficacy")
    injured = state["injuries"][p["injury_id"]]
    if (injured["subject_id"] != p["subject_id"] or injured["status"] != "active"
            or any(t["status"] == "pending" and t["injury_id"] == p["injury_id"]
                   for t in state["treatments"].values())):
        raise ValueError("injury is not available for new treatment")
    if (not _present(state, p["subject_id"], p["site_id"])
            or not _present(state, p["caregiver_id"], p["site_id"])):
        raise ValueError("treatment requires two available colocated NPCs")
    food = state["resources"].get(p["caregiver_id"], {}).get(RESOURCE)
    if type(food) is not int or food < FOOD_COST:
        raise ValueError("caregiver lacks material to perform treatment")
    state["resources"][p["caregiver_id"]][RESOURCE] = food - FOOD_COST
    state["treatments"][p["id"]] = {**p, "status": "pending"}


def validate_recovery_schedule(state: dict[str, Any], p: dict[str, Any],
                               *, recovery_authorized: bool) -> None:
    if not recovery_authorized or set(p["payload"]) != {"__npc_recovery"} or p["interrupt"]:
        raise ValueError("recovery schedule requires trusted appointment creation")
    tid = p["payload"]["__npc_recovery"]
    if type(tid) is not str or tid not in state["treatments"]:
        raise ValueError("recovery schedule references unknown treatment")
    t = state["treatments"][tid]
    if (t["status"] != "pending" or t["schedule_id"] != p["id"]
            or t["due_at"] != p["due"]):
        raise ValueError("recovery schedule does not match paid treatment")


def finish_recovery(state: dict[str, Any], schedule_id: str, payload: dict[str, Any],
                    at_time: int) -> None:
    if set(payload) != {"__npc_recovery"}:
        raise ValueError("invalid recovery completion payload")
    tid = payload["__npc_recovery"]
    if type(tid) is not str or tid not in state["treatments"]:
        raise ValueError("recovery event references unknown treatment")
    t = state["treatments"][tid]
    if (t["status"] != "pending" or schedule_id != t["schedule_id"]
            or at_time != t["due_at"]):
        raise ValueError("recovery is not due or already consumed")
    if (_present(state, t["subject_id"], t["site_id"])
            and _present(state, t["caregiver_id"], t["site_id"])):
        new_injury = compute_recovery_transition(
            state["injuries"][t["injury_id"]],
            started_at=t["started_at"], due_at=t["due_at"],
            at_time=at_time, improvement=t["improvement"])
        state["injuries"][t["injury_id"]] = new_injury
        t["status"] = "completed"
    else:
        # Committed food was used/reserved at start, so no unexplained refund.
        t["status"] = "interrupted"
