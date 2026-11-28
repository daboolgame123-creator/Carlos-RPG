"""WORLD-01g: player-mined ore reaches Carlos's funded forge contract."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCMarketService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION
from carlos_sim.store import InvalidEvent

WORLD = "world01g-player-miner-forge"
PLAYER = "carlos"
MINE_KEEPER = "mine_steward"
KILN_KEEPER = "kiln_steward"
HOME = "home"
MINE = "iron_mine"
KILN = "charcoal_kiln"
FORGE = "smithy"
MINE_RECIPE = "carlos-finite-iron-miner"
FORGE_RECIPE = "carlos-iron-fitting"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01g disposable integration setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        *[_event("LocationCreated", {"id": site, "name": site})
          for site in (HOME, MINE, KILN, FORGE)],
        *[_event("RouteCreated", {
            "id": route, "a": start, "b": end, "seconds": seconds,
        }) for route, start, end, seconds in (
            ("home-mine", HOME, MINE, 60),
            ("mine-kiln", MINE, KILN, 30),
            ("kiln-forge", KILN, FORGE, 30),
        )],
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": HOME,
            "controller": "player",
        }),
    ]
    for npc, site in ((MINE_KEEPER, MINE), (KILN_KEEPER, KILN)):
        events.extend((
            _event("EntityCreated", {
                "id": npc, "name": npc, "location_id": site,
                "controller": "npc",
            }),
            _event("NPCConfigured", {
                "npc_id": npc, "role": "merchant",
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ))

    # The only opening copper is explicitly assigned to Carlos, the mine wage,
    # and the forge wage. Ore comes from one reserve; charcoal is a declared
    # kiln stock already produced outside this bounded integration test.
    for owner, stock in (
        (PLAYER, {"coin_copper": 2, "iron_ore": 0, "charcoal": 0}),
        (MINE, {"iron_ore_reserve": 1, "iron_ore": 0,
                "pickaxe": 1, "coin_copper": 1}),
        (KILN, {"charcoal": 1, "coin_copper": 0}),
        (FORGE, {"iron_ore": 0, "charcoal": 0, "iron_fitting": 0,
                 "anvil": 1, "coin_copper": 1}),
        (MINE_KEEPER, {"coin_copper": 0}),
        (KILN_KEEPER, {"coin_copper": 0}),
    ):
        for resource, quantity in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))

    events.extend((
        _event("MarketStallConfigured", {
            "site_id": MINE, "keeper_id": MINE_KEEPER,
        }),
        _event("MarketStallConfigured", {
            "site_id": KILN, "keeper_id": KILN_KEEPER,
        }),
        _event("ProductionRecipeConfigured", {
            "id": MINE_RECIPE, "site_id": MINE, "role": "miner",
            "input_resource": "iron_ore_reserve", "input_amount": 1,
            "output_resource": "iron_ore", "output_amount": 1,
            "tool_resource": "pickaxe", "duration_seconds": 120,
            "wage_coin": 1, "player_worker_id": PLAYER,
        }),
        _event("ProductionRecipeConfigured", {
            "id": FORGE_RECIPE, "site_id": FORGE, "role": "blacksmith",
            "inputs": [
                {"resource": "iron_ore", "amount": 1},
                {"resource": "charcoal", "amount": 1},
            ],
            "output_resource": "iron_fitting", "output_amount": 1,
            "tool_resource": "anvil", "duration_seconds": 90,
            "wage_coin": 1, "player_worker_id": PLAYER,
        }),
    ))
    store.append(WORLD, "world01g:bootstrap", 0, events, bootstrap=True)


def _copper_total(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _event_count(store: SQLiteEventStore) -> int:
    return store.db.execute(
        "SELECT COUNT(*) FROM events WHERE world_id=?", (WORLD,),
    ).fetchone()[0]


def _travel(db, gateway: PlayerGateway, route: str, seconds: int,
            command: str, destination: str):
    before = db.verify(WORLD)
    departure = gateway.move(
        route, command_id=command + "-depart",
        expected_revision=before.revision,
    )
    assert departure.status == "traveling"
    arrival = gateway.wait(
        seconds, command_id=command + "-arrive",
        expected_revision=departure.revision,
    )
    assert arrival.time == before.time + seconds
    state = db.verify(WORLD)
    assert state.entities[PLAYER]["location_id"] == destination
    return state


def _post_offer(db, clock, seller: str, owner: str, site: str,
                offer_id: str, resource: str):
    result = NPCMarketService(db, clock).post(
        WORLD, seller, owner, site, offer_id, resource, 1,
        "coin_copper", 1, expected_revision=db.verify(WORLD).revision,
    )
    return result.state


def test_carlos_mines_buys_and_delivers_ore_to_his_funded_forge_job(tmp_path):
    database = tmp_path / "world01g-player-miner-forge.sqlite"
    with SQLiteEventStore(database) as db:
        _seed(db)
        opening = db.verify(WORLD)
        assert opening.schema_version == SCHEMA_VERSION == 46
        assert opening.rules_version == RULES_VERSION == 73
        assert opening.entities[PLAYER]["controller"] == "player"
        assert PLAYER not in opening.npcs
        assert opening.production_jobs == {}
        assert opening.market_offers == {}
        assert opening.resources[MINE]["iron_ore_reserve"] == 1
        assert opening.resources[MINE]["iron_ore"] == 0
        assert opening.resources[KILN]["charcoal"] == 1
        assert opening.resources[FORGE]["iron_ore"] == 0
        assert opening.resources[FORGE]["charcoal"] == 0
        assert opening.resources[FORGE]["iron_fitting"] == 0
        assert opening.resources[PLAYER]["coin_copper"] == 2
        assert _copper_total(opening) == 4

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            gateway = PlayerGateway(
                db, clock, world_id=WORLD, player_id=PLAYER,
                engine=LivingWorldEngine(
                    db, clock, economic_enabled=True, agriculture_enabled=True,
                    economy_only_enabled=True, navigation_enabled=True,
                ),
            )
            with pytest.raises(ValueError, match="physically present"):
                gateway.work(
                    MINE_RECIPE, command_id="mine-before-travel",
                    expected_revision=opening.revision,
                )
            assert db.verify(WORLD).to_dict() == opening.to_dict()

            at_mine = _travel(
                db, gateway, "home-mine", 60, "to-mine", MINE,
            )
            assert at_mine.time == 60
            assert at_mine.production_jobs == {}
            assert gateway.offers().details["offers"] == ()

            started = gateway.work(
                MINE_RECIPE, command_id="start-mining",
                expected_revision=at_mine.revision,
            )
            mining = db.verify(WORLD)
            mine_job = mining.production_jobs[started.details["job_id"]]
            assert mine_job["status"] == "running"
            assert (mine_job["started_at"], mine_job["due"]) == (60, 180)
            assert mining.resources[MINE]["iron_ore_reserve"] == 0
            assert mining.resources[MINE]["iron_ore"] == 0
            assert mining.resources[MINE]["coin_copper"] == 1
            assert mining.resources[PLAYER]["coin_copper"] == 2
            assert _copper_total(mining) == 4

            gateway.wait(
                119, command_id="wait-mining-to-179",
                expected_revision=mining.revision,
            )
            almost_mined = db.verify(WORLD)
            assert almost_mined.time == 179
            assert almost_mined.production_jobs[started.details["job_id"]]["status"] == "running"
            assert almost_mined.resources[MINE]["iron_ore"] == 0
            assert almost_mined.resources[PLAYER]["coin_copper"] == 2

            gateway.wait(
                1, command_id="finish-mining",
                expected_revision=almost_mined.revision,
            )
            mined = db.verify(WORLD)
            mine_job = mined.production_jobs[started.details["job_id"]]
            assert mined.time == 180
            assert mine_job["status"] == "completed"
            assert mine_job["output_after"] == 1
            assert mine_job["work_wage"]["paid_at"] == 180
            assert mine_job["work_wage"]["amount"] == 1
            assert mined.resources[MINE]["iron_ore"] == 1
            assert mined.resources[PLAYER]["coin_copper"] == 3
            assert mined.resources[MINE]["coin_copper"] == 0
            assert _copper_total(mined) == 4

            ore_posted = _post_offer(
                db, clock, MINE_KEEPER, MINE, MINE,
                "world01g-player-mined-ore", "iron_ore",
            )
            ore_quote = gateway.offers().details["offers"]
            assert ore_quote == ({
                "offer_id": "world01g-player-mined-ore",
                "seller_id": MINE_KEEPER, "resource": "iron_ore",
                "available": 1, "payment_resource": "coin_copper",
                "unit_price": 1,
            },)
            bought_ore = gateway.buy(
                "world01g-player-mined-ore", 1, 1,
                command_id="buy-mined-ore",
                expected_revision=ore_posted.revision,
            )
            after_ore = db.verify(WORLD)
            ore_trade = after_ore.market_trades[bought_ore.details["trade_id"]]
            assert ore_trade["buyer_id"] == PLAYER
            assert ore_trade["seller_id"] == MINE_KEEPER
            assert ore_trade["stock_owner_id"] == MINE
            assert (ore_trade["resource"], ore_trade["quantity"],
                    ore_trade["total_paid"]) == ("iron_ore", 1, 1)
            assert after_ore.resources[MINE]["iron_ore"] == 0
            assert after_ore.resources[PLAYER]["iron_ore"] == 1
            assert after_ore.resources[PLAYER]["coin_copper"] == 2
            assert after_ore.resources[MINE]["coin_copper"] == 1
            assert _copper_total(after_ore) == 4

            with pytest.raises(ValueError, match="contracted worksite"):
                gateway.deposit_material(
                    FORGE_RECIPE, "iron_ore", 1,
                    command_id="ore-deposit-at-mine",
                    expected_revision=after_ore.revision,
                )
            assert db.verify(WORLD).to_dict() == after_ore.to_dict()

            at_kiln = _travel(
                db, gateway, "mine-kiln", 30, "to-kiln", KILN,
            )
            assert at_kiln.resources[PLAYER]["iron_ore"] == 1
            assert gateway.offers().details["offers"] == ()
            charcoal_posted = _post_offer(
                db, clock, KILN_KEEPER, KILN, KILN,
                "world01g-kiln-charcoal", "charcoal",
            )
            charcoal_quote = gateway.offers().details["offers"]
            assert charcoal_quote == ({
                "offer_id": "world01g-kiln-charcoal",
                "seller_id": KILN_KEEPER, "resource": "charcoal",
                "available": 1, "payment_resource": "coin_copper",
                "unit_price": 1,
            },)
            charcoal_purchase = gateway.buy(
                "world01g-kiln-charcoal", 1, 1,
                command_id="buy-kiln-charcoal",
                expected_revision=charcoal_posted.revision,
            )
            bought_inputs = db.verify(WORLD)
            charcoal_trade = bought_inputs.market_trades[
                charcoal_purchase.details["trade_id"]
            ]
            assert charcoal_trade["buyer_id"] == PLAYER
            assert charcoal_trade["stock_owner_id"] == KILN
            assert (charcoal_trade["resource"], charcoal_trade["quantity"],
                    charcoal_trade["total_paid"]) == ("charcoal", 1, 1)
            assert bought_inputs.resources[PLAYER]["iron_ore"] == 1
            assert bought_inputs.resources[PLAYER]["charcoal"] == 1
            assert bought_inputs.resources[KILN]["charcoal"] == 0
            assert bought_inputs.resources[PLAYER]["coin_copper"] == 1
            assert _copper_total(bought_inputs) == 4

            trip = gateway.move(
                "kiln-forge", command_id="to-forge-depart",
                expected_revision=bought_inputs.revision,
            )
            assert trip.status == "traveling"
            in_transit = db.verify(WORLD)
            with pytest.raises(ValueError, match="while travelling"):
                # Custody cannot be deposited until the physical arrival event.
                gateway.deposit_material(
                    FORGE_RECIPE, "iron_ore", 1,
                    command_id="ore-deposit-in-transit",
                    expected_revision=trip.revision,
                )
            assert db.verify(WORLD).to_dict() == in_transit.to_dict()
            assert in_transit.entities[PLAYER]["location_id"] == KILN
            assert in_transit.resources[PLAYER]["iron_ore"] == 1
            gateway.wait(
                30, command_id="arrive-at-forge",
                expected_revision=in_transit.revision,
            )
            at_forge = db.verify(WORLD)
            assert at_forge.entities[PLAYER]["location_id"] == FORGE

            gateway.deposit_material(
                FORGE_RECIPE, "iron_ore", 1,
                command_id="deliver-mined-ore",
                expected_revision=at_forge.revision,
            )
            ore_at_forge = db.verify(WORLD)
            assert ore_at_forge.resources[PLAYER]["iron_ore"] == 0
            assert ore_at_forge.resources[FORGE]["iron_ore"] == 1
            with pytest.raises(InvalidEvent, match="insufficient or unknown"):
                gateway.work(
                    FORGE_RECIPE, command_id="forge-without-charcoal",
                    expected_revision=ore_at_forge.revision,
                )
            assert db.verify(WORLD).to_dict() == ore_at_forge.to_dict()
            gateway.deposit_material(
                FORGE_RECIPE, "charcoal", 1,
                command_id="deliver-declared-charcoal",
                expected_revision=ore_at_forge.revision,
            )
            ready = db.verify(WORLD)
            assert ready.resources[FORGE]["iron_ore"] == 1
            assert ready.resources[FORGE]["charcoal"] == 1
            assert ready.resources[PLAYER]["charcoal"] == 0

            forge_start = gateway.work(
                FORGE_RECIPE, command_id="forge-mined-ore-fitting",
                expected_revision=ready.revision,
            )
            running = db.verify(WORLD)
            forge_job_id = forge_start.details["job_id"]
            forge_job = running.production_jobs[forge_job_id]
            assert forge_job["status"] == "running"
            assert (forge_job["started_at"], forge_job["due"]) == (240, 330)
            assert running.resources[FORGE]["iron_ore"] == 0
            assert running.resources[FORGE]["charcoal"] == 0
            assert running.resources[FORGE]["anvil"] == 1
            assert running.resources[FORGE]["iron_fitting"] == 0
            assert running.resources[FORGE]["coin_copper"] == 1
            assert running.resources[PLAYER]["coin_copper"] == 1

            gateway.wait(
                89, command_id="wait-forge-to-329",
                expected_revision=running.revision,
            )
            almost_forged = db.verify(WORLD)
            assert almost_forged.time == 329
            assert almost_forged.production_jobs[forge_job_id]["status"] == "running"
            assert almost_forged.resources[FORGE]["iron_fitting"] == 0
            assert almost_forged.resources[FORGE]["coin_copper"] == 1
            assert almost_forged.resources[PLAYER]["coin_copper"] == 1

            gateway.wait(
                1, command_id="complete-forge-job",
                expected_revision=almost_forged.revision,
            )
            finished = db.verify(WORLD)
            forge_job = finished.production_jobs[forge_job_id]
            assert finished.time == 330
            assert forge_job["status"] == "completed"
            assert forge_job["output_after"] == 1
            assert forge_job["work_wage"]["paid_at"] == 330
            assert forge_job["work_wage"]["amount"] == 1
            assert finished.resources[FORGE]["iron_fitting"] == 1
            assert finished.resources[FORGE]["anvil"] == 1
            assert finished.resources[FORGE]["coin_copper"] == 0
            assert finished.resources[PLAYER]["coin_copper"] == 2
            assert finished.resources[PLAYER]["iron_ore"] == 0
            assert finished.resources[PLAYER]["charcoal"] == 0
            assert _copper_total(finished) == 4
            assert PLAYER not in finished.npcs
            assert db.load(WORLD).to_dict() == finished.to_dict()

            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == finished.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == finished.to_dict()
        assert reopened.load(WORLD).to_dict() == finished.to_dict()
        assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
