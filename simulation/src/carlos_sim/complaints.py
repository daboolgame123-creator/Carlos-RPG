"""02-H3: bounded local complaint desks, real intake and acknowledgement only.

A complaint is a statement received, NOT guilt, adjudication, confiscation or a fine.
Registered desk officers are explicit trusted time-zero assignments, not arbitrary roles.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .market import _id, _present
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

MAX_COMPLAINTS = 1000
DESK_KEYS = {"officer_id", "registered_at"}
COMPLAINT_KEYS = {
    "claim_id", "claimant_id", "officer_id", "desk_site_id",
    "received_at", "acknowledged_at", "acknowledged_by", "status",
}


def configure_desk(state: dict[str, Any], event: DomainEvent, *,
                   bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"site_id", "officer_id"}):
        raise ValueError("complaint desk must be explicitly configured in trusted time-zero setup")
    site, officer = p["site_id"], p["officer_id"]
    if (not _id(site) or site not in state["locations"]
            or site in state["complaint_desks"]
            or not _id(officer) or officer not in state["npcs"]
            or not _present(state, officer, site)
            or any(desk["officer_id"] == officer
                   for desk in state["complaint_desks"].values())):
        raise ValueError("desk needs a real distinct, on-site assigned officer")
    state["complaint_desks"][site] = {
        "officer_id": officer, "registered_at": state["time"],
    }


def receive_complaint(state: dict[str, Any], event: DomainEvent, *,
                      complaint_authorized: bool) -> None:
    p = event.data
    if (not complaint_authorized
            or set(p) != {"id", "claim_id", "desk_site_id"}
            or not _id(p["id"]) or p["id"] in state["property_complaints"]
            or len(state["property_complaints"]) >= MAX_COMPLAINTS
            or not _id(p["claim_id"]) or not _id(p["desk_site_id"])):
        raise ValueError("complaint intake requires trusted capability and unused record")
    site, claim_id = p["desk_site_id"], p["claim_id"]
    desk, claim = state["complaint_desks"].get(site), state["property_claims"].get(claim_id)
    claimant = event.actor_id
    if (desk is None or claim is None or claimant != claim["claimant_id"]
            or not _present(state, claimant, site)
            or not _present(state, desk["officer_id"], site)
            or claim["filed_at"] > state["time"]
            or any(rec["claim_id"] == claim_id
                   for rec in state["property_complaints"].values())):
        raise ValueError("only actual claimant and assigned present desk officer can intake claim once")
    state["property_complaints"][p["id"]] = {
        "claim_id": claim_id, "claimant_id": claimant,
        "officer_id": desk["officer_id"], "desk_site_id": site,
        "received_at": state["time"], "acknowledged_at": None,
        "acknowledged_by": None, "status": "received",
    }


def acknowledge_complaint(state: dict[str, Any], event: DomainEvent, *,
                          complaint_authorized: bool) -> None:
    p = event.data
    if (not complaint_authorized or set(p) != {"id"} or not _id(p["id"])):
        raise ValueError("acknowledgement requires trusted capability and complaint ID")
    complaint = state["property_complaints"].get(p["id"])
    if complaint is None or complaint["status"] != "received":
        raise ValueError("only an actually received and pending complaint may be acknowledged")
    site, officer = complaint["desk_site_id"], complaint["officer_id"]
    desk = state["complaint_desks"].get(site)
    if (desk is None or desk["officer_id"] != officer
            or event.actor_id != officer or not _present(state, officer, site)):
        raise ValueError("only the designated active local officer can acknowledge receipt")
    complaint["status"] = "acknowledged"
    complaint["acknowledged_at"] = state["time"]
    complaint["acknowledged_by"] = officer


def validate_complaints(state: dict[str, Any]) -> None:
    desks, records = state["complaint_desks"], state["property_complaints"]
    if not isinstance(desks, dict) or not isinstance(records, dict):
        raise ValueError("complaint ledgers must be mappings")
    officers = set()
    for site, row in desks.items():
        if (not _id(site) or site not in state["locations"]
                or not isinstance(row, dict) or set(row) != DESK_KEYS
                or not _id(row["officer_id"]) or row["officer_id"] not in state["npcs"]
                or row["officer_id"] in officers
                or row["registered_at"] != 0):
            raise ValueError("invalid recorded local complaint desk")
        officers.add(row["officer_id"])
    if len(records) > MAX_COMPLAINTS:
        raise ValueError("complaint ledger capacity exceeded")
    used_claims = set()
    for ident, row in records.items():
        if (not _id(ident) or not isinstance(row, dict) or set(row) != COMPLAINT_KEYS
                or row["desk_site_id"] not in desks
                or not _id(row["claim_id"]) or row["claim_id"] not in state["property_claims"]
                or row["claim_id"] in used_claims
                or row["officer_id"] != desks[row["desk_site_id"]]["officer_id"]
                or row["claimant_id"] != state["property_claims"][row["claim_id"]]["claimant_id"]
                or type(row["received_at"]) is not int
                or not state["property_claims"][row["claim_id"]]["filed_at"] <= row["received_at"] <= state["time"]
                or row["status"] not in {"received", "acknowledged"}):
            raise ValueError("invalid complaint ownership, locality or provenance")
        if row["status"] == "received":
            if row["acknowledged_at"] is not None or row["acknowledged_by"] is not None:
                raise ValueError("unacknowledged complaint carries forged acceptance")
        elif (type(row["acknowledged_at"]) is not int
              or not row["received_at"] <= row["acknowledged_at"] <= state["time"]
              or row["acknowledged_by"] != row["officer_id"]):
            raise ValueError("acknowledgement must be performed by actual assigned officer")
        used_claims.add(row["claim_id"])


def personal_complaints(world: WorldState, viewer_id: str) -> tuple[dict, ...]:
    """Only the complainant sees their own filing here; not a public judicial docket."""
    if viewer_id not in world.npcs:
        raise ValueError("unknown complaint viewer")
    return tuple({"id": ident, **dict(row)}
                 for ident, row in world.property_complaints.items()
                 if row["claimant_id"] == viewer_id)


@dataclass(frozen=True)
class ComplaintResult:
    event_id: str
    state: WorldState


class NPCComplaintService:
    """Trusted engine-local API, not a network authentication interface."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("complaint service requires shared store and clock")
        self.store, self.clock = store, clock

    def _append(self, world_id: str, ident: str, actor: str, kind: str,
                data: dict[str, Any], *, expected_revision: int) -> ComplaintResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if type(expected_revision) is not int or state.revision != expected_revision:
            raise RevisionConflict("stale local complaint command")
        event = DomainEvent(kind, actor, "explicit local complaint service",
                            state.time, data)
        after = self.store.append(world_id, "complaint:" + kind + ":" + str(ident),
                                  expected_revision, [event], complaint_authorized=True)
        return ComplaintResult(ident, after)

    def file(self, world_id: str, claimant_id: str, complaint_id: str,
             claim_id: str, desk_site_id: str, *,
             expected_revision: int) -> ComplaintResult:
        return self._append(world_id, complaint_id, claimant_id, "PropertyComplaintReceived",
                            {"id": complaint_id, "claim_id": claim_id,
                             "desk_site_id": desk_site_id},
                            expected_revision=expected_revision)

    def acknowledge(self, world_id: str, officer_id: str, complaint_id: str, *,
                    expected_revision: int) -> ComplaintResult:
        return self._append(world_id, complaint_id, officer_id, "PropertyComplaintAcknowledged",
                            {"id": complaint_id},
                            expected_revision=expected_revision)
