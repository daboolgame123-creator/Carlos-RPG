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


def observed_local_activities(state: WorldState, observer_id: str) -> tuple[dict[str, object], ...]:
    """Bounded read-only local scene evidence for one NPC, never diagnosis.

    A peer's current rest is visible only through the observer's own recorded
    same-tick NPCObserved snapshot and the persisted ongoing action. No
    omniscient per-tick scan grants knowledge or invents a health conclusion.
    """
    if type(state) is not WorldState:
        raise ValueError("validated WorldState required")
    if type(observer_id) is not str or observer_id not in state.npcs:
        return ()
    site = state.entities[observer_id]["location_id"]
    raw = state.to_dict()
    if not _present(raw, observer_id, site):
        return ()
    sighting = state.observations.get(observer_id, {}).get(site)
    if sighting is None or sighting["at"] != state.time:
        return ()
    if observer_id not in sighting["occupants"]:
        return ()
    results = []
    for subject_id in sighting["occupants"]:
        result = observed_resting_activity(state, observer_id, subject_id)
        if result is not None:
            results.append(result)
    return tuple(results)


def explain_visible_rest(state: WorldState, observer_id: str,
                         subject_id: str) -> dict[str, object] | None:
    """An evidence-constrained interpretation: the *cause is unknown*.

    This is a deliberately conservative baseline. Individual suspicions can
    be modeled later only from separately established, observer-owned
    experience and memories. A visible rest is never proof of an injury.
    """
    observed = observed_resting_activity(state, observer_id, subject_id)
    if observed is None:
        return None
    return {
        **observed,
        "interpretation": "cause_unknown",
        "medical_conclusion": None,
    }


# A rest observation is historical behavioral evidence, not a health finding.
# IDs are small and parser-friendly; avoid interpreting arbitrary text.
ACTIVITY_PREFIX = "visible-rest:"
MAX_REST_MEMORIES = 64


def activity_memory_key(subject_id: str, tick: int) -> str:
    from .injury_transitions import _ident, _time
    if not _ident(subject_id) or not _time(tick):
        raise ValueError("invalid activity evidence identity/time")
    return f"{ACTIVITY_PREFIX}{subject_id}:{tick}"


def _activity_target(key: str, tick: int) -> str | None:
    if type(key) is not str or not key.startswith(ACTIVITY_PREFIX):
        return None
    raw = key[len(ACTIVITY_PREFIX):]
    subject, sep, timestamp = raw.rpartition(":")
    if not sep:
        return None
    try:
        if activity_memory_key(subject, tick) != key:
            return None
    except ValueError:
        return None
    return subject


def check_activity_memory_delivery(state: dict, event) -> None:
    """Strict reducer-side evidence for one first-hand visible rest.

    Never authorize an arbitrary message that uses this reserved namespace.
    Re-check all physical and recorded observational facts at projection time.
    """
    p = event.data
    observer = p["npc_id"]
    key = p["key"]
    subject = _activity_target(key, state["time"])
    site = state["entities"][observer]["location_id"]
    expected = {
        "text": f"visible-resting; observed_at={state['time']}",
        "source": "observation:" + site,
        "received_at": state["time"],
        "confidence": 90,
    }
    if (subject is None or subject not in state["npcs"]
            or subject == observer or p["sender_id"] != observer
            or event.actor_id != observer
            or p["method"] != "observation"
            or p["location_id"] != site or p["claim"] != expected):
        raise ValueError("invalid visible-activity evidence")
    if not any(
        action["npc_id"] == subject and action["action"] == "rest"
        and action["status"] == "running"
        and action["start"] <= state["time"] < action["due"]
        for action in state["actions"].values()
    ):
        raise ValueError("resting evidence lacks active physical action")
    from .market import _present
    if not (_present(state, observer, site)
            and state["entities"][subject]["location_id"] == site):
        raise ValueError("resting evidence requires available local witness")
    from .movement import _in_transit
    from .production import is_producing
    if _in_transit(state, subject) or is_producing(state, subject):
        raise ValueError("resting subject not physically available")
    sight = state["observations"].get(observer, {}).get(site)
    if (sight is None or sight["at"] != state["time"]
            or observer not in sight["occupants"]
            or subject not in sight["occupants"]):
        raise ValueError("resting evidence requires a recorded current sighting")
    if key in state["npcs"][observer]["beliefs"] or any(
        item["key"] == key for item in state["npcs"][observer]["inbox"].values()
    ):
        raise ValueError("duplicate recorded resting memory")
    stored = sum(k.startswith(ACTIVITY_PREFIX)
                 for k in state["npcs"][observer]["beliefs"])
    pending = sum(item["key"].startswith(ACTIVITY_PREFIX)
                  for item in state["npcs"][observer]["inbox"].values())
    if stored + pending >= MAX_REST_MEMORIES:
        raise ValueError("visible-activity history capacity reached")


