"""PLAY-04/17: grounded, local, qualitative NPC activity projection.

A read-only present scene does not itself create a memory. PLAY-17 reuses
this exact physical projection to validate deliberately recorded sightings.
No private activity motives, action IDs, recipes, medical diagnoses or
unseen travel destinations cross the player boundary.
"""
from __future__ import annotations

from typing import Any

from .domain import WorldState
from .movement import _in_transit, _visible


VISIBLE_ACTIONS = {
    "rest": "resting",
    "work": "working",
    "forage": "foraging",
}


def visible_activity_rows(snapshot: dict[str, Any],
                          player_id: str) -> tuple[dict[str, str], ...]:
    """Internal pure physical projection shared by scene and event validator.

    `snapshot` is a trusted WorldState.to_dict() or the transient projection
    within apply_event. Never expose this function directly to an untrusted
    network client, whose requested identity must be authenticated separately.
    """
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("entities"), dict):
        raise ValueError("validated world projection required")
    if (type(player_id) is not str or player_id not in snapshot["entities"]
            or snapshot["entities"][player_id]["controller"] != "player"):
        raise ValueError("existing human-controlled player required")
    if _in_transit(snapshot, player_id):
        return ()

    place = snapshot["entities"][player_id]["location_id"]
    nearby = set(_visible(snapshot, place)) & set(snapshot["npcs"])
    if not nearby:
        return ()

    visible: dict[str, str] = {}
    for action in snapshot["actions"].values():
        who = action["npc_id"]
        kind = VISIBLE_ACTIONS.get(action["action"])
        if (who in nearby and kind is not None
                and action["status"] == "running"
                and action["start"] <= snapshot["time"] < action["due"]):
            visible[who] = kind

    # Production is a separate physically visible lifecycle. Never expose
    # the recipe, internal stock, wage, assignment or due timestamp.
    for job in snapshot["production_jobs"].values():
        who = job["npc_id"]
        if (who in nearby and job["status"] == "running"
                and job["site_id"] == place):
            visible[who] = "producing"

    return tuple({"actor_id": who, "activity": visible[who]}
                 for who in sorted(visible))


def visible_player_activities(state: WorldState,
                              player_id: str) -> tuple[dict[str, str], ...]:
    """Return currently observable activities with no side effects or memory."""
    if type(state) is not WorldState:
        raise ValueError("validated WorldState required")
    return visible_activity_rows(state.to_dict(), player_id)
