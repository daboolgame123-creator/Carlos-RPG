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


def prepare_local_institution_charter_draft(
    state: WorldState, *,
    institution_id: str,
    site_id: str,
    officer_id: str,
    authority_model: str,
    effective_from: int,
) -> dict[str, Any]:
    """Validate a proposed local institution with a real co-located nominee.

    Candidate presence does not equal consent, appointment, capability,
    judicial power, or an established law. No event is emitted.
    """
    from .market import _id

    if not _id(institution_id):
        raise ValueError("institution draft requires bounded unique-format ID")
    if type(officer_id) is not str or officer_id not in state.npcs:
        raise ValueError("institution nominee must be a real NPC")
    proposal = prepare_local_title_law_draft(
        state, site_id=site_id, authority_model=authority_model,
        effective_from=effective_from,
        transfer_rule="requires_preexisting_verified_title_and_mutual_consent",
    )
    from .market import _present
    # _present expects a mutable state dictionary, and checks real
    # location, travel and competing work. It does not appoint an officer.
    if not _present(state.to_dict(), officer_id, site_id):
        raise ValueError("nominee must be present and free at proposed site")
    return {
        "institution_id_proposed": institution_id,
        "site_id_proposed": site_id,
        "officer_id_nominated": officer_id,
        "authority_model_proposed": authority_model,
        "effective_from_proposed": effective_from,
        "charter_status": "unapproved_draft",
        "nominee_consent_recorded": False,
        "appointed_officer_id": None,
        "institution_registered": False,
        "can_receive_legal_claims": False,
        "can_decide_title": False,
        "can_seize_property": False,
        "can_delegate_authority": False,
        "legal_title_status": proposal["legal_title_status"],
        "next_prerequisites": [
            "approval_of_institution_and_nominee_consent",
            "trusted_registration_and_versioned_capability",
            "explicit_local_jurisdiction_and_conflict_rules",
            "notification_and_hearing_before_any_binding_decision",
        ],
        "audience": "trusted_internal_design_only",
    }
