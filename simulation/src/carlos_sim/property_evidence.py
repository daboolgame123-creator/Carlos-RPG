"""02-H2: contemporaneous witnessed physical facts and explicitly unproven claims.

Witness observations are created ONLY within PropertyTaken's atomic reducer.
A complaint/claim can be mistaken or malicious; no guilt follows.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent
from .market import _id, MAX_QUANTITY, MONEY, FORBIDDEN
from .movement import _in_transit

MAX_CLAIMS = 1000
SIGHTING_KEYS = {
    "taking_id", "witness_id", "site_id", "seen_at", "actor_id",
    "source_owner_id", "resource", "quantity",
}
CLAIM_KEYS = {
    "claimant_id", "claim_kind", "subject_id", "site_id", "resource",
    "quantity", "taking_id", "filed_at", "basis", "status",
}


def validate_initial_witnesses(state: dict[str, Any], actor: str,
                               site: str, witnesses: Any) -> tuple[str, ...]:
    if (type(witnesses) is not list or len(witnesses) > 7
            or any(not _id(w) for w in witnesses)
            or len(witnesses) != len(set(witnesses))
            or actor in witnesses):
        raise ValueError("witness list must be finite, unique and explicit")
    for witness in witnesses:
        if (witness not in state["npcs"] or witness not in state["entities"]
                or state["entities"][witness]["location_id"] != site
                or _in_transit(state, witness)):
            raise ValueError("sighting requires a real physically present witness")
    return tuple(witnesses)


def file_property_claim(state: dict[str, Any], event: DomainEvent, *,
                        claim_authorized: bool) -> None:
    p = event.data
    if (not claim_authorized or set(p) != {
            "id", "claim_kind", "subject_id", "site_id", "resource",
            "quantity", "taking_id"}
            or not _id(p.get("id")) or p["id"] in state["property_claims"]
            or len(state["property_claims"]) >= MAX_CLAIMS):
        raise ValueError("claim needs trusted local session and unique bounded ID")
    actor, subject, taking = event.actor_id, p["subject_id"], p["taking_id"]
    if (actor not in state["npcs"]
            or state["entities"][actor]["location_id"] != p["site_id"]
            or _in_transit(state, actor)
            or not _id(p["site_id"]) or p["site_id"] not in state["locations"]
            or p["claim_kind"] not in ("loss", "accusation", "ownership")
            or not _id(p["resource"]) or p["resource"] == MONEY
            or p["resource"] in FORBIDDEN
            or type(p["quantity"]) is not int
            or not 1 <= p["quantity"] <= MAX_QUANTITY
            or subject is not None and (not _id(subject) or subject not in state["entities"])
            or taking is not None and not _id(taking)):
        raise ValueError("claim requires real local claimant and well-formed assertion")
    if p["claim_kind"] == "accusation" and subject is None:
        raise ValueError("accusation must name its alleged subject")
    # A taking ID is hidden audit knowledge: only an eyewitness (or the
    # taking actor) can cite it. A victim may report a loss without this ID.
    basis = "unverified_statement"
    if taking is not None:
        recorded = state["property_takings"].get(taking)
        if (recorded is None or recorded["resource"] != p["resource"]
                or recorded["site_id"] != p["site_id"]
                or (actor != recorded["actor_id"] and
                    taking + ":" + actor not in state["property_sightings"])):
            raise ValueError("claimant cannot cite unobserved or mismatched taking")
        basis = "firsthand_action" if actor == recorded["actor_id"] else "direct_sighting"
    state["property_claims"][p["id"]] = {
        "claimant_id": actor, "claim_kind": p["claim_kind"],
        "subject_id": subject, "site_id": p["site_id"],
        "resource": p["resource"], "quantity": p["quantity"],
        "taking_id": taking, "filed_at": state["time"],
        "basis": basis, "status": "unverified",
    }


def validate_property_evidence(state: dict[str, Any]) -> None:
    sightings, claims = state["property_sightings"], state["property_claims"]
    if not isinstance(sightings, dict) or not isinstance(claims, dict):
        raise ValueError("property evidence must be persistent mappings")
    for key, row in sightings.items():
        if (not isinstance(row, dict) or set(row) != SIGHTING_KEYS
                or not _id(row["taking_id"]) or not _id(row["witness_id"])
                or key != row["taking_id"] + ":" + row["witness_id"]
                or row["witness_id"] not in state["npcs"]
                or row["taking_id"] not in state["property_takings"]):
            raise ValueError("invalid sighting provenance")
        taking = state["property_takings"][row["taking_id"]]
        if (row["witness_id"] == taking["actor_id"]
                or row["site_id"] != taking["site_id"]
                or row["seen_at"] != taking["taken_at"]
                or row["actor_id"] != taking["actor_id"]
                or row["source_owner_id"] != taking["source_owner_id"]
                or row["resource"] != taking["resource"]
                or row["quantity"] != taking["quantity"]):
            raise ValueError("sighting must describe an actual same-tick physical event")
    if len(claims) > MAX_CLAIMS:
        raise ValueError("too many property claims")
    for ident, row in claims.items():
        if (not _id(ident) or not isinstance(row, dict) or set(row) != CLAIM_KEYS
                or row["claimant_id"] not in state["npcs"]
                or row["site_id"] not in state["locations"]
                or row["claim_kind"] not in ("loss", "accusation", "ownership")
                or not _id(row["resource"]) or row["resource"] == MONEY
                or row["resource"] in FORBIDDEN
                or type(row["quantity"]) is not int
                or not 1 <= row["quantity"] <= MAX_QUANTITY
                or type(row["filed_at"]) is not int
                or not 0 <= row["filed_at"] <= state["time"]
                or row["basis"] not in ("unverified_statement", "direct_sighting", "firsthand_action")
                or row["status"] != "unverified"):
            raise ValueError("invalid unproven property claim")
        subject, taking_id = row["subject_id"], row["taking_id"]
        if (subject is not None and subject not in state["entities"]
                or row["claim_kind"] == "accusation" and subject is None):
            raise ValueError("claim subject invalid")
        if taking_id is not None:
            taking = state["property_takings"].get(taking_id)
            if (taking is None or taking["site_id"] != row["site_id"]
                    or taking["resource"] != row["resource"]):
                raise ValueError("claim reference not genuine")
            expected = ("firsthand_action" if row["claimant_id"] == taking["actor_id"]
                        else "direct_sighting" if taking_id + ":" + row["claimant_id"] in sightings
                        else None)
            if row["basis"] != expected:
                raise ValueError("claimant lacks genuine firsthand provenance")
        elif row["basis"] != "unverified_statement":
            raise ValueError("unreferenced claim cannot assert direct evidence")


def personal_property_evidence(world, actor_id: str) -> dict[str, tuple]:
    """Viewpoint-limited projection, NOT global audit/public narrative."""
    if actor_id not in world.entities:
        raise ValueError("unknown viewer")
    return {
        "sightings": tuple({"id": key, **dict(row)}
                           for key, row in world.property_sightings.items()
                           if row["witness_id"] == actor_id),
        "claims": tuple({"id": key, **dict(row)}
                        for key, row in world.property_claims.items()
                        if row["claimant_id"] == actor_id),
    }
