"""PLAY-46 physical two-material market with a genuine repair-industry buyer.

A scripted integration *test* drives trusted APIs; there is no claim this is
autonomous coal-shopping NPC AI. All real movement, ownership and cash
transfers pass the normal reducer checks and survive SQLite replay.
"""
from __future__ import annotations

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.market import NPCMarketService
from carlos_sim.movement import NPCMovementService
from carlos_sim.production import NPCProductionService
from carlos_sim.workshop_transfers import NPCWorkshopService

WORLD = "play46-physical-smelting"
FORGE, MINE, KILN = "smithy", "iron_mine", "charcoal_kiln"
SMITH, MINER, BURNER, CUSTOMER = "smith", "miner", "burner", "mechanic"


def _e(kind, data):
    return DomainEvent(kind, None, "finite trusted setup", 0, data)


def _initialize(db):
    db.create_world(WORLD)
    events = [_e("LocationCreated", {"id": x, "name": x})
              for x in (FORGE, MINE, KILN)]
    for rid, a, b, sec in (
        ("smith-mine", FORGE, MINE, 30),
        ("smith-kiln", FORGE, KILN, 40),
    ):
        events.append(_e("RouteCreated", {
            "id": rid, "a": a, "b": b, "seconds": sec,
        }))
    for who, role, place in (
        (SMITH, "blacksmith", FORGE),
        (MINER, "miner", MINE),
        (BURNER, "charcoal_burner", KILN),
        (CUSTOMER, "repairer", FORGE),
    ):
        events.extend([
            _e("EntityCreated", {
                "id": who, "name": who,
                "location_id": place, "controller": "npc",
            }),
            _e("NPCConfigured", {
                "npc_id": who, "role": role,
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ])
    resources = {
        FORGE: {"iron_ore": 0, "charcoal": 0, "anvil": 1,
                "iron_fitting": 0, "coin_copper": 0},
        MINE: {"iron_ore": 1, "coin_copper": 0},
        KILN: {"charcoal": 1, "coin_copper": 0},
        SMITH: {"coin_copper": 2, "iron_ore": 0, "charcoal": 0},
        CUSTOMER: {"coin_copper": 2, "iron_fitting": 0},
    }
    for owner, owned in resources.items():
        for resource, n in owned.items():
            events.append(_e("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": n,
                "source": "initialization",
            }))
    for place, keeper in ((MINE, MINER), (KILN, BURNER), (FORGE, SMITH)):
        events.append(_e("MarketStallConfigured", {
            "site_id": place, "keeper_id": keeper,
        }))
    events.append(_e("ProductionRecipeConfigured", {
        "id": "iron-plus-fuel", "site_id": FORGE, "role": "blacksmith",
        "inputs": [
            {"resource": "iron_ore", "amount": 1},
            {"resource": "charcoal", "amount": 1},
        ],
        "output_resource": "iron_fitting", "output_amount": 1,
        "tool_resource": "anvil", "duration_seconds": 90,
        "wage_coin": 1,
    }))
    return db.append(WORLD, "physical:boot", 0, events, bootstrap=True)


def _money(state):
    return sum(owned.get("coin_copper", 0) for owned in state.resources.values())


def _leg(db, clock, movement, route, label):
    before = db.load(WORLD)
    started = movement.start(WORLD, SMITH, route, label,
                             expected_revision=before.revision)
    state = clock.advance(
        WORLD, seconds=started.due-before.time,
        command_id="physical:wait:" + label,
        expected_revision=db.load(WORLD).revision,
    ).state
    assert db.verify(WORLD).to_dict() == state.to_dict()
    assert _money(state) == 4
    return state


def test_purchased_ore_and_charcoal_cross_4_roads_and_fund_smith_wage(tmp_path):
    with SQLiteEventStore(tmp_path / "physical-chains.sqlite") as db:
        state = _initialize(db)
        assert _money(state) == 4
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            movement = NPCMovementService(db, clock)
            market = NPCMarketService(db, clock)
            workshop = NPCWorkshopService(db, clock)
            production = NPCProductionService(db, clock)
            for route, owner, seller, item, label in (
                ("smith-mine", MINE, MINER, "iron_ore", "ore"),
                ("smith-kiln", KILN, BURNER, "charcoal", "coal"),
            ):
                _leg(db, clock, movement, route, "out-" + label)
                asked = market.post(
                    WORLD, seller, owner, owner, "offer-" + label,
                    item, 1, "coin_copper", 1,
                    expected_revision=db.load(WORLD).revision,
                )
                purchase = market.buy(
                    WORLD, SMITH, "buy-" + label, "offer-" + label,
                    1, 1, expected_revision=asked.state.revision,
                )
                state = purchase.state
                assert state.resources[SMITH][item] == 1
                assert state.resources[FORGE][item] == 0
                assert _money(state) == 4
                _leg(db, clock, movement, route, "home-" + label)
                deposited = workshop.deposit(
                    WORLD, SMITH, FORGE, item, 1,
                    command_id="deliver-" + label,
                    expected_revision=db.load(WORLD).revision,
                )
                state = deposited.state
                assert state.resources[SMITH][item] == 0
                assert state.resources[FORGE][item] == 1
                assert _money(state) == 4
            assert len(state.market_trades) == 2
            produced = production.start(
                WORLD, SMITH, "iron-plus-fuel", "actual-smelting",
                expected_revision=state.revision,
            ).state
            assert produced.resources[FORGE]["iron_ore"] == 0
            assert produced.resources[FORGE]["charcoal"] == 0
            assert produced.resources[FORGE]["anvil"] == 1
            done = clock.advance(
                WORLD, seconds=90, command_id="physical:smelt",
                expected_revision=produced.revision,
            ).state
            assert done.resources[FORGE]["iron_fitting"] == 1
            quote = market.post(
                WORLD, SMITH, FORGE, FORGE, "finished-product",
                "iron_fitting", 1, "coin_copper", 2,
                expected_revision=done.revision,
            )
            bought = market.buy(
                WORLD, CUSTOMER, "repairer-purchase", "finished-product",
                1, 2, expected_revision=quote.state.revision,
            ).state
            assert bought.resources[CUSTOMER]["iron_fitting"] == 1
            assert bought.resources[FORGE]["coin_copper"] == 2
            assert _money(bought) == 4
            paid = db.append(WORLD, "physical:real-wage", bought.revision, [
                DomainEvent("ProductionWagePaid", None, "real sold output funds worker",
                            bought.time, {"job_id": "actual-smelting", "amount": 1}),
            ], production_authorized=True)
            assert paid.resources[FORGE]["coin_copper"] == 1
            assert paid.resources[SMITH]["coin_copper"] == 1
            assert _money(paid) == 4
            assert len(paid.market_trades) == 3
            assert sum(t["status"] == "arrived" for t in paid.travels.values()) == 4
            assert dict(paid.production_jobs["actual-smelting"][
                "input_after_by_resource"]) == {"iron_ore": 0, "charcoal": 0}
            assert db.verify(WORLD).to_dict() == paid.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == paid.to_dict()
        finally:
            clock.close_session(WORLD)
