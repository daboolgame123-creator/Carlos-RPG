"""WORLD-01b: the player sources and physically delivers blacksmith inputs."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, NPCMarketService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import DuplicateCommand, InvalidEvent

WORLD = "world01b-player-physical-forge"
PLAYER = "carlos"
FORGE = "smithy"
MINE = "iron_mine"
KILN = "charcoal_kiln"
MINER = "iron_miner"
BURNER = "charcoal_burner"
RECIPE = "carlos-iron-fitting"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01b disposable test setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        *[_event("LocationCreated", {"id": place, "name": place})
          for place in ("home", FORGE, MINE, KILN)],
        *[_event("RouteCreated", {
            "id": route, "a": start, "b": end, "seconds": duration,
        }) for route, start, end, duration in (
            ("home-smithy", "home", FORGE, 60),
            ("smithy-mine", FORGE, MINE, 30),
            ("smithy-kiln", FORGE, KILN, 40),
        )],
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": "home",
            "controller": "player",
        }),
    ]
    for npc, name, site, role in (
        (MINER, "Miner", MINE, "miner"),
        (BURNER, "Charcoal burner", KILN, "charcoal_burner"),
    ):
        events.extend((
            _event("EntityCreated", {
                "id": npc, "name": name, "location_id": site,
                "controller": "npc",
            }),
            _event("NPCConfigured", {
                "npc_id": npc, "role": role,
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ))
    for owner, stock in (
        (PLAYER, {"coin_copper": 4, "iron_ore": 0, "charcoal": 0}),
        (FORGE, {"coin_copper": 1, "iron_ore": 0, "charcoal": 0,
                 "anvil": 1, "iron_fitting": 0}),
        (MINE, {"coin_copper": 0, "iron_ore": 1}),
        (KILN, {"coin_copper": 0, "charcoal": 1}),
    ):
        for resource, quantity in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))
    events.extend((
        _event("MarketStallConfigured", {
            "site_id": MINE, "keeper_id": MINER,
        }),
        _event("MarketStallConfigured", {
            "site_id": KILN, "keeper_id": BURNER,
        }),
        _event("ProductionRecipeConfigured", {
            "id": RECIPE, "site_id": FORGE, "role": "blacksmith",
            "inputs": [
                {"resource": "iron_ore", "amount": 1},
                {"resource": "charcoal", "amount": 1},
            ],
            "output_resource": "iron_fitting", "output_amount": 1,
            "tool_resource": "anvil", "duration_seconds": 90,
            "wage_coin": 1, "player_worker_id": PLAYER,
        }),
    ))
    store.append(WORLD, "world01b:bootstrap", 0, events, bootstrap=True)


def _gateway(store: SQLiteEventStore, clock: TimeEngine) -> PlayerGateway:
    # This focused scenario advances only explicit routes and production due
    # signals; autonomous NPC policies are outside WORLD-01b's acceptance.
    return PlayerGateway(store, clock, world_id=WORLD, player_id=PLAYER)


def _travel(db, clock, gateway, route: str, seconds: int, label: str,
            destination: str) -> None:
    before = db.verify(WORLD)
    trip = gateway.move(route, command_id=label + "-depart",
                        expected_revision=before.revision)
    assert trip.status == "traveling"
    arrived = clock.advance(
        WORLD, seconds=seconds, command_id=label + "-arrive",
        expected_revision=trip.revision,
    ).state
    assert arrived.time == before.time + seconds
    assert db.verify(WORLD).entities[PLAYER]["location_id"] == destination


def _post_and_buy(db, clock, gateway, seller: str, site: str, item: str,
                  offer: str, label: str):
    market = NPCMarketService(db, clock)
    posted = market.post(
        WORLD, seller, site, site, offer, item, 1, "coin_copper", 1,
        expected_revision=db.load(WORLD).revision,
    )
    quotes = gateway.offers().details["offers"]
    assert quotes == ({
        "offer_id": offer, "seller_id": seller, "resource": item,
        "available": 1, "payment_resource": "coin_copper", "unit_price": 1,
    },)
    receipt = gateway.buy(
        offer, 1, 1, command_id="buy-" + label,
        expected_revision=posted.state.revision,
    )
    assert receipt.details["resource"] == item
    assert receipt.details["quantity"] == 1
    assert receipt.details["total_paid"] == 1
    return receipt


def _copper(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def test_player_buys_and_delivers_real_ore_and_charcoal_before_work(tmp_path):
    database = tmp_path / "world01b-physical-forge.sqlite"
    with SQLiteEventStore(database) as db:
        _seed(db)
        opening = db.verify(WORLD)
        assert opening.resources[MINE]["iron_ore"] == 1
        assert opening.resources[KILN]["charcoal"] == 1
        assert opening.resources[FORGE]["iron_ore"] == 0
        assert opening.resources[FORGE]["charcoal"] == 0
        assert _copper(opening) == 5

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        gateway = _gateway(db, clock)
        try:
            with pytest.raises(ValueError, match="contracted worksite"):
                gateway.deposit_material(
                    RECIPE, "iron_ore", 1, command_id="before-travel",
                    expected_revision=opening.revision,
                )
            assert db.verify(WORLD).to_dict() == opening.to_dict()

            _travel(db, clock, gateway, "home-smithy", 60, "to-forge", FORGE)
            _travel(db, clock, gateway, "smithy-mine", 30, "to-mine", MINE)
            _post_and_buy(db, clock, gateway, MINER, MINE, "iron_ore",
                          "mine-ore", "ore")
            bought_ore = db.verify(WORLD)
            assert bought_ore.resources[PLAYER]["iron_ore"] == 1
            assert bought_ore.resources[FORGE]["iron_ore"] == 0
            assert bought_ore.resources[MINE]["iron_ore"] == 0
            assert bought_ore.resources[MINE]["coin_copper"] == 1
            assert _copper(bought_ore) == 5

            with pytest.raises(ValueError, match="contracted worksite"):
                gateway.deposit_material(
                    RECIPE, "iron_ore", 1, command_id="deposit-at-mine",
                    expected_revision=bought_ore.revision,
                )
            assert db.verify(WORLD).to_dict() == bought_ore.to_dict()

            trip = gateway.move(
                "smithy-mine", command_id="return-from-mine",
                expected_revision=bought_ore.revision,
            )
            mid_trip = clock.advance(
                WORLD, seconds=10, command_id="mine-road-first-10",
                expected_revision=trip.revision,
            ).state
            with pytest.raises(ValueError, match="while travelling"):
                gateway.deposit_material(
                    RECIPE, "iron_ore", 1, command_id="deposit-in-transit",
                    expected_revision=mid_trip.revision,
                )
            assert db.verify(WORLD).to_dict() == mid_trip.to_dict()
            clock.advance(
                WORLD, seconds=20, command_id="mine-road-last-20",
                expected_revision=mid_trip.revision,
            )
            at_forge = db.verify(WORLD)
            assert at_forge.entities[PLAYER]["location_id"] == FORGE
            ore_delivery = gateway.deposit_material(
                RECIPE, "iron_ore", 1, command_id="deliver-ore",
                expected_revision=at_forge.revision,
            )
            assert ore_delivery.status == "material_deposited"
            assert db.verify(WORLD).resources[PLAYER]["iron_ore"] == 0
            assert db.verify(WORLD).resources[FORGE]["iron_ore"] == 1
            delivered_ore = db.verify(WORLD)
            with pytest.raises(InvalidEvent, match="insufficient"):
                gateway.deposit_material(
                    RECIPE, "iron_ore", 1, command_id="deliver-unowned-ore",
                    expected_revision=delivered_ore.revision,
                )
            assert db.verify(WORLD).to_dict() == delivered_ore.to_dict()
            with pytest.raises(DuplicateCommand):
                gateway.deposit_material(
                    RECIPE, "iron_ore", 1, command_id="deliver-ore",
                    expected_revision=delivered_ore.revision,
                )
            assert db.verify(WORLD).to_dict() == delivered_ore.to_dict()

            _travel(db, clock, gateway, "smithy-kiln", 40, "to-kiln", KILN)
            _post_and_buy(db, clock, gateway, BURNER, KILN, "charcoal",
                          "kiln-charcoal", "charcoal")
            bought_charcoal = db.verify(WORLD)
            assert bought_charcoal.resources[PLAYER]["charcoal"] == 1
            assert bought_charcoal.resources[FORGE]["charcoal"] == 0
            assert bought_charcoal.resources[KILN]["charcoal"] == 0
            assert bought_charcoal.resources[KILN]["coin_copper"] == 1
            assert len(bought_charcoal.market_trades) == 2
            assert _copper(bought_charcoal) == 5
            _travel(db, clock, gateway, "smithy-kiln", 40, "from-kiln", FORGE)

            forge_arrival = db.verify(WORLD)
            with pytest.raises(ValueError, match="not an input"):
                gateway.deposit_material(
                    RECIPE, "anvil", 1, command_id="deposit-tool-as-input",
                    expected_revision=forge_arrival.revision,
                )
            assert db.verify(WORLD).to_dict() == forge_arrival.to_dict()
            gateway.deposit_material(
                RECIPE, "charcoal", 1, command_id="deliver-charcoal",
                expected_revision=forge_arrival.revision,
            )
            ready = db.verify(WORLD)
            assert ready.resources[PLAYER]["charcoal"] == 0
            assert ready.resources[FORGE]["iron_ore"] == 1
            assert ready.resources[FORGE]["charcoal"] == 1
            assert _copper(ready) == 5

            started = gateway.work(
                RECIPE, command_id="smelt-one-fitting",
                expected_revision=ready.revision,
            )
            running = db.verify(WORLD)
            assert running.resources[FORGE]["iron_ore"] == 0
            assert running.resources[FORGE]["charcoal"] == 0
            assert running.resources[FORGE]["anvil"] == 1
            with pytest.raises(ValueError, match="busy working"):
                gateway.deposit_material(
                    RECIPE, "iron_ore", 1, command_id="deposit-during-work",
                    expected_revision=running.revision,
                )
            assert db.verify(WORLD).to_dict() == running.to_dict()

            completed = clock.advance(
                WORLD, seconds=90, command_id="finish-smelting",
                expected_revision=started.revision,
            ).state
            assert completed.time == 290
            job_id = started.details["job_id"]
            assert completed.production_jobs[job_id]["status"] == "completed"
            final = db.append(WORLD, "world01b:pay-player-wage",
                              completed.revision, [DomainEvent(
                "ProductionWagePaid", None,
                "funded wage for completed player-contracted work",
                completed.time, {"job_id": job_id, "amount": 1},
            )], production_authorized=True)
            job = final.production_jobs[job_id]
            assert job["status"] == "completed"
            assert job["output_after"] == 1
            assert job["work_wage"]["amount"] == 1
            assert final.resources[FORGE]["iron_fitting"] == 1
            assert final.resources[PLAYER]["coin_copper"] == 3
            assert final.resources[FORGE]["coin_copper"] == 0
            assert _copper(final) == 5
            assert final.entities[PLAYER]["location_id"] == FORGE
            assert db.verify(WORLD).to_dict() == final.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == final.to_dict()


def test_player_deposit_requires_its_signed_contract_and_rejects_wrong_controller(
        tmp_path):
    with SQLiteEventStore(tmp_path / "world01b-contract.sqlite") as db:
        _seed(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            gateway = _gateway(db, clock)
            before = db.verify(WORLD)
            with pytest.raises(PermissionError, match="signed contract"):
                gateway.deposit_material(
                    "unknown-job", "iron_ore", 1, command_id="unknown-job",
                    expected_revision=before.revision,
                )
            npc_gateway = PlayerGateway(
                db, clock, world_id=WORLD, player_id=MINER,
            )
            with pytest.raises(PermissionError, match="player-controlled"):
                npc_gateway.deposit_material(
                    RECIPE, "iron_ore", 1, command_id="npc-impersonation",
                    expected_revision=before.revision,
                )
            assert db.verify(WORLD).to_dict() == before.to_dict()
        finally:
            clock.close_session(WORLD)
