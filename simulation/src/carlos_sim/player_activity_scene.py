"""PLAY-04: bounded, read-only physical activities in Carlos's current scene.

Current physical presence at the same site is necessary; a distant action,
historical sighting, internal intention, health record, job reservation or
clock time alone cannot leak a private NPC fact to the player. This file
emits only qualitatively visible *ongoing* behavior, never medical causes.
No event is written, and no story/canonical-save state is modified.
"""
from __future__ import annotations

from .domain import WorldState
from .movement import _in_transit, _visible


VISIBLE_ACTIONS = {
    "rest": "resting",
    "work": "working",
    "forage": "foraging",
}


def visible_player_activities(state: WorldState, player_id: str) -> tuple[dict[str, str], ...]:
    """Return only actions physically visible to this player at this instant.

    A record here is not historical player memory. It must not expose action
    identifiers, exact start/due ticks, goals, location-inaccessible actors,
    inventory, private injury, recipes or the reason an NPC acts.
    """
    if type(state) is not WorldState:
        raise ValueError("validated WorldState required")
    if (type(player_id) is not str or player_id not in state.entities
            or state.entities[player_id]["controller"] != "player"):
        raise ValueError("existing human-controlled player required")

    snapshot = state.to_dict()
    if _in_transit(snapshot, player_id):
        return ()
    place = state.entities[player_id]["location_id"]
    nearby = set(_visible(snapshot, place))
    nearby.intersection_update(state.npcs)
    if not nearby:
        return ()

    visible: dict[str, str] = {}
    for action in state.actions.values():
        who = action["npc_id"]
        kind = VISIBLE_ACTIONS.get(action["action"])
        if (who in nearby and kind is not None
                and action["status"] == "running"
                and action["start"] <= state.time < action["due"]):
            visible[who] = kind

    # Production is a distinct physical lifecycle: never reveal its recipe,
    # input stock, job ID, tools, assigned wages or scheduled completion.
    for job in state.production_jobs.values():
        who = job["npc_id"]
        if (who in nearby and job["status"] == "running"
                and job["site_id"] == place):
            visible[who] = "producing"

    return tuple({"actor_id":who, "activity":visible[who]}
                 for who in sorted(visible))
