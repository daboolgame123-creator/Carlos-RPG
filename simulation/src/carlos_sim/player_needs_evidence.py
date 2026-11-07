"""PLAY-14: evidence-only player nutrition/energy boundary.

The model does NOT implement player hunger, satiety, starvation, sleep or
stamina restoration. It exposes historical elapsed time since the player's
own last verified meal and an already-existing RPG ST value (when known).
No custom rates, physiological assumptions or magical healing.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .domain import WorldState
from .player_foraging import player_forage_signal
from .movement import _in_transit


def personal_needs_evidence(state: WorldState, player_id: str,
                            meal_history: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic read-only projection, never remote stock/NPC state."""
    own = state.entities.get(player_id)
    if own is None or own['controller'] != 'player':
        raise PermissionError('personal needs evidence belongs to an actual player')
    if (not isinstance(meal_history, Mapping)
            or type(meal_history.get("total")) is not int
            or meal_history["total"] < 0
            or not isinstance(meal_history.get("recent"), (tuple, list))
            or len(meal_history["recent"]) > 1
            or (meal_history["total"] == 0 and meal_history["recent"])
            or (meal_history["total"] > 0 and len(meal_history["recent"]) != 1)):
        raise ValueError('invalid verified meal history input')
    meal = meal_history["recent"][0] if meal_history["recent"] else None
    last = None if meal is None else meal.get("consumed_at")
    if last is not None and (type(last) is not int or last < 0 or last > state.time):
        raise ValueError('invalid latest player meal time')
    profile = state.rpg_profiles.get(player_id)
    st = (profile.get("vitals", {}).get("st") if profile is not None else None)
    # RPG status is a separate, already validated source; never imply ST
    # tracks biological fatigue or that a meal changed it.
    energy = ({'mode': 'unknown', 'st': None} if st is None
              else {'mode': 'rpg_st_only', 'st': {
                  'current': st['current'], 'max': st['max']}})
    travel = _in_transit(state.to_dict(), player_id)
    foraging = player_forage_signal(state, player_id)
    activity = ('traveling' if travel else 'foraging' if foraging else 'available')
    return {
        'hunger': {'mode': 'not_modeled',
                   'last_verified_meal_at': last,
                   'seconds_since_last_verified_meal': (
                       None if last is None else state.time - last)},
        'energy': energy,
        'activity': activity,
    }
