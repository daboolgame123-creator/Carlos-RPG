"""J1c2b — prospective LOCAL LAW DRAFT validation only.

This module cannot install a law or create/transfer legal title. A draft is
off-ledger, has no authority, and is never a source of world-state truth.
"""
from __future__ import annotations

from typing import Any
from .domain import WorldState


_ALLOWED_AUTHORITIES = frozenset((
    "customary_assembly", "local_council", "lordly_authority",
))
_ALLOWED_TRANSFER_RULES = frozenset((
    "requires_preexisting_verified_title_and_mutual_consent",
))


def prepare_local_title_law_draft(
    state: WorldState, *,
    site_id: str,
    authority_model: str,
    effective_from: int,
    transfer_rule: str,
) -> dict[str, Any]:
    """Validate an unapproved proposal against the currently loaded world.

    Authority selection here is a DESCRIPTION, not a credential. No active
    legal authority or adjudicator exists in Schema 28/Rules 36.
    """
    if type(site_id) is not str or not site_id or site_id not in state.locations:
        raise ValueError("draft jurisdiction must be a real existing site")
    if type(authority_model) is not str or authority_model not in _ALLOWED_AUTHORITIES:
        raise ValueError("draft authority model is not recognized")
    if type(effective_from) is not int or not state.time < effective_from <= 2**63 - 1:
        raise ValueError("draft must begin strictly after current simulation time")
    if type(transfer_rule) is not str or transfer_rule not in _ALLOWED_TRANSFER_RULES:
        raise ValueError("draft must explicitly require verified title and mutual consent")
    return {
        "site_id": site_id,
        "authority_model_proposed": authority_model,
        "effective_from_proposed": effective_from,
        "title_transfer_rule_proposed": transfer_rule,
        "review_status": "unapproved_draft",
        "installed_in_world": False,
        "authorized_institution_id": None,
        "jurisdiction_effective": False,
        "retroactive": False,
        "legal_title_status": "undetermined",
        "legally_enforceable_owner": None,
        "next_prerequisites": [
            "approve_local_institution_and_scope",
            "verify_existing_legal_title_provenance",
            "define_identifiable_item_lot_and_conflict_procedure",
            "implement_versioned_authorization_and_event_replay",
        ],
        "audience": "trusted_internal_design_only",
    }
