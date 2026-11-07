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


def setup_living_market_world(store) -> None:
    """Opt-in, disposable physical market; preserve original plain fixture.

    Salma initially OWNS three test loaves, Carlos ten copper coins,
    and both ends of the atomic exchange have initialized zero balances.
    Nothing is minted when the player buys, and nobody receives free wages
    from an autonomous 'work' counter. This is not RPG equipment.
    """
    from carlos_sim import NPCMarketService, TimeEngine
    setup_living_player_world(store)
    state = store.load(WORLD)
    assets = (
        (PLAYER, "coin_copper", 10), (PLAYER, "bread", 0),
        ("salma", "coin_copper", 0), ("salma", "bread", 3),
        # Finite TEST-ONLY world resources, not player inventory or free food.
        ("square", "wild_food", 2), ("woods", "wild_food", 4),
    )
    store.append(WORLD, "living-market-initial-balances", state.revision, [
        _fixture("ResourceChanged", {
            "owner_id": owner, "resource": item, "previous": None,
            "current": qty, "source": "initialization",
        }) for owner, item, qty in assets
    ], bootstrap=True)
    clock = TimeEngine(store)
    clock.open_session(WORLD)
    try:
        # Verified firsthand sightings, not fabricated omniscience. Basim
        # observes only square; Omar observes only woods. Salma knows neither.
        from carlos_sim.knowledge import make_observation_events
        current = store.load(WORLD)
        sightings = (
            make_observation_events(current, "basim", "square", current.time,
                                    "demo-10-square")
            + make_observation_events(current, "omar", "woods", current.time,
                                      "demo-10-woods")
        )
        store.append(WORLD, "living-market-true-food-sightings",
                     current.revision, sightings, npc_authorized=True)
        NPCMarketService(store, clock).post(
            WORLD, "salma", "salma", "square", "salma-bread",
            "bread", 3, "coin_copper", 2,
            expected_revision=store.load(WORLD).revision)
    finally:
        clock.close_session(WORLD)



def setup_living_foraging_world(store) -> None:
    """PLAY-11 opt-in: food initially owned by Carlos is verified zero.

    Keep the original plain/market fixtures and their unknown balances intact.
    """
    setup_living_market_world(store)
    current = store.load(WORLD)
    store.append(WORLD, "living-forage-initialize-owned-food",
                 current.revision, [_fixture("ResourceChanged", {
        "owner_id": PLAYER, "resource": "food", "previous": None,
        "current": 0, "source": "initialization",
    })], bootstrap=True)
