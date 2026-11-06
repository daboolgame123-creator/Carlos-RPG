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
    return {
        "origin_id": origin_id,
        "resource": origin["resource"],
        "registered_quantity": origin["quantity"],
        "original_recorded_beneficiary": origin["recorded_beneficiary_id"],
        "historical_record_kind": origin["record_kind"],
        "current_recorded_claim_balances": dict(sorted(balances.items())),
        "accepted_historical_assignments": assignments,
        "open_historical_assignment_offers": pending,
        "legal_title_status": "undetermined",
        "legally_enforceable_owner": None,
        "legal_rule_applied": None,
        "physical_custody_derived": False,
    }
