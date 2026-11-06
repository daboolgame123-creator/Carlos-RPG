"""J1c2b: trusted founding records for local institutions, without judicial powers.

A registered institution is a factual existence/representation record at the
world's founding. It is NOT a law, appointment to court, title judgment,
authority to seize property, or universal jurisdiction.
"""
from __future__ import annotations

from typing import Any
from .market import _id, _present

MODELS = frozenset(("customary_assembly", "local_council", "lordly_authority"))
MAX_INSTITUTIONS = 100
INSTITUTION_KEYS = frozenset((
    "site_id", "representative_id", "model", "registered_at", "mandate",
))


def register_institution(state: dict[str, Any], event, *, bootstrap: bool) -> None:
    p = event.data
    if (not bootstrap or state["time"] != 0 or event.actor_id is not None
            or set(p) != {"id", "site_id", "representative_id", "model"}
            or not _id(p.get("id"))
            or p["id"] in state["local_institutions"]
            or len(state["local_institutions"]) >= MAX_INSTITUTIONS):
        raise ValueError("local institution requires unique trusted time-zero registration")
    site = p["site_id"]
    representative = p["representative_id"]
    if (not _id(site) or site not in state["locations"]
            or not _id(representative) or representative not in state["npcs"]
            or p["model"] not in MODELS
            or not _present(state, representative, site)
            or any(row["site_id"] == site for row in state["local_institutions"].values())
            or any(row["representative_id"] == representative
                   for row in state["local_institutions"].values())):
        raise ValueError("local institution must have one available real representative per site")
    state["local_institutions"][p["id"]] = {
        "site_id": site,
        "representative_id": representative,
        "model": p["model"],
        "registered_at": state["time"],
        "mandate": "existence_record_only",
    }


def validate_institutions(state: dict[str, Any]) -> None:
    records = state["local_institutions"]
    if type(records) is not dict or len(records) > MAX_INSTITUTIONS:
        raise ValueError("invalid local institution records")
    seen_sites: set[str] = set()
    seen_representatives: set[str] = set()
    for ident, row in records.items():
        if (not _id(ident) or type(row) is not dict or set(row) != INSTITUTION_KEYS
                or row["site_id"] not in state["locations"]
                or row["representative_id"] not in state["npcs"]
                or row["model"] not in MODELS
                or row["registered_at"] != 0
                or row["mandate"] != "existence_record_only"
                or row["site_id"] in seen_sites
                or row["representative_id"] in seen_representatives):
            raise ValueError("invalid or duplicate local institution founding record")
        seen_sites.add(row["site_id"])
        seen_representatives.add(row["representative_id"])


def institution_record(state, institution_id: str) -> dict[str, Any]:
    """Internal-only read-only evidence. Never exposes powers by implication."""
    if type(institution_id) is not str or not institution_id:
        raise ValueError("institution ID required")
    row = state.local_institutions.get(institution_id)
    if row is None:
        raise ValueError("local institution not registered")
    return {
        "institution_id": institution_id,
        "site_id": row["site_id"],
        "representative_id": row["representative_id"],
        "model": row["model"],
        "registered_at": row["registered_at"],
        "mandate": row["mandate"],
        "can_decide_title": False,
        "can_seize_property": False,
        "legal_title_status": "undetermined",
        "authorized_court_id": None,
        "audience": "trusted_internal_audit_only",
    }
