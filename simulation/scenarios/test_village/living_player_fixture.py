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


def setup_living_player_world(store, *, npc_initial_hunger: int = 20) -> None:
    """Start a fresh world; never overwrite or migrate existing saves."""
    if type(npc_initial_hunger) is not int or not 0 <= npc_initial_hunger <= 100:
        raise ValueError("demo NPC hunger must be an integer from 0 to 100")
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
                "needs": {"fatigue": fatigue, "hunger": npc_initial_hunger, "safety": 0},
                "goals": {"earn": earn, "explore": explore, "survive": 30},
            }),
        ))
        for counter in ("labor_units", "investigation_attempts"):
            events.append(_fixture("ResourceChanged", {
                "owner_id": who, "resource": counter, "previous": None,
                "current": 0, "source": "initialization",
            }))
    store.append(WORLD, "living-fixture", 0, events, bootstrap=True)


def living_player_gateway(store, clock, *, npc_survival_demo: bool = False,
                          npc_ecology_demo: bool = False) -> PlayerGateway:
    """Human-controlled Carlos; opt-in survival/food ecology from marked worlds.

    Existing PLAY-15/20 survival mode remains identical when ecology is off.
    Ecology combines already-existing NPC policies, never player RPG health.
    """
    if type(npc_survival_demo) is not bool:
        raise ValueError("npc_survival_demo must be a boolean")
    if npc_survival_demo != is_living_npc_survival_world(store):
        raise ValueError("NPC survival mode must match the dedicated world bootstrap")
    if type(npc_ecology_demo) is not bool:
        raise ValueError("npc_ecology_demo must be a boolean")
    if npc_ecology_demo != is_living_npc_ecology_world(store):
        raise ValueError("NPC ecology mode must match the dedicated world bootstrap")
    if npc_ecology_demo and not npc_survival_demo:
        raise ValueError("NPC ecology requires the survival mode")
    return PlayerGateway(
        store, clock, world_id=WORLD, player_id=PLAYER,
        engine=LivingWorldEngine(
            store, clock, navigation_enabled=True,
            social_enabled=True,
            consumption_enabled=npc_survival_demo,
            survival_enabled=npc_survival_demo,
            gathering_enabled=npc_ecology_demo,
            foraging_enabled=npc_ecology_demo,
            knowledge_enabled=npc_ecology_demo,
            food_navigation_enabled=npc_ecology_demo,
            scarcity_enabled=npc_ecology_demo,
            assistance_enabled=npc_ecology_demo,
        ),
    )


def setup_living_market_world(store, *, npc_initial_hunger: int = 20) -> None:
    """Opt-in, disposable physical market; preserve original plain fixture.

    Salma initially OWNS three test loaves, Carlos ten copper coins,
    and both ends of the atomic exchange have initialized zero balances.
    Nothing is minted when the player buys, and nobody receives free wages
    from an autonomous 'work' counter. This is not RPG equipment.
    """
    from carlos_sim import NPCMarketService, TimeEngine
    setup_living_player_world(store, npc_initial_hunger=npc_initial_hunger)
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



def setup_living_foraging_world(store, *, npc_initial_hunger: int = 20) -> None:
    """PLAY-11 opt-in: food initially owned by Carlos is verified zero.

    Keep the original plain/market fixtures and their unknown balances intact.
    """
    setup_living_market_world(store, npc_initial_hunger=npc_initial_hunger)
    current = store.load(WORLD)
    store.append(WORLD, "living-forage-initialize-owned-food",
                 current.revision, [_fixture("ResourceChanged", {
        "owner_id": PLAYER, "resource": "food", "previous": None,
        "current": 0, "source": "initialization",
    })], bootstrap=True)



def setup_living_npc_survival_world(store) -> None:
    """PLAY-15 opt-in real NPC feeding, separate from earlier fixtures.

    Pre-existing NPC hunger rules start at 80 only in this disposable mode.
    Two NPCs legitimately start with one owned food unit each; the other
    five have explicit zero. No NPC may borrow Carlos's stock or steal it.
    """
    setup_living_foraging_world(store, npc_initial_hunger=80)
    assets = tuple((npc_id, 1 if npc_id in ("basim", "nora") else 0)
                   for npc_id, *_ in PEOPLE)
    current = store.load(WORLD)
    store.append(WORLD, "living-survival-owned-npc-food", current.revision,
                 [_fixture("ResourceChanged", {
                     "owner_id": npc, "resource": "food", "previous": None,
                     "current": amount, "source": "initialization",
                 }) for npc, amount in assets], bootstrap=True)


def is_living_npc_survival_world(store) -> bool:
    """Persistent exact fixture marker; opt-in never inferred from NPC stock."""
    return store.db.execute(
        "SELECT 1 FROM commands WHERE world_id=? AND command_id=?",
        (WORLD, "living-survival-owned-npc-food"),
    ).fetchone() is not None


def setup_living_npc_ecology_world(store) -> None:
    """PLAY-21 experimental food ecology, separate from PLAY-15/20 worlds.

    Bakery has an explicit EMPTY natural-food deposit, not an unknown balance.
    The unique bootstrap command is the durable, test-only ecology mode marker.
    No new food or copper is added, and old fixture modes are unaffected.
    """
    setup_living_npc_survival_world(store)
    state = store.load(WORLD)
    store.append(WORLD, "living-ecology-bakery-empty-food", state.revision,
                 [_fixture("ResourceChanged", {
                     "owner_id": "bakery", "resource": "wild_food",
                     "previous": None, "current": 0,
                     "source": "initialization",
                 })], bootstrap=True)


def is_living_npc_ecology_world(store) -> bool:
    return store.db.execute(
        "SELECT 1 FROM commands WHERE world_id=? AND command_id=?",
        (WORLD, "living-ecology-bakery-empty-food"),
    ).fetchone() is not None
