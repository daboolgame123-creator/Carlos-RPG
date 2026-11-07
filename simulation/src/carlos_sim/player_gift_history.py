"""PLAY-08: verified, read-only history of actual human-player gifts.

A gift receipt describes only a completed event that the donor performed.
It does not establish gratitude, NPC motives, hunger/medical changes, or
ownership of unrelated resources. Event order, not wall-clock order, governs
ties in the logical simulation tick.
"""
from __future__ import annotations

import json
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore


def player_gift_receipts(store: SQLiteEventStore, state: WorldState,
                         player_id: str, limit: int) -> dict[str, Any]:
    """Read verified accepted events; never project other actors' private state."""
    verified = store.verify(state.world_id)
    if verified.revision != state.revision:
        raise RuntimeError("world changed while reading player gift history")

    recent: list[dict[str, Any]] = []
    total = 0
    # DESC seq is the durable order, even when several gifts share one tick.
    for (raw,) in store.db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq DESC",
            (state.world_id,)):
        obj = json.loads(raw)
        if (obj.get("event_type") != "PlayerGiftDelivered"
                or obj.get("actor_id") != player_id):
            continue
        event = DomainEvent.from_dict(obj)
        total += 1
        if len(recent) < limit:
            recent.append({
                "recipient_id": event.data["recipient_id"],
                "resource": event.data["resource"],
                "quantity": event.data["quantity"],
                "delivered_at": event.time,
            })
    return {"total": total, "recent": tuple(recent)}