def make_rest_activity_events(state: WorldState, observer_id: str,
                              command_id: str) -> list:
    """Draft observations of real local resting peers for atomic append.

    Called by a trusted explicit observe command. Reducer independently
    verifies action, same-tick sighting and claim before persisting.
    """
    from .domain import DomainEvent
    from .movement import _visible
    from .injury_transitions import _ident
    if not _ident(command_id):
        raise ValueError("activity observation command requires bounded ID")
    if type(state) is not WorldState or observer_id not in state.npcs:
        raise ValueError("configured observer required")
    site = state.entities[observer_id]["location_id"]
    raw = state.to_dict()
    if not _present(raw, observer_id, site):
        raise ValueError("unavailable observer")
    results = []
    recorded_count = sum(k.startswith(ACTIVITY_PREFIX)
                         for k in state.npcs[observer_id]["beliefs"])
    reserved_count = sum(item["key"].startswith(ACTIVITY_PREFIX)
                         for item in state.npcs[observer_id]["inbox"].values())
    remaining = max(0, MAX_REST_MEMORIES - recorded_count - reserved_count)
    for subject in _visible(raw, site):
        if remaining <= 0:
            break
        if subject == observer_id or subject not in state.npcs:
            continue
        if not any(a["npc_id"] == subject and a["action"] == "rest"
                   and a["status"] == "running" and a["start"] <= state.time < a["due"]
                   for a in state.actions.values()):
            continue
        key = activity_memory_key(subject, state.time)
        if (key in state.npcs[observer_id]["beliefs"]
                or any(item["key"] == key for item in state.npcs[observer_id]["inbox"].values())):
            continue
        claim = {
            "text": f"visible-resting; observed_at={state.time}",
            "source": "observation:" + site,
            "received_at": state.time,
            "confidence": 90,
        }
        delivery_id = f"rest-obs:{observer_id}:{subject}:{state.time}:{command_id}"
        remaining -= 1
        results.extend([
            DomainEvent("NPCInformationDelivered", observer_id,
                        "explicit local resting activity", state.time,
                        {"npc_id": observer_id, "delivery_id": delivery_id,
                         "key": key, "claim": claim, "sender_id": observer_id,
                         "location_id": site, "method": "observation"}),
            DomainEvent("NPCBeliefReceived", observer_id,
                        "retain first-hand resting activity", state.time,
                        {"npc_id": observer_id, "key": key,
                         "delivery_id": delivery_id}),
        ])
    return results


def recall_rest_activity(state: WorldState, observer_id: str) -> tuple[dict[str, object], ...]:
    """Read only this NPC's verified historical visible-rest memories."""
    if type(state) is not WorldState:
        raise ValueError("validated WorldState required")
    if type(observer_id) is not str or observer_id not in state.npcs:
        return ()
    found = []
    for key, claim in state.npcs[observer_id]["beliefs"].items():
        if not key.startswith(ACTIVITY_PREFIX):
            continue
        prefix = key[len(ACTIVITY_PREFIX):]
        subject, _, raw_tick = prefix.rpartition(":")
        if not raw_tick.isascii() or not raw_tick.isdecimal() or len(raw_tick) > 19:
            continue
        tick = int(raw_tick)
        if _activity_target(key, tick) != subject or tick > state.time:
            continue
        if claim["text"] != f"visible-resting; observed_at={tick}":
            continue
        found.append({
            "subject_id": subject, "sign": "visible_resting",
            "observed_at": tick, "source": claim["source"],
            "interpretation": "cause_unknown",
        })
    return tuple(sorted(found, key=lambda row: (row["observed_at"], row["subject_id"])))


def observed_supportive_care(state: WorldState, observer_id: str,
                            subject_id: str) -> dict[str, object] | None:
    """Present-tense sighting of actual scheduled care, not its diagnosis.

    A trusted RecoveryStarted event has created a paid, active supportive
    care process. The observing NPC must have separately looked at both the
    caregiver and recipient at this site this tick. No injury ID, severity,
    treatment amount or outcome is disclosed.
    """
    if type(state) is not WorldState:
        raise ValueError("validated WorldState required")
    if (type(observer_id) is not str or type(subject_id) is not str
            or observer_id == subject_id or observer_id not in state.npcs
            or subject_id not in state.npcs):
        return None
    site = state.entities[observer_id]["location_id"]
    raw = state.to_dict()
    if not _present(raw, observer_id, site):
        return None
    sight = state.observations.get(observer_id, {}).get(site)
    if (sight is None or sight["at"] != state.time
            or observer_id not in sight["occupants"]
            or subject_id not in sight["occupants"]):
        return None
    for care in state.treatments.values():
        caregiver = care["caregiver_id"]
        if (care["subject_id"] != subject_id or caregiver == observer_id
                or care["site_id"] != site or care["status"] != "pending"
                or not care["started_at"] <= state.time < care["due_at"]
                or caregiver not in sight["occupants"]
                or not _present(raw, subject_id, site)
                or not _present(raw, caregiver, site)):
            continue
        return {
            "subject_id": subject_id,
            "caregiver_id": caregiver,
            "sign": "visible_supportive_care",
            "site_id": site,
            "observed_at": state.time,
            "medical_conclusion": None,
        }
    return None
