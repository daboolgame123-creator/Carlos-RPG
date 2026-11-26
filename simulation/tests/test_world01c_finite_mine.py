"""WORLD-01c: the living engine extracts and sells one finite ore unit."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCProductionService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import InvalidEvent

WORLD = "world01c-finite-mine"
PLAYER = "carlos"
MINER = "miner"
HOME = "home"
MINE = "iron_mine"
RECIPE = "finite-iron-extraction"
JOB = "eco-job-miner-0"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01c disposable finite-mine setup", 0, data)


def _seed(store: SQLiteEventStore, *, reserve: int = 1) -> None:
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": HOME, "name": "Home"}),
        _event("LocationCreated", {"id": MINE, "name": "Iron mine"}),
        _event("RouteCreated", {
            "id": "home-mine", "a": HOME, "b": MINE, "seconds": 60,
        }),
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": HOME,
            "controller": "player",
        }),
        _event("EntityCreated", {
            "id": MINER, "name": "Miner", "location_id": MINE,
            "controller": "npc",
        }),
        _event("NPCConfigured", {
            "npc_id": MINER, "role": "miner",
            "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }),
    ]
    for owner, stock in (
        (PLAYER, {"coin_copper": 1, "iron_ore": 0}),
        (MINER, {"coin_copper": 0}),
        (MINE, {"iron_ore_reserve": reserve, "iron_ore": 0,
                "pickaxe": 1, "coin_copper": 1}),
    ):
        for resource, quantity in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))
    events.extend((
        _event("NPCRoutineConfigured", {
            "npc_id": MINER, "home_id": HOME,
            "workplace_id": MINE, "work_start": 0, "work_end": 20_000,
        }),
        _event("MarketStallConfigured", {
            "site_id": MINE, "keeper_id": MINER,
        }),
        _event("ProductionRecipeConfigured", {
            "id": RECIPE, "site_id": MINE, "role": "miner",
            "input_resource": "iron_ore_reserve", "input_amount": 1,
            "output_resource": "iron_ore", "output_amount": 1,
            "tool_resource": "pickaxe", "duration_seconds": 120,
            "wage_coin": 1,
        }),
    ))
    store.append(WORLD, "world01c:bootstrap", 0, events, bootstrap=True)


def _engine(store: SQLiteEventStore, clock: TimeEngine) -> LivingWorldEngine:
    return LivingWorldEngine(
        store, clock, economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=True, navigation_enabled=True, routines_enabled=True,
        multi_professional_markets_enabled=True,
    )


def _copper(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _ore_equivalents(state) -> int:
    outstanding = sum(
        job["recipe_id"] == RECIPE and job["status"] == "running"
        for job in state.production_jobs.values()
    )
    return (state.resources[MINE]["iron_ore_reserve"]
            + state.resources[MINE]["iron_ore"]
            + state.resources[PLAYER]["iron_ore"] + outstanding)


def test_miner_produces_one_ore_from_finite_reserve_then_carlos_buys_it(tmp_path):
    database = tmp_path / "world01c-finite-mine.sqlite"
    with SQLiteEventStore(database) as db:
        _seed(db)
        opening = db.verify(WORLD)
        assert opening.resources[MINE]["iron_ore_reserve"] == 1
        assert opening.resources[MINE]["iron_ore"] == 0
        assert _ore_equivalents(opening) == 1
        assert _copper(opening) == 2

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            gateway = PlayerGateway(
                db, clock, world_id=WORLD, player_id=PLAYER, engine=engine,
            )
            departure = gateway.move(
                "home-mine", command_id="walk-to-mine",
                expected_revision=opening.revision,
            )
            first_wait = gateway.wait(
                60, command_id="wait-to-mine", expected_revision=departure.revision,
            )
            working = db.verify(WORLD)
            job = working.production_jobs[JOB]
            assert first_wait.time == 60
            assert job["status"] == "running"
            assert (job["started_at"], job["due"]) == (0, 120)
            assert working.resources[MINE]["iron_ore_reserve"] == 0
            assert working.resources[MINE]["iron_ore"] == 0
            assert working.resources[MINE]["pickaxe"] == 1
            assert working.resources[MINE]["coin_copper"] == 1
            assert working.resources[MINER]["coin_copper"] == 0
            assert _ore_equivalents(working) == 1
            assert _copper(working) == 2
            assert gateway.offers().details["offers"] == ()

            due = gateway.wait(
                60, command_id="wait-for-mining", expected_revision=working.revision,
            )
            mined = db.verify(WORLD)
            completed_job = mined.production_jobs[JOB]
            assert due.time == 120
            assert completed_job["status"] == "completed"
            assert completed_job["output_after"] == 1
            assert completed_job["work_wage"]["amount"] == 1
            assert mined.resources[MINE]["iron_ore_reserve"] == 0
            assert mined.resources[MINE]["iron_ore"] == 1
            assert mined.resources[MINE]["pickaxe"] == 1
            assert mined.resources[MINE]["coin_copper"] == 0
            assert mined.resources[MINER]["coin_copper"] == 1
            assert _ore_equivalents(mined) == 1
            assert _copper(mined) == 2

            quotes = gateway.offers().details["offers"]
            assert len(quotes) == 1
            quote = quotes[0]
            assert quote["offer_id"].startswith("eco-multiquote-miner-")
            assert {key: value for key, value in quote.items()
                    if key != "offer_id"} == {
                "seller_id": MINER, "resource": "iron_ore", "available": 1,
                "payment_resource": "coin_copper", "unit_price": 1,
            }
            purchase = gateway.buy(
                quote["offer_id"], 1, 1, command_id="buy-mined-ore",
                expected_revision=mined.revision,
            )
            sold = db.verify(WORLD)
            assert purchase.status == "purchased"
            assert purchase.details["trade_id"].startswith("player-")
            assert {key: value for key, value in purchase.details.items()
                    if key != "trade_id"} == {
                "offer_id": quote["offer_id"], "resource": "iron_ore",
                "quantity": 1, "payment_resource": "coin_copper",
                "total_paid": 1,
            }
            assert sold.resources[MINE]["iron_ore"] == 0
            assert sold.resources[PLAYER]["iron_ore"] == 1
            assert sold.resources[PLAYER]["coin_copper"] == 0
            assert sold.resources[MINE]["coin_copper"] == 1
            assert sold.resources[MINER]["coin_copper"] == 1
            assert _ore_equivalents(sold) == 1
            assert _copper(sold) == 2

            with pytest.raises(InvalidEvent, match="insufficient"):
                NPCProductionService(db, clock).start(
                    WORLD, MINER, RECIPE, "mine-empty-seam",
                    expected_revision=sold.revision,
                )
            assert db.verify(WORLD).to_dict() == sold.to_dict()
            assert db.verify(WORLD).to_dict() == sold.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == sold.to_dict()
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == sold.to_dict()


def test_miner_cannot_produce_ore_when_the_declared_reserve_is_empty(tmp_path):
    with SQLiteEventStore(tmp_path / "world01c-empty-mine.sqlite") as db:
        _seed(db, reserve=0)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            before = db.verify(WORLD)
            with pytest.raises(InvalidEvent, match="insufficient"):
                NPCProductionService(db, clock).start(
                    WORLD, MINER, RECIPE, "mine-empty-seam",
                    expected_revision=before.revision,
                )
            assert db.verify(WORLD).to_dict() == before.to_dict()
        finally:
            clock.close_session(WORLD)
