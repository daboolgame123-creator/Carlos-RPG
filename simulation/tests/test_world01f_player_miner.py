"""WORLD-01f: Carlos explicitly works one funded finite-mine contract."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, PlayerGateway, SQLiteEventStore, TimeEngine,
)
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION
from carlos_sim.store import InvalidEvent

WORLD = "world01f-player-miner"
PLAYER = "carlos"
HOME = "home"
MINE = "iron_mine"
ROUTE = "home-iron-mine"
RECIPE = "carlos-finite-iron-miner"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01f disposable miner world", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": HOME, "name": "Home"}),
        _event("LocationCreated", {"id": MINE, "name": "Iron Mine"}),
        _event("RouteCreated", {
            "id": ROUTE, "a": HOME, "b": MINE, "seconds": 60,
        }),
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": HOME,
            "controller": "player",
        }),
    ]
    for owner, resources in (
        (PLAYER, {"coin_copper": 0}),
        (MINE, {
            "iron_ore_reserve": 1, "iron_ore": 0, "pickaxe": 1,
            "coin_copper": 2,
        }),
    ):
        for resource, quantity in resources.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))
    events.append(_event("ProductionRecipeConfigured", {
        "id": RECIPE, "site_id": MINE, "role": "miner",
        "input_resource": "iron_ore_reserve", "input_amount": 1,
        "output_resource": "iron_ore", "output_amount": 1,
        "tool_resource": "pickaxe", "duration_seconds": 120,
        "wage_coin": 1, "player_worker_id": PLAYER,
    }))
    store.append(WORLD, "world01f:bootstrap", 0, events, bootstrap=True)


def _copper_total(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _event_count(store: SQLiteEventStore) -> int:
    return store.db.execute(
        "SELECT COUNT(*) FROM events WHERE world_id=?", (WORLD,),
    ).fetchone()[0]


def test_player_explicitly_mines_one_funded_unit_from_finite_reserve(tmp_path):
    database = tmp_path / "world01f-player-miner.sqlite"
    with SQLiteEventStore(database) as store:
        _seed(store)
        opening = store.verify(WORLD)
        assert opening.schema_version == SCHEMA_VERSION == 46
        assert opening.rules_version == RULES_VERSION == 73
        assert opening.entities[PLAYER]["controller"] == "player"
        assert PLAYER not in opening.npcs
        assert opening.production_jobs == {}
        assert opening.resources[PLAYER]["coin_copper"] == 0
        assert opening.resources[MINE]["iron_ore_reserve"] == 1
        assert opening.resources[MINE]["iron_ore"] == 0
        assert opening.resources[MINE]["pickaxe"] == 1
        assert opening.resources[MINE]["coin_copper"] == 2
        assert _copper_total(opening) == 2

        clock = TimeEngine(store)
        clock.open_session(WORLD)
        try:
            gateway = PlayerGateway(
                store, clock, world_id=WORLD, player_id=PLAYER,
                engine=LivingWorldEngine(store, clock, navigation_enabled=True),
            )
            with pytest.raises(ValueError, match="physically present"):
                gateway.work(
                    RECIPE, command_id="miner-before-travel",
                    expected_revision=opening.revision,
                )
            assert store.verify(WORLD).to_dict() == opening.to_dict()

            travel = gateway.move(
                ROUTE, command_id="miner-travel", expected_revision=opening.revision,
            )
            assert travel.status == "traveling"
            assert store.verify(WORLD).production_jobs == {}
            arrived_result = gateway.wait(
                60, command_id="miner-arrive", expected_revision=travel.revision,
            )
            arrived = store.verify(WORLD)
            assert arrived_result.time == 60
            assert arrived.entities[PLAYER]["location_id"] == MINE
            assert arrived.production_jobs == {}
            assert arrived.resources[MINE]["iron_ore_reserve"] == 1
            assert arrived.resources[MINE]["iron_ore"] == 0

            started = gateway.work(
                RECIPE, command_id="miner-start-one",
                expected_revision=arrived.revision,
            )
            job_id = started.details["job_id"]
            running = store.verify(WORLD)
            job = running.production_jobs[job_id]
            assert job["npc_id"] == PLAYER
            assert job["status"] == "running"
            assert (job["started_at"], job["due"]) == (60, 180)
            assert running.resources[MINE]["iron_ore_reserve"] == 0
            assert running.resources[MINE]["iron_ore"] == 0
            assert running.resources[MINE]["pickaxe"] == 1
            assert running.resources[MINE]["coin_copper"] == 2
            assert running.resources[PLAYER]["coin_copper"] == 0
            assert PLAYER not in running.npcs
            assert _copper_total(running) == 2

            gateway.wait(
                119, command_id="miner-wait-to-179",
                expected_revision=running.revision,
            )
            almost_done = store.verify(WORLD)
            assert almost_done.time == 179
            assert almost_done.production_jobs[job_id]["status"] == "running"
            assert almost_done.resources[MINE]["iron_ore"] == 0
            assert almost_done.resources[MINE]["coin_copper"] == 2
            assert almost_done.resources[PLAYER]["coin_copper"] == 0

            gateway.wait(
                1, command_id="miner-job-due",
                expected_revision=almost_done.revision,
            )
            finished = store.verify(WORLD)
            completed = finished.production_jobs[job_id]
            receipt = completed["work_wage"]
            assert finished.time == 180
            assert completed["status"] == "completed"
            assert completed["output_after"] == 1
            assert receipt["worker_id"] == PLAYER
            assert receipt["site_id"] == MINE
            assert receipt["amount"] == 1
            assert receipt["paid_at"] == 180
            assert (receipt["site_before"], receipt["site_after"]) == (2, 1)
            assert (receipt["worker_before"], receipt["worker_after"]) == (0, 1)
            assert finished.resources[MINE]["iron_ore_reserve"] == 0
            assert finished.resources[MINE]["iron_ore"] == 1
            assert finished.resources[MINE]["pickaxe"] == 1
            assert finished.resources[MINE]["coin_copper"] == 1
            assert finished.resources[PLAYER]["coin_copper"] == 1
            assert PLAYER not in finished.npcs
            assert _copper_total(finished) == 2
            assert store.load(WORLD).to_dict() == finished.to_dict()

            prior_events = _event_count(store)
            with pytest.raises(InvalidEvent, match="insufficient or unknown"):
                gateway.work(
                    RECIPE, command_id="miner-empty-reserve-retry",
                    expected_revision=finished.revision,
                )
            assert store.verify(WORLD).to_dict() == finished.to_dict()
            assert _event_count(store) == prior_events

            store.snapshot(WORLD)
            assert store.verify(WORLD).to_dict() == finished.to_dict()
            assert store.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == finished.to_dict()
        assert reopened.load(WORLD).to_dict() == finished.to_dict()
        assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
