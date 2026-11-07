"""Trusted, disposable CARLOS + seven independent NPCs fixture.

No canonical story data, no fictitious treasure or imported private NPC
knowledge. Time advances only when the human invokes the player gateway.
This module is solely an offline testing/demo bootstrap, not an API.
"""
from __future__ import annotations

from carlos_sim import DomainEvent, LivingWorldEngine, PlayerGateway
from carlos_sim.rpg_state import unknown_profile

WORLD = "living-demo"
PLAYER = "carlos"
PEOPLE = (
    ("basim", "square", "baker", 15, 80, 5),
    ("salma", "square", "merchant", 20, 80, 15),
    ("adel", "square", "guard", 10, 20, 85),
    ("nora", "bakery", "farmer", 75, 35, 5),
    ("huda", "bakery", "courier", 40, 50, 80),
    ("omar", "woods", "explorer", 10, 20, 95),
    ("layla", "woods", "resident", 10, 80, 5),
)


def _fixture(kind: str, payload: dict) -> DomainEvent:
    return DomainEvent(kind, None, "trusted disposable living-play fixture", 0, payload)


def setup_living_player_world(store) -> None:
    """Start a fresh world; never overwrite or migrate existing saves."""
    store.create_world(WORLD)
    events = [
        _fixture("LocationCreated", {"id": "square", "name": "Town Square"}),
        _fixture("LocationCreated", {"id": "bakery", "name": "Bakery"}),
        _fixture("LocationCreated", {"id": "woods", "name": "Woods"}),
        _fixture("RouteCreated", {"id": "square-bakery", "a": "square",
                                  "b": "bakery", "seconds": 40}),
        _fixture("RouteCreated", {"id": "square-woods", "a": "square",
                                  "b": "woods", "seconds": 50}),
        _fixture("EntityCreated", {"id": PLAYER, "name": "Carlos",
                                   "controller": "player",
                                   "location_id": "square"}),
    ]
    sample = unknown_profile()
    # Demo-only values: never read from nor write to the canonical story.
    sample["vitals"]["hp"] = {"current": 12, "max": 12}
    sample["vitals"]["st"] = {"current": 8, "max": 8}
    events.append(_fixture("PlayerRPGInitialized", {
        "player_id": PLAYER, "profile": sample,
    }))
    for who, site, role, fatigue, earn, explore in PEOPLE:
        events.extend((
            _fixture("EntityCreated", {
                "id": who, "name": who.capitalize(),
                "controller": "npc", "location_id": site,
            }),
            _fixture("NPCConfigured", {
                "npc_id": who, "role": role,
                "needs": {"fatigue": fatigue, "hunger": 20, "safety": 0},
                "goals": {"earn": earn, "explore": explore, "survive": 30},
            }),
        ))
        for counter in ("labor_units", "investigation_attempts"):
            events.append(_fixture("ResourceChanged", {
                "owner_id": who, "resource": counter, "previous": None,
                "current": 0, "source": "initialization",
            }))
    store.append(WORLD, "living-fixture", 0, events, bootstrap=True)


def living_player_gateway(store, clock) -> PlayerGateway:
    """Give the human Carlos only; every NPC remains independently controlled."""
    return PlayerGateway(
        store, clock, world_id=WORLD, player_id=PLAYER,
        engine=LivingWorldEngine(
            store, clock, navigation_enabled=True,
            social_enabled=True,
        ),
    )
