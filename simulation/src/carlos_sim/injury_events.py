"""03-A4: event-projected *bootstrap-only* NPC injury evidence.

No spontaneous injury, combat damage, healing, or player HP mutation.
A trusted setup event is sufficient to preserve an initial test injury; it
does NOT establish a generic runtime injury source or treatment authority.
"""
from __future__ import annotations

from typing import Any

from .domain import DomainEvent
from .injury_registry import validate_candidate_registry, draft_registry_insertion
from .injury_transitions import draft_injury_record

BOOTSTRAP_SOURCE = "trusted_test_bootstrap"


def validate_injury_state(state: dict[str, Any]) -> None:
    validate_candidate_registry(state["injuries"], state["entities"], at_time=state["time"])
    for row in state["injuries"].values():
        subject_id = row["subject_id"]
        if (subject_id not in state["npcs"]
                or state["entities"][subject_id]["controller"] != "npc"):
            raise ValueError("first injury ledger is NPC-only")


def project_bootstrap_injury(state: dict[str, Any], event: DomainEvent, *,
                             bootstrap: bool) -> None:
    p = event.data
    if (event.event_type != "InjuryRecorded"
            or not bootstrap or state["time"] != 0
            or event.actor_id is not None
            or set(p) != {"injury_id", "subject_id", "severity", "source"}
            or p["source"] != BOOTSTRAP_SOURCE):
        raise ValueError("injury evidence requires trusted time-zero test bootstrap")
    subject = p["subject_id"]
    if (type(subject) is not str or subject not in state["npcs"]
            or state["entities"][subject]["controller"] != "npc"):
        raise ValueError("injury must reference a configured NPC")
    proposed = draft_injury_record(
        injury_id=p["injury_id"], subject_id=subject,
        severity=p["severity"], onset=state["time"],
    )
    state["injuries"] = draft_registry_insertion(
        state["injuries"], state["entities"], record=proposed,
        at_time=state["time"],
    )
