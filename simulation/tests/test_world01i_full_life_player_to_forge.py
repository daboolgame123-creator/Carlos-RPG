"""WORLD-01i: Carlos's complete forge chain and independent NPC in full-life."""
from __future__ import annotations

import json
import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCMarketService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION
from carlos_sim.store import InvalidEvent

WORLD = "world01i-full-life-player-to-forge"
PLAYER = "carlos"
MINE_KEEPER = "mine_steward"
KILN_KEEPER = "kiln_steward"
WOODCUTTER = "independent_woodcutter"
HOME = "home"
MINE = "iron_mine"
FOREST = "lumberyard"
KILN = "charcoal_kiln"
FORGE = "smithy"
MINE_RECIPE = "carlos-finite-iron-miner"
FORGE_RECIPE = "carlos-iron-fitting"
WOOD_RECIPE = "independent-finite-timber-cutting"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01i disposable integration setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        *[_event("LocationCreated", {"id": site, "name": site})
          for site in (HOME, MINE, FOREST, KILN, FORGE)],
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
    events.extend((
        _event("EntityCreated", {
            "id": WOODCUTTER, "name": "Independent lumber worker",
            "location_id": FOREST, "controller": "npc",
        }),
        _event("NPCConfigured", {
            "npc_id": WOODCUTTER, "role": "woodcutter",
            "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }),
    ))

    # All opening copper, source units, and tools have explicit owners. Charcoal
    # is a declared kiln stock produced outside this bounded integration test.
    for owner, stock in (
        (PLAYER, {"coin_copper": 2, "iron_ore": 0, "charcoal": 0}),
        (MINE, {"iron_ore_reserve": 1, "iron_ore": 0,
                "pickaxe": 1, "coin_copper": 1}),
        (KILN, {"charcoal": 1, "coin_copper": 0}),
        (FOREST, {"standing_timber": 1, "wood": 0, "axe": 1,
                  "coin_copper": 1}),
        (FORGE, {"iron_ore": 0, "charcoal": 0, "iron_fitting": 0,
                 "anvil": 1, "coin_copper": 1}),
        (MINE_KEEPER, {"coin_copper": 0}),
        (KILN_KEEPER, {"coin_copper": 0}),
        (WOODCUTTER, {"coin_copper": 0}),
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
        _event("NPCRoutineConfigured", {
            "npc_id": WOODCUTTER, "home_id": HOME,
            "workplace_id": FOREST, "work_start": 0, "work_end": 20_000,
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
        _event("ProductionRecipeConfigured", {
            "id": WOOD_RECIPE, "site_id": FOREST, "role": "woodcutter",
            "input_resource": "standing_timber", "input_amount": 1,
            "output_resource": "wood", "output_amount": 1,
            "tool_resource": "axe", "duration_seconds": 120,
            "wage_coin": 1,
        }),
    ))
    store.append(WORLD, "world01i:bootstrap", 0, events, bootstrap=True)


def _copper_total(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _event_rows(store: SQLiteEventStore) -> tuple[tuple, ...]:
    return tuple(store.db.execute(
        "SELECT seq, command_id, payload, hash FROM events "
        "WHERE world_id=? ORDER BY seq", (WORLD,),
    ))


def _npc_jobs(state) -> list[dict]:
    return sorted((job for job in state.production_jobs.values()
                   if job["npc_id"] == WOODCUTTER
                   and job["recipe_id"] == WOOD_RECIPE),
                  key=lambda job: (job["started_at"], job["due"]))


def _full_life_engine(store: SQLiteEventStore, clock: TimeEngine):
    return LivingWorldEngine(
        store, clock, max_events_per_advance=5000,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=False, navigation_enabled=True, routines_enabled=True,
        multi_professional_markets_enabled=True, compound_procurement_enabled=True,
        consumption_enabled=True, survival_enabled=True, supply_enabled=True,
        professional_full_life_enabled=True,
    )


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


def _run_world(database):
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
        assert opening.resources[FOREST]["standing_timber"] == 1
        assert opening.resources[FOREST]["wood"] == 0
        assert opening.resources[PLAYER]["coin_copper"] == 2
        assert _copper_total(opening) == 5

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            gateway = PlayerGateway(
                db, clock, world_id=WORLD, player_id=PLAYER,
                engine=_full_life_engine(db, clock),
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
            npc_jobs = _npc_jobs(at_mine)
            assert len(npc_jobs) == 1
            npc_job = npc_jobs[0]
            assert npc_job["status"] == "running"
            assert (npc_job["started_at"], npc_job["due"]) == (0, 120)
            assert at_mine.resources[FOREST]["standing_timber"] == 0
            assert at_mine.resources[FOREST]["wood"] == 0
            assert at_mine.resources[FOREST]["coin_copper"] == 1
            assert at_mine.resources[WOODCUTTER]["coin_copper"] == 0
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
            assert _npc_jobs(mining)[0]["status"] == "running"
            assert _copper_total(mining) == 5

            gateway.wait(
                59, command_id="wait-mining-to-119",
                expected_revision=mining.revision,
            )
            before_npc_due = db.verify(WORLD)
            assert before_npc_due.time == 119
            assert before_npc_due.production_jobs[started.details["job_id"]]["status"] == "running"
            assert _npc_jobs(before_npc_due)[0]["status"] == "running"
            assert before_npc_due.resources[FOREST]["wood"] == 0
            assert before_npc_due.resources[WOODCUTTER]["coin_copper"] == 0
            assert before_npc_due.resources[MINE]["iron_ore"] == 0
            assert before_npc_due.resources[PLAYER]["coin_copper"] == 2

            gateway.wait(
                1, command_id="finish-npc-woodcutting",
                expected_revision=before_npc_due.revision,
            )
            npc_completed = db.verify(WORLD)
            npc_job = _npc_jobs(npc_completed)[0]
            assert npc_completed.time == 120
            assert npc_job["status"] == "completed"
            assert npc_job["output_after"] == 1
            assert npc_job["work_wage"]["paid_at"] == 120
            assert npc_job["work_wage"]["amount"] == 1
            assert npc_completed.resources[FOREST]["standing_timber"] == 0
            assert npc_completed.resources[FOREST]["wood"] == 1
            assert npc_completed.resources[FOREST]["coin_copper"] == 0
            assert npc_completed.resources[WOODCUTTER]["coin_copper"] == 1
            assert npc_completed.production_jobs[started.details["job_id"]]["status"] == "running"
            assert npc_completed.resources[MINE]["iron_ore"] == 0
            assert npc_completed.resources[PLAYER]["coin_copper"] == 2
            assert _copper_total(npc_completed) == 5

            start_events = [json.loads(row[2]) for row in _event_rows(db)]
            start_events = [event for event in start_events
                            if event["event_type"] == "ProductionStarted"]
            npc_job_id = next(
                job_id for job_id, job in npc_completed.production_jobs.items()
                if job["npc_id"] == WOODCUTTER
                and job["recipe_id"] == WOOD_RECIPE
            )
            npc_start = next(event for event in start_events
                             if event["data"]["id"] == npc_job_id)
            assert (npc_start["actor_id"], npc_start["time"]) == (WOODCUTTER, 0)
            assert npc_start["cause"].startswith("autonomous production:")
            player_start = next(
                event for event in start_events
                if event["data"]["id"] == started.details["job_id"]
            )
            assert (player_start["actor_id"], player_start["cause"],
                    player_start["time"]) == (
                PLAYER, "player explicitly started contracted local production", 60,
            )

            gateway.wait(
                59, command_id="wait-mining-to-179",
                expected_revision=npc_completed.revision,
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
            assert _copper_total(mined) == 5

            ore_posted = _post_offer(
                db, clock, MINE_KEEPER, MINE, MINE,
                "world01i-player-mined-ore", "iron_ore",
            )
            ore_quote = gateway.offers().details["offers"]
            assert ore_quote == ({
                "offer_id": "world01i-player-mined-ore",
                "seller_id": MINE_KEEPER, "resource": "iron_ore",
                "available": 1, "payment_resource": "coin_copper",
                "unit_price": 1,
            },)
            bought_ore = gateway.buy(
                "world01i-player-mined-ore", 1, 1,
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
            assert _copper_total(after_ore) == 5

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
                "world01i-kiln-charcoal", "charcoal",
            )
            charcoal_quote = gateway.offers().details["offers"]
            assert charcoal_quote == ({
                "offer_id": "world01i-kiln-charcoal",
                "seller_id": KILN_KEEPER, "resource": "charcoal",
                "available": 1, "payment_resource": "coin_copper",
                "unit_price": 1,
            },)
            charcoal_purchase = gateway.buy(
                "world01i-kiln-charcoal", 1, 1,
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
            assert _copper_total(bought_inputs) == 5

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
            assert _copper_total(finished) == 5
            assert finished.resources[WOODCUTTER]["coin_copper"] == 1
            assert finished.resources[FOREST]["wood"] == 1
            assert len(_npc_jobs(finished)) == 1
            assert PLAYER not in finished.npcs
            assert db.load(WORLD).to_dict() == finished.to_dict()

            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == finished.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            state_data = finished.to_dict()
            rows = _event_rows(db)
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == state_data
        assert reopened.load(WORLD).to_dict() == state_data
        assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    return state_data, rows


def test_full_life_carlos_forges_while_independent_npc_works_and_replays(tmp_path):
    first_state, first_events = _run_world(
        tmp_path / "world01i-first.sqlite",
    )
    repeated_state, repeated_events = _run_world(
        tmp_path / "world01i-repeat.sqlite",
    )
    assert repeated_state == first_state
    assert repeated_events == first_events
