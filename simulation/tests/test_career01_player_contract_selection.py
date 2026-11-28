"""CAREER-01: Carlos selects two real profession contracts in one world."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, PlayerGateway, SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import InvalidEvent


WORLD = "career01-two-player-contracts"
PLAYER = "carlos"
HOME = "home"
BAKERY = "bakery"
LUMBERYARD = "lumberyard"
BAKER_RECIPE = "carlos-baker-contract"
WOODCUTTER_RECIPE = "carlos-woodcutter-contract"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "CAREER-01 finite test-world setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": HOME, "name": "Home"}),
        _event("LocationCreated", {"id": BAKERY, "name": "Bakery"}),
        _event("LocationCreated", {"id": LUMBERYARD, "name": "Lumberyard"}),
        _event("RouteCreated", {
            "id": "home-bakery", "a": HOME, "b": BAKERY, "seconds": 30,
        }),
        _event("RouteCreated", {
            "id": "bakery-lumberyard", "a": BAKERY, "b": LUMBERYARD,
            "seconds": 60,
        }),
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": HOME,
            "controller": "player",
        }),
    ]
    for owner, stock in (
        (PLAYER, {"coin_copper": 0}),
        (BAKERY, {"grain": 1, "food": 0, "oven": 1, "coin_copper": 4}),
        (LUMBERYARD, {
            "standing_timber": 1, "wood": 0, "axe": 1, "coin_copper": 4,
        }),
    ):
        for resource, amount in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource, "previous": None,
                "current": amount, "source": "initialization",
            }))
    events.extend((
        _event("ProductionRecipeConfigured", {
            "id": BAKER_RECIPE, "site_id": BAKERY, "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 2,
            "tool_resource": "oven", "duration_seconds": 90,
            "wage_coin": 2, "player_worker_id": PLAYER,
        }),
        _event("ProductionRecipeConfigured", {
            "id": WOODCUTTER_RECIPE, "site_id": LUMBERYARD,
            "role": "woodcutter", "input_resource": "standing_timber",
            "input_amount": 1, "output_resource": "wood", "output_amount": 1,
            "tool_resource": "axe", "duration_seconds": 120,
            "wage_coin": 2, "player_worker_id": PLAYER,
        }),
    ))
    store.append(WORLD, "career01:bootstrap", 0, events, bootstrap=True)


def _event_rows(store: SQLiteEventStore) -> tuple[tuple, ...]:
    return tuple(store.db.execute(
        "SELECT seq, command_id, payload, hash FROM events "
        "WHERE world_id=? ORDER BY seq", (WORLD,),
    ))


def _run_world(database) -> tuple[dict, tuple[tuple, ...]]:
    with SQLiteEventStore(database) as store:
        _seed(store)
        opening = store.verify(WORLD)
        assert set(opening.production_recipes) == {BAKER_RECIPE, WOODCUTTER_RECIPE}
        assert opening.production_jobs == {}
        assert opening.resources[BAKERY]["grain"] == 1
        assert opening.resources[LUMBERYARD]["standing_timber"] == 1
        assert PLAYER not in opening.npcs

        clock = TimeEngine(store)
        clock.open_session(WORLD)
        player = PlayerGateway(
            store, clock, world_id=WORLD, player_id=PLAYER,
            engine=LivingWorldEngine(store, clock),
        )
        try:
            # Both contracts are present, but Carlos must reach each site.
            rows_before = _event_rows(store)
            with pytest.raises(ValueError, match="physically present"):
                player.work(
                    WOODCUTTER_RECIPE, command_id="wood-from-home",
                    expected_revision=opening.revision,
                )
            assert store.verify(WORLD).to_dict() == opening.to_dict()
            assert _event_rows(store) == rows_before

            trip = player.move(
                "home-bakery", command_id="career-to-bakery",
                expected_revision=opening.revision,
            )
            player.wait(
                30, command_id="career-arrive-bakery",
                expected_revision=trip.revision,
            )
            at_bakery = store.verify(WORLD)
            started_baking = player.work(
                BAKER_RECIPE, command_id="career-start-baker",
                expected_revision=at_bakery.revision,
            )
            baking = store.verify(WORLD)
            baker_job_id = started_baking.details["job_id"]
            assert baking.production_jobs[baker_job_id]["due"] == 120
            assert baking.resources[BAKERY]["grain"] == 0
            assert baking.resources[BAKERY]["food"] == 0
            assert baking.resources[BAKERY]["coin_copper"] == 4
            assert baking.resources[PLAYER]["coin_copper"] == 0

            player.wait(
                89, command_id="career-baker-before-due",
                expected_revision=baking.revision,
            )
            before_baker_due = store.verify(WORLD)
            assert before_baker_due.time == 119
            assert before_baker_due.resources[BAKERY]["food"] == 0
            assert before_baker_due.resources[PLAYER]["coin_copper"] == 0
            player.wait(
                1, command_id="career-finish-baker",
                expected_revision=before_baker_due.revision,
            )
            baked = store.verify(WORLD)
            baker_receipt = baked.production_jobs[baker_job_id]
            assert baker_receipt["status"] == "completed"
            assert baker_receipt["finished_at"] == 120
            assert baker_receipt["work_wage"]["amount"] == 2
            assert baked.resources[BAKERY]["food"] == 2
            assert baked.resources[BAKERY]["coin_copper"] == 2
            assert baked.resources[PLAYER]["coin_copper"] == 2

            # A second explicit start is rejected after the finite grain is
            # gone; rejection appends no event and changes no projection.
            rows_before = _event_rows(store)
            with pytest.raises(InvalidEvent, match="insufficient or unknown"):
                player.work(
                    BAKER_RECIPE, command_id="career-retry-empty-bakery",
                    expected_revision=baked.revision,
                )
            assert store.verify(WORLD).to_dict() == baked.to_dict()
            assert _event_rows(store) == rows_before

            trip = player.move(
                "bakery-lumberyard", command_id="career-to-lumberyard",
                expected_revision=baked.revision,
            )
            player.wait(
                60, command_id="career-arrive-lumberyard",
                expected_revision=trip.revision,
            )
            at_lumberyard = store.verify(WORLD)
            assert at_lumberyard.time == 180
            started_cutting = player.work(
                WOODCUTTER_RECIPE, command_id="career-start-woodcutter",
                expected_revision=at_lumberyard.revision,
            )
            cutting = store.verify(WORLD)
            wood_job_id = started_cutting.details["job_id"]
            assert cutting.production_jobs[wood_job_id]["due"] == 300
            assert cutting.resources[LUMBERYARD]["standing_timber"] == 0
            assert cutting.resources[LUMBERYARD]["wood"] == 0
            assert cutting.resources[LUMBERYARD]["coin_copper"] == 4
            assert cutting.resources[PLAYER]["coin_copper"] == 2

            player.wait(
                119, command_id="career-woodcutter-before-due",
                expected_revision=cutting.revision,
            )
            before_cut_due = store.verify(WORLD)
            assert before_cut_due.time == 299
            assert before_cut_due.resources[LUMBERYARD]["wood"] == 0
            assert before_cut_due.resources[PLAYER]["coin_copper"] == 2
            player.wait(
                1, command_id="career-finish-woodcutter",
                expected_revision=before_cut_due.revision,
            )
            finished = store.verify(WORLD)
            wood_receipt = finished.production_jobs[wood_job_id]
            assert wood_receipt["status"] == "completed"
            assert wood_receipt["finished_at"] == 300
            assert wood_receipt["work_wage"]["amount"] == 2
            assert finished.resources[LUMBERYARD]["wood"] == 1
            assert finished.resources[LUMBERYARD]["coin_copper"] == 2
            assert finished.resources[PLAYER]["coin_copper"] == 4
            assert sum(stock.get("coin_copper", 0)
                       for stock in finished.resources.values()) == 8

            # The lumberyard wage can still fund a retry, isolating the
            # failure to exhausted timber rather than missing copper.
            rows_before = _event_rows(store)
            with pytest.raises(InvalidEvent, match="insufficient or unknown"):
                player.work(
                    WOODCUTTER_RECIPE, command_id="career-retry-empty-timber",
                    expected_revision=finished.revision,
                )
            assert store.verify(WORLD).to_dict() == finished.to_dict()
            assert _event_rows(store) == rows_before

            assert len(finished.production_jobs) == 2
            assert PLAYER not in finished.npcs
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


def test_carlos_can_select_two_funded_profession_contracts_deterministically(tmp_path):
    first_state, first_events = _run_world(tmp_path / "career01-first.sqlite")
    repeat_state, repeat_events = _run_world(tmp_path / "career01-repeat.sqlite")
    assert repeat_state == first_state
    assert repeat_events == first_events
