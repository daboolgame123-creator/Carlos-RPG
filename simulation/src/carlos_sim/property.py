"""Phase 02-H1: physically conserved non-consensual taking, not adjudicated theft.

Local trusted test-session capability only. No witness, guilt, title or penalty.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .market import _id, _balance, _present, MAX_AMOUNT, MAX_QUANTITY, MONEY, FORBIDDEN
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

TAKING_KEYS = {
    "actor_id", "source_owner_id", "site_id", "resource", "quantity",
    "taken_at", "source_before", "source_after", "target_before",
    "target_after", "permission_basis",
}


def project_taking(state: dict[str, Any], event: DomainEvent, *,
                   taking_authorized: bool) -> None:
    p = event.data
    if (not taking_authorized or set(p) not in ({
            "id", "source_owner_id", "site_id", "resource", "quantity"}, {
            "id", "source_owner_id", "site_id", "resource", "quantity", "witness_ids"})
            or not _id(p["id"]) or p["id"] in state["property_takings"]):
        raise ValueError("taking requires an independent trusted capability and unique ID")
    actor, source, site, resource = (
        event.actor_id, p["source_owner_id"], p["site_id"], p["resource"])
    quantity = p["quantity"]
    if (not _id(actor) or actor not in state["npcs"]
            or not _id(source) or source == actor
            or not _id(site) or site not in state["locations"]
            or not _id(resource) or resource == MONEY or resource in FORBIDDEN
            or type(quantity) is not int or not 1 <= quantity <= MAX_QUANTITY
            or not _present(state, actor, site)):
        raise ValueError("invalid taking actor, location, item or amount")
    if source == site:
        # Without a registered steward the site's effective custodian is
        # unknown, so claiming it unowned would be a false legal inference.
        stall = state["market_stalls"].get(site)
        if stall is None or stall["keeper_id"] == actor:
            raise ValueError("site stock must have an independent recorded steward")
    elif source not in state["npcs"] or not _present(state, source, site):
        raise ValueError("personal stock can only be taken from a co-located person")
    # Production equipment may be in use or required by an outstanding job.
    # Until tool reservations and interruption rules exist, do not take it.
    if source == site and any(recipe["site_id"] == site and
                              recipe["tool_resource"] == resource
                              for recipe in state["production_recipes"].values()):
        raise ValueError("production equipment is not available for taking")
    source_before = state["resources"].get(source, {}).get(resource)
    target_before = state["resources"].get(actor, {}).get(resource)
    if (not _balance(source_before) or not _balance(target_before)
            or source_before < quantity or target_before + quantity > MAX_AMOUNT):
        raise ValueError("taking requires known, sufficient and bounded inventories")
    from .property_evidence import validate_initial_witnesses
    witnesses = validate_initial_witnesses(state, actor, site, p.get("witness_ids", []))
    state["resources"][source][resource] = source_before - quantity
    state["resources"][actor][resource] = target_before + quantity
    state["property_takings"][p["id"]] = {
        "actor_id": actor, "source_owner_id": source, "site_id": site,
        "resource": resource, "quantity": quantity, "taken_at": state["time"],
        "source_before": source_before, "source_after": source_before - quantity,
        "target_before": target_before, "target_after": target_before + quantity,
        "permission_basis": "no_grant_recorded",
    }
    for witness in witnesses:
        key = p["id"] + ":" + witness
        state["property_sightings"][key] = {
            "taking_id": p["id"], "witness_id": witness,
            "site_id": site, "seen_at": state["time"],
            "actor_id": actor, "source_owner_id": source,
            "resource": resource, "quantity": quantity,
        }


def validate_takings(state: dict[str, Any]) -> None:
    records = state["property_takings"]
    if not isinstance(records, dict):
        raise ValueError("invalid taking ledger")
    for ident, item in records.items():
        if (not _id(ident) or not isinstance(item, dict)
                or set(item) != TAKING_KEYS
                or item["actor_id"] not in state["npcs"]
                or item["source_owner_id"] not in state["npcs"]
                   and item["source_owner_id"] not in state["locations"]
                or item["actor_id"] == item["source_owner_id"]
                or item["site_id"] not in state["locations"]
                or not _id(item["resource"]) or item["resource"] == MONEY
                or item["resource"] in FORBIDDEN
                or type(item["quantity"]) is not int
                or not 1 <= item["quantity"] <= MAX_QUANTITY
                or type(item["taken_at"]) is not int
                or not 0 <= item["taken_at"] <= state["time"]
                or item["permission_basis"] != "no_grant_recorded"):
            raise ValueError("invalid physical taking provenance")
        a, b, q = (item["source_before"], item["target_before"],
                   item["quantity"])
        if (not _balance(a) or not _balance(b)
                or not _balance(item["source_after"])
                or not _balance(item["target_after"])
                or a - item["source_after"] != q
                or item["target_after"] - b != q):
            raise ValueError("physical taking did not conserve inventory")


@dataclass(frozen=True)
class TakingResult:
    event_id: str
    state: WorldState


class NPCPropertyService:
    """Explicit local engine service; NOT an untrusted API or player command."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("taking and clock must share an event store")
        self.store, self.clock = store, clock

    def take(self, world_id: str, actor_id: str, taking_id: str,
             source_owner_id: str, site_id: str, resource: str, quantity: int,
             *, expected_revision: int, witnessed_by: tuple[str, ...] = ()) -> TakingResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if type(expected_revision) is not int or expected_revision != state.revision:
            raise RevisionConflict("stale property command")
        if type(witnessed_by) is not tuple:
            raise ValueError("witnesses must be an explicit tuple")
        event = DomainEvent(
            "PropertyTaken", actor_id, "explicit physical taking",
            state.time, {"id": taking_id, "source_owner_id": source_owner_id,
                         "site_id": site_id, "resource": resource,
                         "quantity": quantity,
                         "witness_ids": list(witnessed_by)})
        after = self.store.append(
            world_id, "property:take:" + str(taking_id),
            expected_revision, [event], taking_authorized=True)
        return TakingResult(taking_id, after)
