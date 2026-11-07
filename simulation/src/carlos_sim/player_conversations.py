"""PLAY-09: firsthand record of the player's completed NPC interactions.

Only player-authored speech and the NPC's *recorded reaction category* cross
the narration boundary. No hidden trust, third-party speech, unknown motives
or invented NPC dialogue can enter this projection.
"""
from __future__ import annotations

import json
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore


def player_conversation_history(store: SQLiteEventStore, state: WorldState,
                                player_id: str, limit: int) -> dict[str, Any]:
    """Verified completed conversations, newest event sequence first."""
    verified = store.verify(state.world_id)
    if verified.revision != state.revision:
        raise RuntimeError("world changed while reading player conversations")

    recent: list[dict[str, Any]] = []
    total = 0
    for (raw,) in store.db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq DESC",
            (state.world_id,)):
        event_obj = json.loads(raw)
        if (event_obj.get("event_type") != "SocialMessageSent"
                or event_obj.get("actor_id") != player_id):
            continue
        event = DomainEvent.from_dict(event_obj)
        message_id = event.data["id"]
        saved = state.social_messages.get(message_id)
        if (saved is None or saved["sender"] != player_id
                or saved["status"] != "received"):
            continue
        total += 1
        if len(recent) < limit:
            recent.append({
                "recipient_id": saved["recipient"],
                "kind": saved["kind"],
                "text": saved["text"],
                "reaction": saved["reaction"],
                "spoken_at": saved["sent_at"],
            })
    return {"total": total, "recent": tuple(recent)}
