"""PLAY-43: buy real grain, carry it, deposit to workshop, bake and pay wages.

All monetary balances originate from finite, explicit t=0 wallets. Goods are
either t=0 physical grain or documented production output. Events, real road
journeys, trade receipts and SQLite replay are the source of truth.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, InvalidEvent, SQLiteEventStore, TimeEngine,
)
from carlos_sim.market import NPCMarketService
from carlos_sim.movement import NPCMovementService
from carlos_sim.production import NPCProductionService
from carlos_sim.workshop_transfers import NPCWorkshopService

WORLD = "play43-physical-grain-deposit"
FARM = "grain_farm"
BAKERY = "small_bakery"
BAKER = "basim"
FARMER = "nora"
CUSTOMER = "layla"


def _e(kind, data):
    return DomainEvent(kind, None, "trusted finite PLAY-43 setup", 0, data)


def _boot(db):
    db.create_world(WORLD)
    events = [
        _e("LocationCreated", {"id": FARM, "name": "Grain Farm"}),
        _e("LocationCreated", {"id": BAKERY, "name": "Bakery"}),
        _e("RouteCreated", {
            "id": "farm-bakery", "a": FARM, "b": BAKERY, "seconds": 60,
        }),
        _e("EntityCreated", {
            "id": FARMER, "name": "Nora", "location_id": FARM,
            "controller": "npc",
        }),
        _e("EntityCreated", {
            "id": BAKER, "name": "Basim", "location_id": BAKERY,
            "controller": "npc",
        }),
        _e("EntityCreated", {
            "id": CUSTOMER, "name": "Layla", "location_id": BAKERY,
            "controller": "npc",
        }),
    ]
    for who, role in ((FARMER, "farmer"), (BAKER, "baker"),
                      (CUSTOMER, "resident")):
        events.append(_e("NPCConfigured", {
            "npc_id": who, "role": role,
            "needs": {"hunger": 15, "fatigue": 0, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }))
    # Exactly 4 initial copper. Farm starts with a finite, owned grain lot.
    # Everything the baker subsequently uses has to be paid for and carried.
    starting_stock = {
        FARM: {"grain": 2, "coin_copper": 0},
        BAKERY: {"grain": 0, "food": 0, "oven": 1, "coin_copper": 0},
        BAKER: {"grain": 0, "food": 0, "coin_copper": 2},
        CUSTOMER: {"food": 0, "coin_copper": 2},
    }
    for owner, resources in starting_stock.items():
        for item, value in resources.items():
            events.append(_e("ResourceChanged", {
                "owner_id": owner, "resource": item, "previous": None,
                "current": value, "source": "initialization",
            }))
    events.extend([
        _e("MarketStallConfigured", {"site_id": FARM, "keeper_id": FARMER}),
        _e("MarketStallConfigured", {"site_id": BAKERY, "keeper_id": BAKER}),
        _e("ProductionRecipeConfigured", {
            "id": "grain-to-bread",
            "site_id": BAKERY, "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 2,
            "tool_resource": "oven", "duration_seconds": 90,
            "wage_coin": 2,
        }),
    ])
    return db.append(WORLD, "play43:bootstrap", 0, events, bootstrap=True)


def _cash(state):
    return sum(b.get("coin_copper", 0) for b in state.resources.values())


def _step(db, clock, seconds, label):
    now = db.load(WORLD)
    return clock.advance(
        WORLD, seconds=seconds, command_id="play43:clock:" + label,
        expected_revision=now.revision,
    ).state


def _physical_trip(db, clock, movement, destination, label):
    current = db.load(WORLD)
    here = current.entities[BAKER]["location_id"]
    assert {here, destination} == {FARM, BAKERY}
    result = movement.start(
        WORLD, BAKER, "farm-bakery", label, expected_revision=current.revision,
    )
    assert result.due == current.time + 60
    traveling = db.load(WORLD)
    assert traveling.entities[BAKER]["location_id"] == here
    with pytest.raises(InvalidEvent):
        NPCWorkshopService(db, clock).deposit(
            WORLD, BAKER, BAKERY, "grain", 1,
            command_id="teleport:" + label, expected_revision=traveling.revision,
        )
    landed = _step(db, clock, 60, label)
    assert landed.entities[BAKER]["location_id"] == destination
    assert db.verify(WORLD).to_dict() == landed.to_dict()
    return landed


def test_paid_grain_personal_bag_real_road_workshop_deposit_and_bread(tmp_path):
    with SQLiteEventStore(tmp_path / "grain-cycle.sqlite") as db:
        state = _boot(db)
        assert _cash(state) == 4
        assert state.resources[FARM]["grain"] == 2
        assert state.resources[BAKERY]["grain"] == 0
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            movement = NPCMovementService(db, clock)
            market = NPCMarketService(db, clock)
            workshop = NPCWorkshopService(db, clock)
            production = NPCProductionService(db, clock)

            state = db.append(
                WORLD, "play43:survey", state.revision,
                [DomainEvent(
                    "NPCNavigationSurveyed", BAKER, "baker sees local road",
                    state.time, {"npc_id": BAKER},
                )], movement_authorized=True,
            )
            state = _physical_trip(db, clock, movement, FARM, "outward")
            assert _cash(state) == 4
            offer = market.post(
                WORLD, FARMER, FARM, FARM, "grain-ask", "grain", 2,
                "coin_copper", 2, expected_revision=state.revision,
            )
            sale = market.buy(
                WORLD, BAKER, "grain-sale-1", "grain-ask", 1, 2,
                expected_revision=offer.state.revision,
            )
            state = sale.state
            assert state.resources[BAKER]["grain"] == 1
            assert state.resources[BAKERY]["grain"] == 0
            assert state.resources[FARM]["grain"] == 1
            assert state.resources[FARM]["coin_copper"] == 2
            assert state.resources[BAKER]["coin_copper"] == 0
            assert _cash(state) == 4

            state = _physical_trip(db, clock, movement, BAKERY, "return")
            before = db.verify(WORLD).to_dict()
            with pytest.raises(InvalidEvent):
                workshop.deposit(
                    WORLD, BAKER, FARM, "grain", 1,
                    command_id="far-farm", expected_revision=state.revision,
                )
            with pytest.raises(InvalidEvent):
                workshop.deposit(
                    WORLD, BAKER, BAKERY, "grain", 2,
                    command_id="overdraft", expected_revision=state.revision,
                )
            assert db.verify(WORLD).to_dict() == before
            state = workshop.deposit(
                WORLD, BAKER, BAKERY, "grain", 1,
                command_id="actual-delivery", expected_revision=state.revision,
            ).state
            assert state.resources[BAKER]["grain"] == 0
            assert state.resources[BAKERY]["grain"] == 1
            assert state.resources[BAKERY]["food"] == 0
            assert _cash(state) == 4

            job = production.start(
                WORLD, BAKER, "grain-to-bread", "bread-job-1",
                expected_revision=state.revision,
            )
            state = _step(db, clock, 90, "bread-done")
            assert state.production_jobs["bread-job-1"]["status"] == "completed"
            assert state.resources[BAKERY]["grain"] == 0
            assert state.resources[BAKERY]["food"] == 2
            assert _cash(state) == 4

            bread = market.post(
                WORLD, BAKER, BAKERY, BAKERY, "bread-ask", "food", 2,
                "coin_copper", 2, expected_revision=state.revision,
            )
            state = market.buy(
                WORLD, CUSTOMER, "bread-sale-1", "bread-ask", 1, 2,
                expected_revision=bread.state.revision,
            ).state
            assert state.resources[CUSTOMER]["food"] == 1
            assert state.resources[BAKERY]["food"] == 1
            assert state.resources[BAKERY]["coin_copper"] == 2
            assert state.resources[CUSTOMER]["coin_copper"] == 0
            assert _cash(state) == 4

            # A completed job may now be paid out of REAL new bakery income.
            state = db.append(
                WORLD, "play43:real-wage", state.revision,
                [DomainEvent(
                    "ProductionWagePaid", None,
                    "bread seller pays its employed baker from sold goods",
                    state.time, {"job_id": "bread-job-1", "amount": 2},
                )], production_authorized=True,
            )
            assert state.resources[BAKERY]["coin_copper"] == 0
            assert state.resources[BAKER]["coin_copper"] == 2
            assert _cash(state) == 4
            assert state.production_jobs["bread-job-1"]["work_wage"]["amount"] == 2
            assert db.verify(WORLD).to_dict() == state.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("amount", [0, -1, True, 1.5, "1", None, [], 1001])
def test_quantity_is_strict_and_atomic(tmp_path, amount):
    with SQLiteEventStore(tmp_path / "invalid.sqlite") as db:
        state = _boot(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            before = db.verify(WORLD).to_dict()
            with pytest.raises(InvalidEvent):
                NPCWorkshopService(db, clock).deposit(
                    WORLD, BAKER, BAKERY, "grain", amount,
                    command_id="invalid-quantity", expected_revision=state.revision,
                )
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


def test_no_unauthorized_material_deposits_or_remote_laundering(tmp_path):
    with SQLiteEventStore(tmp_path / "authorization.sqlite") as db:
        state = _boot(db)
        clock = TimeEngine(db)
        before = db.verify(WORLD).to_dict()
        event = DomainEvent(
            "WorkshopMaterialDeposited", BAKER, "forged material deposit", 0,
            {"site_id": BAKERY, "resource": "grain", "quantity": 1},
        )
        for market_cap, production_cap in (
            (False, False), (True, False), (False, True), (True, True),
        ):
            with pytest.raises(InvalidEvent):
                db.append(
                    WORLD, f"play43:closed-{market_cap}-{production_cap}",
                    state.revision, [event],
                    market_authorized=market_cap,
                    production_authorized=production_cap,
                )
        assert db.verify(WORLD).to_dict() == before
        clock.open_session(WORLD)
        try:
            for market_cap, production_cap in (
                (False, False), (True, False), (False, True),
            ):
                with pytest.raises(InvalidEvent):
                    db.append(
                        WORLD, f"play43:unauth-{market_cap}-{production_cap}",
                        state.revision, [event],
                        market_authorized=market_cap,
                        production_authorized=production_cap,
                    )
            for actor, site, item in (
                (FARMER, BAKERY, "grain"),
                (CUSTOMER, BAKERY, "grain"),
                (BAKER, FARM, "grain"),
                (BAKER, BAKERY, "coin_copper"),
                (BAKER, BAKERY, "food"),
            ):
                with pytest.raises(InvalidEvent):
                    db.append(
                        WORLD, f"play43:wrong-{actor}-{site}-{item}",
                        state.revision,
                        [DomainEvent(
                            "WorkshopMaterialDeposited", actor, "forged",
                            0, {"site_id": site, "resource": item, "quantity": 1},
                        )],
                        market_authorized=True, production_authorized=True,
                    )
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


def test_reserved_courier_cargo_is_not_laundered_through_workshop(tmp_path):
    """Reducer adversarial test: the courier's one consigned unit is not owned stock.

    This constructs a narrowly manipulated reducer input to verify the invariant,
    not a claim that the full synthetic state is a valid ordinary courier route.
    """
    from carlos_sim.workshop_transfers import deposit_workshop_material
    with SQLiteEventStore(tmp_path / "reserved-cargo.sqlite") as db:
        state = _boot(db).to_dict()
        state["supply_circuits"][BAKER] = {
            "carry": {"resource": "grain", "source": FARM, "destination": BAKERY},
        }
        # One grain in the depositor's ledger belongs to an existing consignment.
        state["resources"][BAKER]["grain"] = 1
        event = DomainEvent(
            "WorkshopMaterialDeposited", BAKER,
            "adversarial attempt to launder courier grain", 0,
            {"site_id": BAKERY, "resource": "grain", "quantity": 1},
        )
        with pytest.raises(ValueError, match="reserved courier cargo"):
            deposit_workshop_material(state, event, authorized=True)
        assert state["resources"][BAKER]["grain"] == 1
        assert state["resources"][BAKERY]["grain"] == 0

        # If the courier additionally owns a second, unreserved grain unit,
        # only that genuine personal surplus can be deposited.
        state["resources"][BAKER]["grain"] = 2
        deposit_workshop_material(state, event, authorized=True)
        assert state["resources"][BAKER]["grain"] == 1
        assert state["resources"][BAKERY]["grain"] == 1
