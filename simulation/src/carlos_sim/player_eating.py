"""PLAY-13: explicit one-unit consumption of genuinely owned player food.

Neither nutrition/hunger nor HP/ST/MP changes are justified by this event.
A recorded physical meal is not a medical or motivational assertion.
"""
from __future__ import annotations

import json
from typing import Any
from .domain import DomainEvent, WorldState
from .movement import _in_transit

EDIBLE = frozenset(("food", "bread"))


def project_player_food_eaten(state: dict[str, Any], event: DomainEvent, *,
                              bootstrap: bool, consumption_authorized: bool) -> None:
    """Burn exactly one owned physical food unit, with strict actor/capability."""
    if (bootstrap or not consumption_authorized
            or set(event.data) != {"resource", "quantity"}):
        raise ValueError("player eating requires dedicated trusted consumption authority")
    who = event.actor_id
    item, quantity = event.data["resource"], event.data["quantity"]
    if (not isinstance(who, str) or who not in state["entities"]
            or state["entities"][who]["controller"] != "player"
            or type(item) is not str or item not in EDIBLE
            or type(quantity) is not int or quantity != 1):
        raise ValueError("only a real player may eat exactly one owned food or bread")
    if _in_transit(state, who):
        raise ValueError("cannot eat while travelling")
    if any(s["payload"].get("__player_forage", {}).get("player_id") == who
           for s in state["scheduled"].values()):
        raise ValueError("cannot eat while busy foraging")
    balance = state["resources"].get(who, {}).get(item)
    if type(balance) is not int or balance < 1:
        raise ValueError("eating requires positive initialized player ownership")
    state["resources"][who][item] = balance - 1
    from .player_needs import apply_player_meal
    apply_player_meal(state, who)


def player_meal_history(store, state: WorldState, player_id: str,
                        limit: int) -> dict[str, Any]:
    """Verified personal food expenditure; never reads NPC meals or private needs."""
    checked = store.verify(state.world_id)
    if checked.revision != state.revision:
        raise RuntimeError("world changed while reading player meal history")
    total = 0
    recent: list[dict[str, Any]] = []
    for (raw,) in store.db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq DESC",
            (state.world_id,)):
        obj = json.loads(raw)
        if (obj.get("event_type") != "PlayerFoodEaten"
                or obj.get("actor_id") != player_id):
            continue
        event = DomainEvent.from_dict(obj)
        total += 1
        if len(recent) < limit:
            recent.append({"resource": event.data["resource"],
                           "quantity": 1, "consumed_at": event.time})
    return {"total": total, "recent": tuple(recent)}
