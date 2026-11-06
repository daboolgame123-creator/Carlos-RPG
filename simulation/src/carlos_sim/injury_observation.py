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


def observed_resting_activity(state: WorldState, observer_id: str,
                              subject_id: str) -> dict[str, object] | None:
    """Evidence of *visible current rest*, not evidence of injury.

    Only a previously recorded local sighting and a real active rest action
    can produce this bounded qualitative result. Rest may be due to ordinary
    fatigue, preference or injury; never return the cause, severity, medical
    data, the action identifier or a diagnosis.
    """
    if type(state) is not WorldState:
        raise ValueError("validated WorldState required")
    if (type(observer_id) is not str or type(subject_id) is not str
            or observer_id == subject_id
            or observer_id not in state.npcs or subject_id not in state.npcs):
        return None
    site = state.entities[observer_id]["location_id"]
    if state.entities[subject_id]["location_id"] != site:
        return None
    raw = state.to_dict()
    if not _present(raw, observer_id, site):
        return None
    from .movement import _in_transit
    from .production import is_producing
    if _in_transit(raw, subject_id) or is_producing(raw, subject_id):
        return None
    sighting = state.observations.get(observer_id, {}).get(site)
    if (sighting is None or sighting["at"] != state.time
            or observer_id not in sighting["occupants"]
            or subject_id not in sighting["occupants"]):
        return None
    resting = any(
        a["npc_id"] == subject_id and a["action"] == "rest"
        and a["status"] == "running" and a["start"] <= state.time < a["due"]
        for a in state.actions.values()
    )
    if not resting:
        return None
    return {
        "subject_id": subject_id,
        "sign": "visible_resting",
        "site_id": site,
        "observed_at": state.time,
    }
