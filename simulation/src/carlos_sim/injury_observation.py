"""03-A7c1: read-only candidate interpretation of *explicit* visible symptoms.

IMPORTANT: This is a pure, non-authoritative policy. A signal passed by a
caller is NOT proof that an observation occurred. No event may be persisted,
no NPC knowledge may be updated, and no diagnosis may be authorized using
this module until a trusted observation source and replay contract exist.
"""
from __future__ import annotations

from dataclasses import dataclass

from .domain import WorldState

VISIBLE_SIGNALS = frozenset({"limping", "visible_bleeding", "difficulty_moving", "collapse"})
INFERENCES = {
    "limping": "possible_mobility_problem",
    "visible_bleeding": "possible_external_wound",
    "difficulty_moving": "possible_mobility_problem",
    "collapse": "possible_distress",
}


@dataclass(frozen=True)
class CandidateSymptomObservation:
    observer_id: str
    subject_id: str
    visible_signal: str
    inference: str
    observed_at: int
    location_id: str
    confirmed_diagnosis: bool = False


def _present(state: WorldState, npc_id: str) -> bool:
    if npc_id not in state.npcs or npc_id not in state.entities:
        return False
    if any(t["npc_id"] == npc_id and t["status"] == "traveling"
           for t in state.travels.values()):
        return False
    if any(a["npc_id"] == npc_id and a["status"] == "running"
           for a in state.actions.values()):
        return False
    return True


def interpret_visible_symptom(
    state: WorldState, observer_id: str, subject_id: str, signal: str,
    *, observed_at: int,
) -> CandidateSymptomObservation:
    """Interpret a supplied sensory signal without consulting ANY injury record.

    Requiring co-location and current presence is necessary but not sufficient:
    the caller MUST NOT treat this candidate as proof of a real observation.
    This function deliberately cannot return severity, injury IDs or causes.
    """
    if type(state) is not WorldState:
        raise ValueError("world state required")
    if (type(observer_id) is not str or type(subject_id) is not str
            or observer_id == subject_id or not _present(state, observer_id)
            or not _present(state, subject_id)):
        raise ValueError("distinct present NPCs required")
    if (type(signal) is not str or signal not in VISIBLE_SIGNALS):
        raise ValueError("unsupported visible signal")
    if (type(observed_at) is not int or observed_at != state.time
            or not 0 <= observed_at <= 2**63 - 1):
        raise ValueError("observation must use current logical time")
    observer_location = state.entities[observer_id]["location_id"]
    if observer_location != state.entities[subject_id]["location_id"]:
        raise ValueError("remote observation forbidden")
    return CandidateSymptomObservation(
        observer_id=observer_id, subject_id=subject_id,
        visible_signal=signal, inference=INFERENCES[signal],
        observed_at=observed_at, location_id=observer_location,
    )
