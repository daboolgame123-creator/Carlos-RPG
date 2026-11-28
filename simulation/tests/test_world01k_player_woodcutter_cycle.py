"""WORLD-01k: a finite woodcutter job chosen and carried by Carlos."""
from __future__ import annotations

import json
import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCMarketService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION
from carlos_sim.store import InvalidEvent

WORLD = "world01k-player-woodcutter-cycle"
PLAYER = "carlos"
STEWARD = "forest_market_steward"
HOME = "home"
FOREST = "lumberyard"
ROUTE = "home-lumberyard"
RECIPE = "carlos-finite-woodcutting"
OFFER = "world01k-real-wood"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01k bounded experiment setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": HOME, "name": "Home"}),
        _event("LocationCreated", {"id": FOREST, "name": "Lumberyard"}),
        _event("RouteCreated", {
            "id": ROUTE, "a": HOME, "b": FOREST, "seconds": 60,
        }),
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": HOME,
            "controller": "player",
        }),
        _event("EntityCreated", {
            "id": STEWARD, "name": "Forest steward", "location_id": FOREST,
            "controller": "npc",
        }),
        _event("NPCConfigured", {
            "npc_id": STEWARD, "role": "merchant",
            "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }),
        # Four coins cover the agreed two-coin wage twice, so a retry after
        # the harvest is rejected for the exhausted timber, not lack of cash.
        *[_event("ResourceChanged", {
            "owner_id": owner, "resource": item,
            "previous": None, "current": amount, "source": "initialization",
        }) for owner, stock in (
            (PLAYER, {"coin_copper": 0, "wood": 0}),
            (FOREST, {"standing_timber": 1, "wood": 0, "axe": 1,
                      "coin_copper": 4}),
            (STEWARD, {"coin_copper": 0}),
        ) for item, amount in stock.items()],
        _event("MarketStallConfigured", {
            "site_id": FOREST, "keeper_id": STEWARD,
        }),
        _event("ProductionRecipeConfigured", {
            "id": RECIPE, "site_id": FOREST, "role": "woodcutter",
            "input_resource": "standing_timber", "input_amount": 1,
            "output_resource": "wood", "output_amount": 1,
            "tool_resource": "axe", "duration_seconds": 120,
            "wage_coin": 2, "player_worker_id": PLAYER,
        }),
    ]
    store.append(WORLD, "world01k:bootstrap", 0, events, bootstrap=True)


def _copper_total(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _event_rows(store: SQLiteEventStore) -> tuple[tuple, ...]:
    return tuple(store.db.execute(
        "SELECT seq, command_id, payload, hash FROM events "
        "WHERE world_id=? ORDER BY seq", (WORLD,),
    ))


def _run_world(database):
    with SQLiteEventStore(database) as store:
        _seed(store)
        opening = store.verify(WORLD)
        assert opening.schema_version == SCHEMA_VERSION
        assert opening.rules_version == RULES_VERSION
        assert opening.entities[PLAYER]["controller"] == "player"
        assert PLAYER not in opening.npcs
        assert opening.production_jobs == {}
        assert opening.market_offers == {}
        assert opening.resources[FOREST]["standing_timber"] == 1
        assert opening.resources[FOREST]["wood"] == 0
        assert opening.resources[FOREST]["axe"] == 1
        assert opening.resources[FOREST]["coin_copper"] == 4
        assert _copper_total(opening) == 4

        clock = TimeEngine(store)
        clock.open_session(WORLD)
        try:
            # The focused economic engine advances actual scheduled work and
            # travel while keeping unrelated autonomous systems out of this
            # one-job acceptance world.
            engine = LivingWorldEngine(
                store, clock, economic_enabled=True, agriculture_enabled=True,
                economy_only_enabled=True,
            )
            player = PlayerGateway(
                store, clock, world_id=WORLD, player_id=PLAYER, engine=engine,
            )
            trip = player.move(
                ROUTE, command_id="to-lumberyard", expected_revision=opening.revision,
            )
            assert trip.status == "traveling"
            arrived = player.wait(
                60, command_id="arrive-lumberyard", expected_revision=trip.revision,
            )
            at_forest = store.verify(WORLD)
            assert arrived.time == 60
            assert at_forest.entities[PLAYER]["location_id"] == FOREST
            assert at_forest.resources[FOREST]["standing_timber"] == 1
            assert at_forest.market_offers == {}

            started = player.work(
                RECIPE, command_id="carlos-starts-woodcutting",
                expected_revision=at_forest.revision,
            )
            working = store.verify(WORLD)
            job_id = started.details["job_id"]
            job = working.production_jobs[job_id]
            assert job["npc_id"] == PLAYER
            assert job["status"] == "running"
            assert (job["started_at"], job["due"]) == (60, 180)
            assert working.resources[FOREST]["standing_timber"] == 0
            assert working.resources[FOREST]["wood"] == 0
            assert working.resources[FOREST]["coin_copper"] == 4
            assert working.resources[PLAYER]["coin_copper"] == 0
            assert _copper_total(working) == 4

            player.wait(
                119, command_id="wait-for-wood-119",
                expected_revision=working.revision,
            )
            before_due = store.verify(WORLD)
            assert before_due.time == 179
            assert before_due.production_jobs[job_id]["status"] == "running"
            assert before_due.resources[FOREST]["wood"] == 0
            assert before_due.resources[PLAYER]["coin_copper"] == 0
            assert player.offers().details["offers"] == ()

            player.wait(
                1, command_id="finish-woodcutting-at-120",
                expected_revision=before_due.revision,
            )
            cut = store.verify(WORLD)
            job = cut.production_jobs[job_id]
            assert cut.time == 180
            assert job["status"] == "completed"
            assert job["finished_at"] == 180
            assert job["output_after"] == 1
            assert job["work_wage"]["worker_id"] == PLAYER
            assert job["work_wage"]["amount"] == 2
            assert job["work_wage"]["paid_at"] == 180
            assert cut.resources[FOREST]["standing_timber"] == 0
            assert cut.resources[FOREST]["wood"] == 1
            assert cut.resources[FOREST]["coin_copper"] == 2
            assert cut.resources[PLAYER]["coin_copper"] == 2
            assert _copper_total(cut) == 4

            start_event = next(
                json.loads(row[2]) for row in _event_rows(store)
                if json.loads(row[2])["event_type"] == "ProductionStarted"
                and json.loads(row[2])["data"]["id"] == job_id
            )
            assert (start_event["actor_id"], start_event["time"],
                    start_event["cause"]) == (
                PLAYER, 60, "player explicitly started contracted local production",
            )

            # The steward lists only the unit that actually exists after
            # production. Carlos observes and pays the real local quote with
            # the wage he just earned; neither item is granted by the command.
            market = NPCMarketService(store, clock)
            posted = market.post(
                WORLD, STEWARD, FOREST, FOREST, OFFER,
                "wood", 1, "coin_copper", 1,
                expected_revision=cut.revision,
            )
            quote = player.offers().details["offers"]
            assert quote == ({
                "offer_id": OFFER, "seller_id": STEWARD, "resource": "wood",
                "available": 1, "payment_resource": "coin_copper", "unit_price": 1,
            },)
            purchase = player.buy(
                OFFER, 1, 1, command_id="buy-earned-wood",
                expected_revision=posted.state.revision,
            )
            sold = store.verify(WORLD)
            trade = sold.market_trades[purchase.details["trade_id"]]
            assert (trade["buyer_id"], trade["seller_id"], trade["stock_owner_id"],
                    trade["site_id"], trade["resource"], trade["quantity"],
                    trade["total_paid"]) == (
                PLAYER, STEWARD, FOREST, FOREST, "wood", 1, 1,
            )
            assert sold.resources[FOREST]["wood"] == 0
            assert sold.resources[PLAYER]["wood"] == 1
            assert sold.resources[FOREST]["coin_copper"] == 3
            assert sold.resources[PLAYER]["coin_copper"] == 1
            assert _copper_total(sold) == 4

            # A second job cannot be started from the exhausted forest. The
            # failed command must be atomic, including its event history.
            before_retry_events = _event_rows(store)
            with pytest.raises(InvalidEvent, match="insufficient or unknown"):
                player.work(
                    RECIPE, command_id="try-empty-forest-again",
                    expected_revision=sold.revision,
                )
            assert store.verify(WORLD).to_dict() == sold.to_dict()
            assert _event_rows(store) == before_retry_events

            return_trip = player.move(
                ROUTE, command_id="carry-wood-home",
                expected_revision=sold.revision,
            )
            assert return_trip.status == "traveling"
            in_transit = store.verify(WORLD)
            assert in_transit.resources[PLAYER]["wood"] == 1
            player.wait(
                60, command_id="arrive-home-with-wood",
                expected_revision=return_trip.revision,
            )
            finished = store.verify(WORLD)
            assert finished.time == 240
            assert finished.entities[PLAYER]["location_id"] == HOME
            assert finished.resources[PLAYER]["wood"] == 1
            assert finished.resources[FOREST]["wood"] == 0
            assert finished.resources[FOREST]["standing_timber"] == 0
            assert finished.resources[PLAYER]["coin_copper"] == 1
            assert finished.resources[FOREST]["coin_copper"] == 3
            assert _copper_total(finished) == 4
            assert PLAYER not in finished.npcs
            assert len(finished.production_jobs) == 1
            assert len(finished.market_trades) == 1
            assert store.load(WORLD).to_dict() == finished.to_dict()

            store.snapshot(WORLD)
            assert store.verify(WORLD).to_dict() == finished.to_dict()
            assert store.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert store.db.execute("PRAGMA foreign_key_check").fetchall() == []
            final_state = finished.to_dict()
            final_events = _event_rows(store)
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == final_state
        assert reopened.load(WORLD).to_dict() == final_state
        assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    return final_state, final_events


def test_player_woodcutter_cycle_is_finite_paid_and_replayable(tmp_path):
    first_state, first_events = _run_world(tmp_path / "woodcutter-first.sqlite")
    repeat_state, repeat_events = _run_world(tmp_path / "woodcutter-repeat.sqlite")
    assert repeat_state == first_state
    assert repeat_events == first_events
