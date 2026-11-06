"""J1c2b: read-only provenance inventory, NOT a legal-title decision engine.

Input is a trusted internal WorldState (never expose raw state to players).
No rules of law, title transfer, adjudication, or ownership inference here.
"""
from __future__ import annotations

from typing import Any
from .domain import WorldState


def historical_title_evidence(state: WorldState, origin_id: str) -> dict[str, Any]:
    """Summarize recorded provenance for one registered origin, without legal effects.

    Claims and physical holdings deliberately remain separate. Absence of a
    legal rule means status is *undetermined*, even when there are no objections.
    """
    if type(origin_id) is not str or not origin_id:
        raise ValueError("nonempty registered origin ID required")
    origin = state.property_title_origins.get(origin_id)
    if origin is None:
        raise ValueError("registered origin not found")
    balances = state.registered_claim_balances.get(origin_id)
    if balances is None:
        raise ValueError("registered claim ledger missing")
    assignments = [
        {"offer_id": key, "from_account": value["from_account"],
         "recipient_id": value["recipient_id"], "quantity": value["quantity"],
         "accepted_at": value["accepted_at"]}
        for key, value in state.registered_claim_transfers.items()
        if value["origin_id"] == origin_id
    ]
    assignments.sort(key=lambda item: (item["accepted_at"], item["offer_id"]))
    pending = [
        {"offer_id": key, "from_account": value["from_account"],
         "recipient_id": value["recipient_id"], "quantity": value["quantity"],
         "expires_at": value["expires_at"]}
        for key, value in state.registered_claim_offers.items()
        if value["origin_id"] == origin_id
        and value["status"] == "open"
        and value["expires_at"] > state.time
    ]
    pending.sort(key=lambda item: item["offer_id"])
    offer_history = [
        {"offer_id": key, "from_account": value["from_account"],
         "recipient_id": value["recipient_id"], "quantity": value["quantity"],
         "opened_at": value["opened_at"], "expires_at": value["expires_at"],
         "recorded_status": value["status"],
         "effective_status": ("expired" if value["status"] == "open"
                              and value["expires_at"] <= state.time
                              else value["status"]),
         "resolved_at": value["resolved_at"]}
        for key, value in state.registered_claim_offers.items()
        if value["origin_id"] == origin_id
    ]
    offer_history.sort(key=lambda item: (item["opened_at"], item["offer_id"]))
    return {
        "origin_id": origin_id,
        "resource": origin["resource"],
        "registered_quantity": origin["quantity"],
        "original_recorded_beneficiary": origin["recorded_beneficiary_id"],
        "historical_record_kind": origin["record_kind"],
        "current_recorded_claim_balances": dict(sorted(balances.items())),
        "accepted_historical_assignments": assignments,
        "open_historical_assignment_offers": pending,
        "historical_assignment_offer_history": offer_history,
        "legal_title_status": "undetermined",
        "legally_enforceable_owner": None,
        "legal_rule_applied": None,
        "physical_custody_derived": False,
    }


def origin_evidence_packet(state: WorldState, origin_id: str) -> dict[str, Any]:
    """Trusted-auditor packet: historical ledger and physical custody side by side.

    The two traces must never be reconciled into a legal owner, and unresolved
    physical units must not be arbitrarily allocated to a recorded claimant.
    This can expose confidential actor locations/accounts: NEVER give the
    result directly to a player, NPC, LLM, or an untrusted network request.
    """
    history = historical_title_evidence(state, origin_id)
    lot = state.property_custody_lots.get(origin_id)
    if lot is None:
        raise ValueError("registered physical custody lot missing")
    movements = [
        {"id": key, "from_holder": row["source_holder"],
         "to_holder": row["target_holder"], "quantity": row["quantity"],
         "kind": row["kind"], "event_kind": row["event_kind"],
         "event_revision": row["event_revision"], "at": row["at"]}
        for key, row in state.property_custody_moves.items()
        if row["origin_id"] == origin_id
    ]
    movements.sort(key=lambda item: (item["event_revision"], item["id"]))
    physical = {
        "known_holders": dict(sorted(lot["known_holders"].items())),
        "unresolved_quantity": lot["unresolved_quantity"],
        "exited_quantity": lot["exited_quantity"],
        "physical_movements": movements,
        "provenance_certainty": (
            "partial_or_unknown" if lot["unresolved_quantity"] else "tracked_or_exited"
        ),
    }
    if (sum(physical["known_holders"].values())
            + physical["unresolved_quantity"]
            + physical["exited_quantity"] != history["registered_quantity"]):
        raise ValueError("custody evidence does not conserve registered origin")
    return {
        "historical_claim_evidence": history,
        "physical_custody_evidence": physical,
        "legal_title_status": "undetermined",
        "legally_enforceable_owner": None,
        "legal_rule_applied": None,
        "audience": "trusted_internal_audit_only",
    }


