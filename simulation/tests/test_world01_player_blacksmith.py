"""WORLD-01: explicit, finite player blacksmith contract in a disposable world."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, PlayerGateway, SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import DuplicateCommand, InvalidEvent

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "scenarios" / "test_village"))
from play_physical_supply import (  # noqa: E402
    PLAYER, WORLD, audit_physical_supply, seed_physical_supply,
)

FORGE = "smithy"
RECIPE = "carlos-blacksmith-first-job"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(
        kind, None, "WORLD-01 disposable blacksmith world", 0, data,
    )


def _blacksmith_genesis(*, ore: int = 1, wage: int = 1):
    """Extend only this test world, before its first authorized bootstrap."""
    def add(events: list[DomainEvent]) -> None:
        player_wallets = [
            index for index, event in enumerate(events)
            if event.event_type == "ResourceChanged"
            and event.data.get("owner_id") == PLAYER
            and event.data.get("resource") == "coin_copper"
        ]
        assert len(player_wallets) == 1
        index = player_wallets[0]
        wallet_event = events[index]
        wallet_data = dict(wallet_event.data)
        assert wallet_data["current"] == 10
        # Transfer one existing coin from Carlos to the smithy treasury.
        wallet_data["current"] = 9
        events[index] = DomainEvent(
            wallet_event.event_type, wallet_event.actor_id,
            wallet_event.cause, wallet_event.time, wallet_data,
        )
        events.extend([
            _event("LocationCreated", {"id": FORGE, "name": "Smithy"}),
            _event("RouteCreated", {
                "id": "home-smithy", "a": "home", "b": FORGE, "seconds": 60,
            }),
            *[
                _event("ResourceChanged", {
                    "owner_id": FORGE, "resource": resource,
                    "previous": None, "current": amount,
                    "source": "initialization",
                })
                for resource, amount in (
                    ("iron_ore", ore), ("charcoal", 1),
                    ("iron_fitting", 0), ("anvil", 1),
                    ("coin_copper", 1),
                )
            ],
            _event("ProductionRecipeConfigured", {
                "id": RECIPE, "site_id": FORGE, "role": "blacksmith",
                "inputs": [
                    {"resource": "iron_ore", "amount": 1},
                    {"resource": "charcoal", "amount": 1},
                ],
                "output_resource": "iron_fitting", "output_amount": 1,
                "tool_resource": "anvil", "duration_seconds": 90,
                "wage_coin": wage, "player_worker_id": PLAYER,
            }),
        ])

    return add


def _seed(store: SQLiteEventStore, *, ore: int = 1, wage: int = 1) -> None:
    seed_physical_supply(
        store, playable_demo=True, player_needs_enabled=True,
        buyer_copper=2, personal_food=0, initial_market_food=0,
        trusted_genesis_hook=_blacksmith_genesis(ore=ore, wage=wage),
    )


def _open_player(store: SQLiteEventStore):
    clock = TimeEngine(store)
    clock.open_session(WORLD)
    gateway = PlayerGateway(
        store, clock, world_id=WORLD, player_id=PLAYER,
        engine=LivingWorldEngine(store, clock, navigation_enabled=True),
    )
    return clock, gateway


def _copper_total(state) -> int:
    return sum(stock["coin_copper"] for stock in state.resources.values()
               if "coin_copper" in stock)


def test_player_blacksmith_travels_and_completes_one_funded_job(tmp_path):
    with SQLiteEventStore(tmp_path / "world01-smith.sqlite") as store:
        _seed(store)
        opening = store.verify(WORLD)
        audit_physical_supply(
            opening, seed=1, water=2, buyer_copper=2,
            personal_food=0, initial_market_food=0,
        )
        assert opening.entities[PLAYER]["controller"] == "player"
        assert PLAYER not in opening.npcs
        assert len(opening.npcs) == 7
        assert opening.entities[PLAYER]["location_id"] == "home"
        assert opening.resources[PLAYER]["coin_copper"] == 9
        assert opening.resources[FORGE]["coin_copper"] == 1
        assert _copper_total(opening) == 12
        assert opening.production_jobs == {}

        clock, gateway = _open_player(store)
        try:
            with pytest.raises(ValueError, match="physically present"):
                gateway.work(
                    RECIPE, command_id="smith-before-travel",
                    expected_revision=opening.revision,
                )
            assert store.load(WORLD).to_dict() == opening.to_dict()

            trip = gateway.move(
                "home-smithy", command_id="smith-travel",
                expected_revision=opening.revision,
            )
            assert trip.status == "traveling"
            gateway.wait(
                59, command_id="smith-travel-to-59",
                expected_revision=trip.revision,
            )
            almost_there = store.verify(WORLD)
            assert almost_there.time == 59
            assert almost_there.entities[PLAYER]["location_id"] == "home"
            assert gateway.inspect().details == {
                "route_id": "home-smithy", "remaining_seconds": 1,
            }

            arrived_result = gateway.wait(
                1, command_id="smith-arrive",
                expected_revision=almost_there.revision,
            )
            arrived = store.verify(WORLD)
            assert arrived_result.time == 60
            assert arrived.entities[PLAYER]["location_id"] == FORGE
            assert arrived.production_jobs == {}

            started = gateway.work(
                RECIPE, command_id="smith-first-job",
                expected_revision=arrived.revision,
            )
            job_id = started.details["job_id"]
            running = store.verify(WORLD)
            receipt = running.production_jobs[job_id]
            assert receipt["npc_id"] == PLAYER
            assert receipt["status"] == "running"
            assert receipt["started_at"] == 60
            assert receipt["due"] == 150
            assert running.resources[FORGE]["iron_ore"] == 0
            assert running.resources[FORGE]["charcoal"] == 0
            assert running.resources[FORGE]["anvil"] == 1
            assert running.resources[FORGE]["iron_fitting"] == 0
            assert running.resources[FORGE]["coin_copper"] == 1
            assert running.resources[PLAYER]["coin_copper"] == 9
            assert _copper_total(running) == 12

            gateway.wait(
                89, command_id="smith-work-to-149",
                expected_revision=running.revision,
            )
            almost_done = store.verify(WORLD)
            assert almost_done.time == 149
            assert almost_done.production_jobs[job_id]["status"] == "running"
            assert almost_done.resources[FORGE]["iron_fitting"] == 0
            assert almost_done.resources[FORGE]["coin_copper"] == 1
            assert almost_done.resources[PLAYER]["coin_copper"] == 9

            gateway.wait(
                1, command_id="smith-work-due",
                expected_revision=almost_done.revision,
            )
            finished = store.verify(WORLD)
            finished_job = finished.production_jobs[job_id]
            assert finished.time == 150
            assert finished_job["status"] == "completed"
            wage_receipt = finished_job["work_wage"]
            assert wage_receipt["worker_id"] == PLAYER
            assert wage_receipt["site_id"] == FORGE
            assert wage_receipt["amount"] == 1
            assert wage_receipt["paid_at"] == 150
            assert (wage_receipt["site_before"], wage_receipt["site_after"]) == (1, 0)
            assert (wage_receipt["worker_before"],
                    wage_receipt["worker_after"]) == (9, 10)
            assert finished.resources[FORGE]["iron_fitting"] == 1
            assert finished.resources[FORGE]["anvil"] == 1
            assert finished.resources[FORGE]["coin_copper"] == 0
            assert finished.resources[PLAYER]["coin_copper"] == 10
            assert _copper_total(finished) == 12
            assert store.load(WORLD).to_dict() == finished.to_dict()
            assert store.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)

            with pytest.raises(DuplicateCommand):
                gateway.work(
                    RECIPE, command_id="smith-first-job",
                    expected_revision=finished.revision,
                )
            assert store.verify(WORLD).to_dict() == finished.to_dict()
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("ore,wage,expected_error", [
    (0, 1, "insufficient or unknown local production inputs/tool/output"),
    (1, 2, "full wage at signing"),
])
def test_player_blacksmith_rejects_missing_stock_or_unsigned_funding(
        tmp_path, ore, wage, expected_error):
    with SQLiteEventStore(tmp_path / f"world01-invalid-{ore}-{wage}.sqlite") as store:
        if wage > 1:
            with pytest.raises(InvalidEvent, match=expected_error):
                _seed(store, ore=ore, wage=wage)
            # The failed first bootstrap is atomic: no partial site or wallet.
            state = store.load(WORLD)
            assert state.revision == 0
            assert state.entities == {}
            assert store.db.execute(
                "SELECT COUNT(*) FROM events WHERE world_id=?", (WORLD,)
            ).fetchone() == (0,)
            return

        _seed(store, ore=ore, wage=wage)
        clock, gateway = _open_player(store)
        try:
            before = store.verify(WORLD)
            trip = gateway.move(
                "home-smithy", command_id="invalid-smith-travel",
                expected_revision=before.revision,
            )
            gateway.wait(
                60, command_id="invalid-smith-arrive",
                expected_revision=trip.revision,
            )
            before_work = store.verify(WORLD)
            with pytest.raises(InvalidEvent, match=expected_error):
                gateway.work(
                    RECIPE, command_id="invalid-smith-input",
                    expected_revision=before_work.revision,
                )
            assert store.verify(WORLD).to_dict() == before_work.to_dict()
        finally:
            clock.close_session(WORLD)
