"""Phase 03-A2 preliminary injury-intake contract for trusted test scenarios.

A successful assessment is NOT an injury, event, HP change, or medical finding.
This module does not mutate WorldState, authorize a command, or persist data.
It must not be exposed directly to untrusted clients.
"""
from __future__ import annotations

from typing import Any

MAX_INJURY_SEVERITY = 100
MAX_SIM_TIME = 2**63 - 1


def assess_injury_intake(
    state: Any, *, subject_id: str, injury_id: str, severity: int,
    source_kind: str, source_reference: str, onset_time: int,
) -> dict[str, Any]:
    """Check a proposed *test-only* injury record against current world facts.

    A caller-supplied source_reference is not verified provenance. Hence this
    returns a rejected-for-commit proposal even when shape checks succeed.
    """
    if type(subject_id) is not str or not 1 <= len(subject_id) <= 80 or not subject_id.isascii() or not all(c.isalnum() or c in '._-' for c in subject_id):
        raise ValueError("subject ID must use bounded ASCII identifier syntax")
    subject = state.entities.get(subject_id)
    if subject is None or subject.get("controller") not in ("npc", "player"):
        raise ValueError("subject must be an existing NPC or player")
    if type(injury_id) is not str or not 1 <= len(injury_id) <= 80 or not injury_id.isascii() or not all(c.isalnum() or c in '._-' for c in injury_id):
        raise ValueError("invalid proposed injury ID")
    if type(severity) is not int or not 1 <= severity <= MAX_INJURY_SEVERITY:
        raise ValueError("injury severity must be in 1..100")
    if source_kind != "trusted_test_scenario" or type(source_kind) is not str:
        raise ValueError("no gameplay injury source is currently authorized")
    if type(source_reference) is not str or not 1 <= len(source_reference) <= 80 or not source_reference.isascii() or not all(c.isalnum() or c in '._-' for c in source_reference):
        raise ValueError("an identified proposed source is required")
    if type(onset_time) is not int or onset_time != state.time or not 0 <= onset_time <= MAX_SIM_TIME:
        raise ValueError("injury onset must equal the logical current time")
    controller = subject["controller"]
    profile = state.rpg_profiles.get(subject_id) if controller == "player" else None
    hp_current = None
    if profile is not None:
        hp_current = profile["vitals"]["hp"]["current"]
    return {
        "subject_id": subject_id,
        "controller": controller,
        "injury_id_proposed": injury_id,
        "severity_proposed": severity,
        "source_kind_proposed": source_kind,
        "source_reference_proposed": source_reference,
        "onset_time_proposed": onset_time,
        "hp_current_known": hp_current is not None,
        "hp_adjustment": None,
        "injury_recorded": False,
        "source_provenance_verified": False,
        "world_mutated": False,
        "commit_authorized": False,
        "status": "unverified_intake_only",
        "audience": "trusted_internal_design_only",
    }
