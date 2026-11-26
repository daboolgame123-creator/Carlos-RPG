"""READ-PLAY: a player-only paid baking job using real site inputs."""
from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCMarketService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import DuplicateCommand, InvalidEvent, UnsupportedVersion
from carlos_sim.domain import canonical, canonical_hash


WORLD = "player-baker"
PLAYER = "carlos"
BAKERY = "bakery"
RECIPE_ID = "grain-to-bread"


def _event(kind, data, *, actor=None):
    return DomainEvent(kind, actor, "bounded player baker fixture", 0, data)


def _setup(store, *, grain=2, site_copper=2, player_location=BAKERY,
           contract_worker=PLAYER, needs=False, market=False):
    store.create_world(WORLD)
    events = [
        _event("LocationCreated", {"id": BAKERY, "name": "Bakery"}),
        _event("LocationCreated", {"id": "square", "name": "Square"}),
        _event("EntityCreated", {"id": PLAYER, "name": "Carlos",
                                  "controller": "player",
                                  "location_id": player_location}),
        _event("EntityCreated", {"id": "basim", "name": "Basim",
                                  "controller": "npc", "location_id": BAKERY}),
        _event("NPCConfigured", {
            "npc_id": "basim", "role": "baker",
            "needs": {"hunger": 10, "fatigue": 5, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }),
        _event("RouteCreated", {"id": "square-bakery", "a": "square",
                                 "b": BAKERY, "seconds": 30}),
    ]
    for owner, resource, amount in (
        (BAKERY, "grain", grain), (BAKERY, "food", 0),
        (BAKERY, "oven", 1), (BAKERY, "coin_copper", site_copper),
        (PLAYER, "coin_copper", 0), (PLAYER, "food", 0),
        ("basim", "labor_units", 0),
        ("basim", "investigation_attempts", 0),
    ):
        events.append(_event("ResourceChanged", {
            "owner_id": owner, "resource": resource, "previous": None,
            "current": amount, "source": "initialization",
        }))
    events.append(_event("ProductionRecipeConfigured", {
        "id": RECIPE_ID, "site_id": BAKERY, "role": "baker",
        "input_resource": "grain", "input_amount": 1,
        "output_resource": "food", "output_amount": 2,
        "tool_resource": "oven", "duration_seconds": 90,
        "wage_coin": 2, "player_worker_id": contract_worker,
    }))
    if needs:
        events.append(_event("PlayerNeedsInitialized", {
            "player_id": PLAYER, "hunger": 50, "fatigue": 25,
        }))
    if market:
        events.append(_event("MarketStallConfigured", {
            "site_id": BAKERY, "keeper_id": "basim",
        }))
    store.append(WORLD, "player-baker-bootstrap", 0, events, bootstrap=True)


def _gateway(store, *, engine=None):
    clock = TimeEngine(store)
    clock.open_session(WORLD)
    gateway = PlayerGateway(
        store, clock, world_id=WORLD, player_id=PLAYER,
        engine=engine if engine is not None else LivingWorldEngine(store, clock),
    )
    return clock, gateway


def test_player_baking_repeats_with_physical_inputs_and_funded_wages(tmp_path):
    path = tmp_path / "player-baker.sqlite"
    with SQLiteEventStore(path) as store:
        # Finite fixture stock funds exactly two jobs; it is not generated
        # during play and cannot pay a third job.
        _setup(store, grain=2, site_copper=4)
        clock, gateway = _gateway(store)
        try:
            before = store.load(WORLD)
            with pytest.raises(InvalidEvent):
                store.append(
                    WORLD, "npc-claims-player-contract", before.revision,
                    [DomainEvent(
                        "ProductionStarted", "basim", "forged player contract use", 0,
                        {"id": "stolen-job", "recipe_id": RECIPE_ID,
                         "npc_id": "basim"})], production_authorized=True)
            assert store.load(WORLD).to_dict() == before.to_dict()
            started = gateway.work(
                RECIPE_ID, command_id="bake-one",
                expected_revision=before.revision,
            )
            running = store.load(WORLD)
            job = running.production_jobs[started.details["job_id"]]
            assert started.status == "production_started"
            assert job["npc_id"] == PLAYER  # worker ID; Carlos remains a player.
            assert job["due"] == 90 and job["status"] == "running"
            assert running.entities[PLAYER]["location_id"] == BAKERY
            assert PLAYER not in running.npcs
            assert running.resources[BAKERY]["grain"] == 1
            assert running.resources[BAKERY]["food"] == 0

            with pytest.raises(DuplicateCommand):
                gateway.work(RECIPE_ID, command_id="bake-one",
                             expected_revision=running.revision)
            with pytest.raises(ValueError, match="working"):
                gateway.rest(command_id="rest-during-bake",
                             expected_revision=running.revision)
            with pytest.raises(ValueError, match="busy working"):
                gateway.move("square-bakery", command_id="move-during-bake",
                             expected_revision=running.revision)
            with pytest.raises(ValueError, match="busy working"):
                gateway.forage(command_id="forage-during-bake",
                               expected_revision=running.revision)
            with pytest.raises(ValueError, match="busy working"):
                gateway.eat(command_id="eat-during-bake",
                            expected_revision=running.revision)
            assert store.load(WORLD).to_dict() == running.to_dict()

            gateway.wait(89, command_id="bake-wait-89",
                         expected_revision=running.revision)
            almost = store.load(WORLD)
            assert almost.time == 89
            assert almost.resources[BAKERY]["food"] == 0
            assert almost.resources[PLAYER]["coin_copper"] == 0

            gateway.wait(1, command_id="bake-wait-90",
                         expected_revision=almost.revision)
            finished = store.verify(WORLD)
            receipt = finished.production_jobs[started.details["job_id"]]
            assert receipt["status"] == "completed"
            assert receipt["finished_at"] == 90
            assert receipt["work_wage"]["amount"] == 2
            assert receipt["work_wage"]["worker_id"] == PLAYER
            assert finished.resources[BAKERY]["grain"] == 1
            assert finished.resources[BAKERY]["food"] == 2
            assert finished.resources[BAKERY]["coin_copper"] == 2
            assert finished.resources[PLAYER]["coin_copper"] == 2
            assert (finished.resources[BAKERY]["coin_copper"]
                    + finished.resources[PLAYER]["coin_copper"]) == 4
            assert PLAYER not in finished.npcs
            assert finished.to_dict() == store.load(WORLD).to_dict()

            # The player explicitly starts the second funded job. Waiting by
            # itself does not order more work or change the NPC roster.
            second = gateway.work(
                RECIPE_ID, command_id="bake-two",
                expected_revision=finished.revision,
            )
            second_running = store.load(WORLD)
            assert len(second_running.production_jobs) == 2
            assert second_running.production_jobs[second.details["job_id"]]["due"] == 180
            assert second_running.resources[BAKERY]["grain"] == 0
            assert second_running.resources[BAKERY]["food"] == 2
            assert second_running.resources[BAKERY]["coin_copper"] == 2
            assert second_running.resources[PLAYER]["coin_copper"] == 2
            gateway.wait(89, command_id="bake-two-wait-89",
                         expected_revision=second_running.revision)
            second_almost = store.load(WORLD)
            assert second_almost.time == 179
            assert second_almost.resources[BAKERY]["food"] == 2
            assert second_almost.resources[PLAYER]["coin_copper"] == 2
            gateway.wait(1, command_id="bake-two-wait-90",
                         expected_revision=second_almost.revision)
            finished = store.verify(WORLD)
            second_receipt = finished.production_jobs[second.details["job_id"]]
            assert second_receipt["status"] == "completed"
            assert second_receipt["finished_at"] == 180
            assert second_receipt["work_wage"]["worker_id"] == PLAYER
            assert finished.resources[BAKERY]["grain"] == 0
            assert finished.resources[BAKERY]["food"] == 4
            assert finished.resources[BAKERY]["coin_copper"] == 0
            assert finished.resources[PLAYER]["coin_copper"] == 4
            assert sum(finished.resources[owner]["coin_copper"]
                       for owner in (BAKERY, PLAYER)) == 4
            assert len(finished.production_jobs) == 2

            with pytest.raises(InvalidEvent, match="wage to be locally funded"):
                gateway.work(RECIPE_ID, command_id="unfunded-third-bake",
                             expected_revision=finished.revision)
            assert store.load(WORLD).to_dict() == finished.to_dict()
            with pytest.raises(InvalidEvent, match="exactly once"):
                store.append(
                    WORLD, "duplicate-player-wage", finished.revision,
                    [DomainEvent(
                        "ProductionWagePaid", None, "forged duplicate wage",
                        finished.time,
                    {"job_id": started.details["job_id"], "amount": 2})],
                    production_authorized=True)
            assert store.load(WORLD).to_dict() == finished.to_dict()
            store.snapshot(WORLD)
            assert store.verify(WORLD).to_dict() == finished.to_dict()
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(path) as reopened:
        assert reopened.verify(WORLD).to_dict() == finished.to_dict()


@pytest.mark.parametrize("copper,worker,expected", [
    (0, PLAYER, "full wage at signing"),
    (2, "ghost", "player work contract"),
])
def test_player_contract_rejects_missing_material_funding_or_wrong_worker(
        tmp_path, copper, worker, expected):
    with SQLiteEventStore(tmp_path / f"invalid-{copper}-{worker}.sqlite") as store:
        store.create_world(WORLD)
        base = [
            _event("LocationCreated", {"id": BAKERY, "name": "Bakery"}),
            _event("EntityCreated", {"id": PLAYER, "name": "Carlos",
                                      "controller": "player", "location_id": BAKERY}),
        ]
        base.extend(_event("ResourceChanged", {
            "owner_id": BAKERY, "resource": item, "previous": None,
            "current": quantity, "source": "initialization",
        }) for item, quantity in (("grain", 2), ("food", 0),
                                  ("oven", 1), ("coin_copper", copper)))
        store.append(WORLD, "invalid-base", 0, base, bootstrap=True)
        state = store.load(WORLD)
        contract = _event("ProductionRecipeConfigured", {
            "id": RECIPE_ID, "site_id": BAKERY, "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 2,
            "tool_resource": "oven", "duration_seconds": 90,
            "wage_coin": 2, "player_worker_id": worker,
        })
        with pytest.raises(InvalidEvent, match=expected):
            store.append(WORLD, "invalid-contract", state.revision,
                         [contract], bootstrap=True)
        assert store.load(WORLD).to_dict() == state.to_dict()


def test_player_cannot_start_without_real_local_inputs(tmp_path):
    with SQLiteEventStore(tmp_path / "no-grain.sqlite") as store:
        _setup(store, grain=0)
        clock, gateway = _gateway(store)
        try:
            before = store.load(WORLD)
            with pytest.raises(InvalidEvent):
                gateway.work(RECIPE_ID, command_id="no-grain",
                             expected_revision=before.revision)
            assert store.load(WORLD).to_dict() == before.to_dict()
            assert store.verify(WORLD).to_dict() == before.to_dict()
        finally:
            clock.close_session(WORLD)


def test_player_cannot_start_npc_recipe_or_work_from_another_site(tmp_path):
    with SQLiteEventStore(tmp_path / "boundaries.sqlite") as store:
        _setup(store, player_location="square")
        clock, gateway = _gateway(store)
        try:
            state = store.load(WORLD)
            with pytest.raises(PermissionError, match="contract"):
                gateway.work("unknown-recipe", command_id="wrong-recipe",
                             expected_revision=state.revision)
            with pytest.raises(ValueError, match="physically present"):
                gateway.work(RECIPE_ID, command_id="wrong-site",
                             expected_revision=state.revision)
            assert store.load(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


def test_earned_wage_buys_real_food_that_player_eats_before_rest(tmp_path):
    with SQLiteEventStore(tmp_path / "paid-food-loop.sqlite") as store:
        _setup(store, grain=1, site_copper=2, needs=True, market=True)
        clock = TimeEngine(store)
        clock.open_session(WORLD)
        gateway = PlayerGateway(
            store, clock, world_id=WORLD, player_id=PLAYER,
            engine=LivingWorldEngine(store, clock, decision_cooldown=300),
        )
        try:
            started = gateway.work(
                RECIPE_ID, command_id="earn-food-wage",
                expected_revision=store.load(WORLD).revision,
            )
            gateway.wait(90, command_id="finish-food-wage",
                         expected_revision=store.load(WORLD).revision)
            earned = store.verify(WORLD)
            assert earned.resources[PLAYER]["coin_copper"] == 2
            assert earned.resources[BAKERY]["food"] == 2
            assert earned.production_jobs[started.details["job_id"]]["work_wage"]["amount"] == 2

            # Basim's own autonomous task keeps running while Carlos works;
            # wait for the real steward to become available before posting.
            gateway.wait(90, command_id="wait-for-steward",
                         expected_revision=earned.revision)
            market = NPCMarketService(store, clock)
            market.post(
                WORLD, "basim", BAKERY, BAKERY, "baked-food-for-sale",
                "food", 2, "coin_copper", 1,
                expected_revision=store.load(WORLD).revision,
            )
            purchased = gateway.buy(
                "baked-food-for-sale", 1, 1,
                command_id="buy-from-earned-wage",
                expected_revision=store.load(WORLD).revision,
            )
            assert purchased.details["total_paid"] == 1
            bought = store.load(WORLD)
            assert bought.resources[PLAYER]["coin_copper"] == 1
            assert bought.resources[PLAYER]["food"] == 1
            assert bought.resources[BAKERY]["coin_copper"] == 1
            assert bought.resources[BAKERY]["food"] == 1

            meal = gateway.eat(
                "food", command_id="eat-bought-food",
                expected_revision=bought.revision,
            )
            eaten = store.load(WORLD)
            assert meal.status == "ate"
            assert eaten.player_needs[PLAYER]["hunger"] == 15
            assert eaten.resources[PLAYER]["food"] == 0
            assert eaten.resources[BAKERY]["food"] == 1
            assert (eaten.resources[PLAYER]["coin_copper"]
                    + eaten.resources[BAKERY]["coin_copper"]) == 2

            gateway.rest(command_id="rest-after-work-and-meal",
                         expected_revision=eaten.revision)
            resting = store.load(WORLD)
            gateway.wait(1_799, command_id="almost-finished-rest",
                         expected_revision=resting.revision)
            almost = store.load(WORLD)
            assert almost.player_needs[PLAYER]["fatigue"] == 25
            gateway.wait(1, command_id="finish-rest-after-work",
                         expected_revision=almost.revision)
            rested = store.verify(WORLD)
            assert rested.time == 1_980
            assert rested.player_needs[PLAYER]["fatigue"] == 5
            assert rested.player_needs[PLAYER]["hunger"] == 21
            assert rested.resources[PLAYER]["coin_copper"] == 1
            assert rested.resources[BAKERY]["coin_copper"] == 1
            assert store.load(WORLD).to_dict() == rested.to_dict()
        finally:
            clock.close_session(WORLD)


def test_rules72_world_is_rejected_without_rewriting_saved_bytes(tmp_path):
    path = tmp_path / "rules72.sqlite"
    with SQLiteEventStore(path) as store:
        store.create_world("old")
        state = store.load("old").to_dict()
    old = dict(state, rules_version=72)
    with sqlite3.connect(path) as raw:
        raw.execute(
            "UPDATE worlds SET rules_version=?, initial_state=?, initial_hash=? WHERE id=?",
            (72, canonical(old), canonical_hash(old), "old"),
        )
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as store:
        for read in (store.load, store.verify):
            with pytest.raises(UnsupportedVersion, match="schema/rules mismatch"):
                read("old")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with sqlite3.connect(path) as raw:
        saved = json.loads(raw.execute(
            "SELECT initial_state FROM worlds WHERE id='old'"
        ).fetchone()[0])
        assert saved == old
