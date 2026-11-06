"""03-A7c: pure gate for a recorded, local NPC observation opportunity.

This does not infer a symptom from an injury record, write beliefs or grant
permission to access medical data. It verifies only the *opportunity* to
observe a peer; a separate trusted symptom producer is required.
"""
from __future__ import annotations

from .domain import WorldState
from .market import _present


def witnessed_peer_here(state: WorldState, observer_id: str,
                        subject_id: str) -> bool:
    """Has the observer actually recorded seeing this available peer *now*?

    Stale snapshots, transit, production/busy activity and bare co-location
    are not enough. Never read `state.injuries` or peer beliefs here.
    """
    if type(state) is not WorldState:
        raise ValueError("validated WorldState required")
    if type(observer_id) is not str or type(subject_id) is not str:
        return False
    if observer_id == subject_id:
        return False
    if observer_id not in state.npcs or subject_id not in state.npcs:
        return False
    site = state.entities[observer_id]["location_id"]
    if state.entities[subject_id]["location_id"] != site:
        return False
    raw = state.to_dict()
    if not _present(raw, observer_id, site) or not _present(raw, subject_id, site):
        return False
    observation = state.observations.get(observer_id, {}).get(site)
    return (
        observation is not None
        and observation["at"] == state.time
        and observer_id in observation["occupants"]
        and subject_id in observation["occupants"]
    )
