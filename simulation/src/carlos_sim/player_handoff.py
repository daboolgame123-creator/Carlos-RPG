"""Copyable, read-only player-visible handoff for an offline disposable demo.

The trusted PlayerGateway is the only source: do not pass a WorldState,
raw NPC memory, inventory ledger, event log, or server/database capability
to a narrator. This is NOT an authorization boundary for untrusted HTTP
clients, and this envelope never makes the demo Carlos's canonical story.
"""
from __future__ import annotations

from .player_gateway import PlayerCommandResult, PlayerGateway


def player_handoff(gateway: PlayerGateway) -> dict[str, object]:
    """Project only the human player's current scene, status and earned memory.

    A coherent (world/time/revision) triple is essential: an observer must
    not receive a stitched story assembled from several changing worlds.
    No world time advances and no event or command is appended here.
    """
    if type(gateway) is not PlayerGateway:
        raise TypeError("trusted local PlayerGateway required")
    scene = gateway.inspect()
    status = gateway.status()
    memory = gateway.recall()
    supplies = gateway.supplies()
    purchases = gateway.purchases(limit=5)
    gifts = gateway.gifts(limit=5)
    if not all(type(row) is PlayerCommandResult for row in (scene, status, memory, supplies, purchases, gifts)):
        raise ValueError("invalid player projection")
    versions = {(row.world_id, row.time, row.revision)
                for row in (scene, status, memory, supplies, purchases, gifts)}
    if len(versions) != 1:
        raise RuntimeError("player view changed during handoff")
    if (scene.status not in ("present", "traveling")
            or status.status not in ("rpg_status", "rpg_uninitialized")
            or memory.status != "memory"
            or supplies.status != "supplies"
            or purchases.status != "purchases"
            or gifts.status != "gifts"):
        raise ValueError("unexpected player view")
    return {
        "format": "carlos-player-handoff-v1",
        "disposable_test": True,
        "canonical_story": False,
        "world_id": scene.world_id,
        "time": scene.time,
        "revision": scene.revision,
        "scene": {"status": scene.status, "details": scene.details},
        "player_status": {"status": status.status, "details": status.details},
        "player_memory": memory.details,
        "player_supplies": supplies.details,
        "player_purchases": purchases.details,
        "player_gifts": gifts.details,
    }
