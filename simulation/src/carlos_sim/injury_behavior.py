"""03-A7a: purely local self-injury decision advisory for autonomous NPCs.

This module is NOT a medical diagnosis, action authorization, observation, or
healing rule. It reads a single NPC's own persisted injury records and makes
a deterministic self-care recommendation. It MUST NOT examine peers' injuries,
invent any external knowledge, advance world time, or modify the world.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import WorldState

SELF_CARE_THRESHOLD = 20


@dataclass(frozen=True)
class OwnInjuryAdvisory:
    npc_id: str
    active_injury_count: int
    maximum_severity: int
    should_prioritize_rest: bool
    reason: str


def assess_own_injuries(state: WorldState, npc_id: str) -> OwnInjuryAdvisory:
    """Return a self-only health advisory for an existing autonomous NPC.

    Rest is suggested because severe injury may impair effort; it is NOT a
    substitute for the paid, scheduled 03-A6 recovery mechanism.
    """
    if type(state) is not WorldState:
        raise ValueError("world state required")
    if type(npc_id) is not str or npc_id not in state.npcs:
        raise ValueError("self-injury assessment requires a configured NPC")
    maximum = 0
    count = 0
    for rec in state.injuries.values():
        # Intentionally ignore records for EVERY other NPC; do not reveal their
        # identities, counts, severity, treatment or injury onset to this policy.
        if rec["subject_id"] != npc_id or rec["status"] != "active":
            continue
        count += 1
        maximum = max(maximum, rec["severity"])
    prioritize = maximum >= SELF_CARE_THRESHOLD
    reason = (
        "self_known_active_injury_rest_priority"
        if prioritize else (
            "self_known_minor_injury_caution" if count else "no_self_injury_recorded"
        )
    )
    return OwnInjuryAdvisory(
        npc_id=npc_id,
        active_injury_count=count,
        maximum_severity=maximum,
        should_prioritize_rest=prioritize,
        reason=reason,
    )
