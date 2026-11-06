"""03-A: classify candidate injury-source events without authorizing injury writes.

A DomainEvent is evidence only if it has a supported cause contract. Existing
property and market events cannot be treated as bodily injury by implication.
This intentionally returns fail-closed until a dedicated trusted source event
and store capability are implemented and verified.
"""
from __future__ import annotations

from typing import Any
from .domain import DomainEvent, WorldState


def evaluate_injury_source(state: WorldState, *, subject_id: str,
                           source_event: DomainEvent) -> dict[str, Any]:
    """Return an internal, read-only trust assessment for an injury proposal.

    WARNING: even a well-formed DomainEvent is caller-constructible and does
    not prove SQLite provenance. This helper never grants event authority.
    """
    if type(state) is not WorldState:
        raise ValueError("trusted world state is required")
    if type(subject_id) is not str or not subject_id or subject_id not in state.entities:
        raise ValueError("injury subject must exist")
    if type(source_event) is not DomainEvent:
        raise ValueError("source must be a domain event")
    if source_event.time > state.time:
        raise ValueError("future event cannot cause a present injury")
    event = source_event.to_dict()
    if event["event_type"] in (
        "PropertyTaken", "MarketTradeExecuted", "PlayerVitalChanged",
        "NPCObserved", "PlayerObserved", "PropertyClaimFiled",
    ):
        kind = "not_an_injury_cause"
    else:
        kind = "no_supported_verified_injury_source"
    return {
        "subject_id": subject_id,
        "source_event_type": event["event_type"],
        "source_event_time": event["time"],
        "source_classification": kind,
        "source_in_persisted_ledger_verified": False,
        "causally_proves_injury": False,
        "authority_to_record_injury": False,
        "current_injury_created": False,
        "world_changed": False,
        "audience": "trusted_internal_design_only",
    }
