"""04-A/J1c1 — explicit, revocable, finite physical-collection permissions.

A granted right to collect physical stock is not proof of legally enforceable
title, not a transfer of title, and never a judicial finding of innocence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .market import _id, _present, _balance, MAX_QUANTITY
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine

MAX_GRANTS = 1000
MAX_DURATION = 7 * 24 * 3600
PERMISSION_KEYS = {
    "origin_id", "source_holder_id", "site_id", "grantor_id", "grantee_id",
    "resource", "scope", "quantity", "remaining", "used", "granted_at",
    "expires_at", "status", "revoked_at",
}
PERMISSION_EVENTS = {"PropertyPermissionGranted", "PropertyPermissionRevoked"}


def _grantor_controls_origin(state: dict[str, Any], origin: dict[str, Any],
                             grantor: str) -> bool:
    source = origin["source_owner_id"]
    if source in state["npcs"]:
        return grantor == source and origin["recorded_beneficiary_id"] == source
    stall = state["market_stalls"].get(source)
    return (source in state["locations"] and stall is not None
            and stall["keeper_id"] == grantor
            and origin["recorded_beneficiary_id"] == source)


def _exclusively_traceable(state: dict[str, Any], origin_id: str,
                           source: str, resource: str, quantity: int) -> bool:
    lot = state["property_custody_lots"].get(origin_id)
    if lot is None or lot["resource"] != resource:
        return False
    available = state["resources"].get(source, {}).get(resource)
    certified = lot["known_holders"].get(source, 0)
    # No arbitrary matching of "one of the loaves": the entire source stock
    # must unambiguously correspond to this single registered origin.
    return (_balance(available) and available == certified
            and certified >= quantity)


def issue_permission(state: dict[str, Any], event: DomainEvent, *,
                     permission_authorized: bool) -> None:
    p = event.data
    if (not permission_authorized
            or set(p) != {"id", "origin_id", "grantee_id", "quantity", "expires_at"}
            or not _id(p["id"]) or p["id"] in state["property_permissions"]
            or len(state["property_permissions"]) >= MAX_GRANTS
            or not _id(p["origin_id"]) or not _id(p["grantee_id"])
            or type(p["quantity"]) is not int
            or not 1 <= p["quantity"] <= MAX_QUANTITY
            or type(p["expires_at"]) is not int
            or not state["time"] < p["expires_at"] <= state["time"] + MAX_DURATION
            or p["expires_at"] > 2**63 - 1):
        raise ValueError("invalid trusted bounded collection permission")
    origin = state["property_title_origins"].get(p["origin_id"])
    grantor, grantee = event.actor_id, p["grantee_id"]
    if origin is None or not _id(grantor) or grantor == grantee:
        raise ValueError("missing registered origin or distinct grantor")
    source, resource, site = (
        origin["source_owner_id"], origin["resource"], origin["site_id"])
    if (not _grantor_controls_origin(state, origin, grantor)
            or not _present(state, grantor, site)
            or not _present(state, grantee, site)
            or not _exclusively_traceable(
                state, p["origin_id"], source, resource, p["quantity"])):
        raise ValueError("grant requires real local authority and unambiguous registered stock")
    available = state["property_custody_lots"][p["origin_id"]]["known_holders"][source]
    reserved = sum(
        rec["remaining"] for rec in state["property_permissions"].values()
        if rec["origin_id"] == p["origin_id"]
        and rec["source_holder_id"] == source
        and rec["status"] == "open" and rec["expires_at"] > state["time"]
    )
    if reserved + p["quantity"] > available:
        raise ValueError("permission cannot double-reserve registered goods")
    state["property_permissions"][p["id"]] = {
        "origin_id": p["origin_id"], "source_holder_id": source,
        "site_id": site, "grantor_id": grantor, "grantee_id": grantee,
        "resource": resource, "scope": "collect",
        "quantity": p["quantity"], "remaining": p["quantity"], "used": 0,
        "granted_at": state["time"], "expires_at": p["expires_at"],
        "status": "open", "revoked_at": None,
    }


def revoke_permission(state: dict[str, Any], event: DomainEvent, *,
                      permission_authorized: bool) -> None:
    p = event.data
    if (not permission_authorized or set(p) != {"id"} or not _id(p["id"])):
        raise ValueError("revocation requires trusted local permission capability")
    rec = state["property_permissions"].get(p["id"])
    if (rec is None or rec["status"] != "open"
            or rec["grantor_id"] != event.actor_id
            or not _present(state, rec["grantor_id"], rec["site_id"])
            or not _present(state, rec["grantee_id"], rec["site_id"])):
        raise ValueError("only actual grantor meeting grantee may revoke active permission")
    rec["status"] = "revoked"
    rec["revoked_at"] = state["time"]


def redeem_permission(state: dict[str, Any], event: DomainEvent,
                      *, permission_id: str, source: str, site: str,
                      resource: str, quantity: int) -> None:
    rec = state["property_permissions"].get(permission_id) if _id(permission_id) else None
    if (rec is None or rec["status"] != "open"
            or not rec["granted_at"] <= state["time"] < rec["expires_at"]
            or rec["scope"] != "collect"
            or rec["grantee_id"] != event.actor_id
            or rec["source_holder_id"] != source
            or rec["site_id"] != site
            or rec["resource"] != resource
            or quantity > rec["remaining"]
            or not _exclusively_traceable(
                state, rec["origin_id"], source, resource, quantity)):
        raise ValueError("taking lacks matching unexpired, unambiguous local collection permission")
    rec["used"] += quantity
    rec["remaining"] -= quantity
    if rec["remaining"] == 0:
        rec["status"] = "exhausted"


def validate_permissions(state: dict[str, Any]) -> None:
    records = state["property_permissions"]
    if type(records) is not dict or len(records) > MAX_GRANTS:
        raise ValueError("invalid property permission records")
    takings = state["property_takings"]
    counted: dict[str, int] = {}
    # Within a logical second, historical ordering is established by the
    # immutable event revisions, not by timestamps alone. The reducer rejects
    # any use after revocation; here only later-time contradictions are tested.
    for taking in takings.values():
        permit = taking["permission_id"]
        if permit is not None:
            if permit not in records:
                raise ValueError("taking cites missing permission record")
            rec = records[permit]
            if (taking["actor_id"] != rec["grantee_id"]
                    or taking["source_owner_id"] != rec["source_holder_id"]
                    or taking["site_id"] != rec["site_id"]
                    or taking["resource"] != rec["resource"]
                    or not rec["granted_at"] <= taking["taken_at"] < rec["expires_at"]
                    or (rec["revoked_at"] is not None
                        and taking["taken_at"] > rec["revoked_at"])):
                raise ValueError("physical taking contradicts cited permission")
            counted[permit] = counted.get(permit, 0) + taking["quantity"]
    for ident, rec in records.items():
        if not _id(ident) or type(rec) is not dict or set(rec) != PERMISSION_KEYS:
            raise ValueError("invalid permission record shape")
        origin = state["property_title_origins"].get(rec["origin_id"])
        if (origin is None or rec["source_holder_id"] != origin["source_owner_id"]
                or rec["resource"] != origin["resource"]
                or rec["site_id"] != origin["site_id"]
                or rec["scope"] != "collect"
                or not _id(rec["grantor_id"])
                or not _id(rec["grantee_id"])
                or rec["grantor_id"] == rec["grantee_id"]
                or rec["grantee_id"] not in state["npcs"]
                or not _grantor_controls_origin(state, origin, rec["grantor_id"])
                or type(rec["quantity"]) is not int
                or not 1 <= rec["quantity"] <= origin["quantity"]
                or type(rec["used"]) is not int
                or type(rec["remaining"]) is not int
                or not 0 <= rec["used"] <= rec["quantity"]
                or rec["remaining"] != rec["quantity"] - rec["used"]
                or rec["used"] != counted.get(ident, 0)
                or type(rec["granted_at"]) is not int
                or not 0 <= rec["granted_at"] <= state["time"]
                or type(rec["expires_at"]) is not int
                or not rec["granted_at"] < rec["expires_at"] <= rec["granted_at"] + MAX_DURATION
                or rec["expires_at"] > 2**63 - 1
                or rec["status"] not in {"open", "revoked", "exhausted"}):
            raise ValueError("permission origin, quantity, usage or rights are inconsistent")
        if rec["status"] == "exhausted" and rec["remaining"] != 0:
            raise ValueError("exhausted grant carries unused stock")
        if rec["status"] == "open" and rec["remaining"] == 0:
            raise ValueError("open grant has no remaining quantity")
        if rec["status"] == "revoked":
            if (type(rec["revoked_at"]) is not int
                    or not rec["granted_at"] <= rec["revoked_at"] <= state["time"]):
                raise ValueError("revocation must have valid timestamp")
        elif rec["revoked_at"] is not None:
            raise ValueError("non-revoked permission carries fake revocation time")


def _internal_permission_view(world: WorldState, permission_id: str) -> dict:
    """Trusted engine only, never passed into NPC knowledge or player_view."""
    if permission_id not in world.property_permissions:
        raise ValueError("unknown registered permission")
    return dict(world.property_permissions[permission_id])


@dataclass(frozen=True)
class PermissionResult:
    permission_id: str
    state: WorldState


class NPCPermissionService:
    """Local command coordinator; NOT a network identity/authentication API."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError("permission coordinator must use same store/clock")
        self.store, self.clock = store, clock

    def _append(self, world_id: str, actor_id: str, permit_id: str,
                event_type: str, data: dict[str, Any], *,
                expected_revision: int) -> PermissionResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if type(expected_revision) is not int or expected_revision != state.revision:
            raise RevisionConflict("stale permission command")
        ev = DomainEvent(event_type, actor_id, "trusted explicit local custody permission",
                         state.time, data)
        updated = self.store.append(
            world_id, "permit:" + event_type + ":" + permit_id,
            expected_revision, [ev], permission_authorized=True)
        return PermissionResult(permit_id, updated)

    def grant(self, world_id: str, grantor_id: str, permission_id: str,
              origin_id: str, grantee_id: str, quantity: int, *,
              expires_at: int, expected_revision: int) -> PermissionResult:
        return self._append(
            world_id, grantor_id, permission_id, "PropertyPermissionGranted",
            {"id": permission_id, "origin_id": origin_id,
             "grantee_id": grantee_id, "quantity": quantity,
             "expires_at": expires_at}, expected_revision=expected_revision)

    def revoke(self, world_id: str, grantor_id: str, permission_id: str,
               *, expected_revision: int) -> PermissionResult:
        return self._append(
            world_id, grantor_id, permission_id, "PropertyPermissionRevoked",
            {"id": permission_id}, expected_revision=expected_revision)
