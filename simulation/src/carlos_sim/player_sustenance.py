"""PLAY-14: verified meal and local ownership evidence, not fake player vitals.

NPC hunger/fatigue is NOT applicable to the player. Likewise, an RPG ST
value is not assumed to represent caloric energy, and meals do not heal HP.
"""
from __future__ import annotations

import json
from typing import Any

from .domain import DomainEvent, WorldState

EDIBLE = ("food", "bread")


def player_sustenance_view(store, state: WorldState, player_id: str) -> dict[str, Any]:
    """Read verified player-only meal events and initialized personal food.

    No thresholds, inferred hunger percent, guesses at nutrition, NPC memory,
    remote food stocks, automatic consumption or synthetic zero balances.
    """
    if (player_id not in state.entities
            or state.entities[player_id]["controller"] != "player"):
        raise PermissionError("needs projection requires real player")
    verified = store.verify(state.world_id)
    if verified.revision != state.revision or verified.time != state.time:
        raise RuntimeError("world changed while projecting meal timing")
    most_recent: dict[str, Any] | None = None
    for (raw,) in store.db.execute(
        "SELECT payload FROM events WHERE world_id=? ORDER BY seq DESC",
        (state.world_id,),
    ):
        record = json.loads(raw)
        if (record.get("event_type") != "PlayerFoodEaten"
                or record.get("actor_id") != player_id):
            continue
        event = DomainEvent.from_dict(record)
        if event.time > state.time:
            raise RuntimeError("meal event occurs after the current world time")
        most_recent = {
            "resource": event.data["resource"],
            "consumed_at": event.time,
        }
        break
    owned = state.resources.get(player_id, {})
    result = {
        "hunger": "not_modeled",
        "physical_energy": "not_modeled",
        "rpg_stamina_link": "not_established",
        "last_meal": most_recent,
        "seconds_since_last_meal": (
            state.time - most_recent["consumed_at"]
            if most_recent is not None else None
        ),
        "owned_edible": {
            kind: owned.get(kind)
            if type(owned.get(kind)) is int else None
            for kind in EDIBLE
        },
    }
    return result