def property_claim_audit_packet(state: WorldState, claim_id: str) -> dict[str, Any]:
    """Trusted-only audit of an NPC statement and its cited physical record.

    A claim has no origin_id in the existing schema. Never bind it to a
    particular registered origin based on location/resource coincidence.
    Direct sighting supports the described *physical taking*, not ownership,
    criminal guilt, or legal title.
    """
    if type(claim_id) is not str or not claim_id:
        raise ValueError("nonempty claim ID required")
    claim = state.property_claims.get(claim_id)
    if claim is None:
        raise ValueError("property claim not found")
    taking_id = claim["taking_id"]
    observed = None
    if taking_id is not None:
        taking = state.property_takings.get(taking_id)
        if taking is None:
            raise ValueError("claim cites missing taking")
        observed = {
            "taking_id": taking_id,
            "actor_id": taking["actor_id"],
            "source_owner_id": taking["source_owner_id"],
            "resource": taking["resource"],
            "quantity": taking["quantity"],
            "site_id": taking["site_id"],
            "taken_at": taking["taken_at"],
            "evidence_scope": "recorded_physical_action_only",
        }
    return {
        "claim_id": claim_id,
        "claimant_id": claim["claimant_id"],
        "claim_kind": claim["claim_kind"],
        "alleged_subject_id": claim["subject_id"],
        "resource": claim["resource"],
        "quantity": claim["quantity"],
        "site_id": claim["site_id"],
        "filed_at": claim["filed_at"],
        "claim_status": claim["status"],
        "basis": claim["basis"],
        "cited_physical_taking": observed,
        "registered_origin_id": None,
        "origin_linkage": "not_established",
        "legal_title_status": "undetermined",
        "legally_enforceable_owner": None,
        "guilt_determined": False,
        "audience": "trusted_internal_audit_only",
    }


def property_claim_context_packet(state: WorldState, claim_id: str) -> dict[str, Any]:
    """Trusted-only comparison of statements sharing a site and resource.

    Co-location and matching resource are merely search criteria. They do NOT
    establish identical goods, the same incident, corroboration or conflict
    about a legally identified object. This is not an NPC/player view.
    """
    selected = property_claim_audit_packet(state, claim_id)
    related = [
        {"claim_id": ident, "claimant_id": row["claimant_id"],
         "claim_kind": row["claim_kind"], "alleged_subject_id": row["subject_id"],
         "quantity": row["quantity"], "filed_at": row["filed_at"],
         "basis": row["basis"], "taking_id": row["taking_id"],
         "comparison_basis": "same_site_and_resource_only",
         "same_physical_incident_established": False,
         "same_registered_origin_established": False}
        for ident, row in state.property_claims.items()
        if ident != claim_id and row["site_id"] == selected["site_id"]
        and row["resource"] == selected["resource"]
    ]
    related.sort(key=lambda item: (item["filed_at"], item["claim_id"]))
    return {
        "selected_claim": selected,
        "potentially_related_statements": related,
        "comparison_scope": "same_site_and_resource_only",
        "conflict_determined": False,
        "legal_title_status": "undetermined",
        "legally_enforceable_owner": None,
        "audience": "trusted_internal_audit_only",
    }
