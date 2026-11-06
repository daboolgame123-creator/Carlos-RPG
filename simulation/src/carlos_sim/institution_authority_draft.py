"""04-A J1c2b-LAW: inspect a future charter proposal for an EXISTING institution.

Pure trusted design helper: no authority is installed, no event is emitted,
no world resources or legal rights are changed. NOT a player/LLM-facing API.
"""
from __future__ import annotations

from typing import Any
from .domain import WorldState


def prepare_registered_institution_authority_draft(
    state: WorldState, *, institution_id: str, effective_from: int
) -> dict[str, Any]:
    """Check an existing factual registration before considering jurisdiction.

    Presence and institutional model never imply consent or lawful authority.
    In particular, this function cannot create title adjudication powers.
    """
    if type(institution_id) is not str or not institution_id:
        raise ValueError("registered institution ID required")
    record = state.local_institutions.get(institution_id)
    if record is None or record["mandate"] != "existence_record_only":
        raise ValueError("an existing factual institution registration is required")
    if type(effective_from) is not int or not state.time < effective_from <= 2**63 - 1:
        raise ValueError("proposed charter must take effect in future simulation time")
    site_id = record["site_id"]
    representative_id = record["representative_id"]
    if site_id not in state.locations or representative_id not in state.npcs:
        raise ValueError("institution references invalid world entities")
    return {
        "institution_id": institution_id,
        "site_id": site_id,
        "representative_id": representative_id,
        "authority_model_proposed": record["model"],
        "effective_from_proposed": effective_from,
        "registration_mandate": "existence_record_only",
        "charter_status": "unapproved_draft",
        "representative_consent_recorded": False,
        "authorized_issuer_id": None,
        "jurisdiction_effective": False,
        "can_make_binding_law": False,
        "can_decide_title": False,
        "can_seize_property": False,
        "can_delegate_authority": False,
        "legally_enforceable_owner": None,
        "next_prerequisites": [
            "record_valid_authority_source",
            "verify_representative_consent_and_capacity",
            "define_local_scope_and_prospective_mandate",
            "implement_trusted_authorization_and_event_replay",
        ],
        "audience": "trusted_internal_design_only",
    }
