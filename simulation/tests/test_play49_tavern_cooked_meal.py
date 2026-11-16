"""PLAY49-D isolated tavern recipe: actual orchard fruit + dairy cheese -> one food.

A real local cook buys two previously sourced goods from a travelling trader,
deposits BOTH from personally owned inventory, then completes timed compound
preparation. A genuine customer's payment funds one post-sale cook wage.
One actual owned food meal may be eaten; no free ingredients or money.
This is a deterministic TEST fixture, not autonomous village economics.
"""
import pytest

from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCMarketService,
    NPCProductionService, NPCMovementService, NPCConsumptionService,
)
from carlos_sim.workshop_transfers import NPCWorkshopService
from carlos_sim.store import InvalidEvent
from test_market_02c import ev, prepare, _rev
from test_play49_fruit_stall_contract import WORLD, add_orchard, copper
from test_play49_dairy_stall_contract import add_dairy, produce, pay_both, post_three
from test_play49_tavern_trade_provenance import add_tavern, source_goods, walk, post_tavern


def add_actual_kitchen(db):
    """Five of Salma's original opening 10 coins go to a real cook, not mint."""
    old = db.load(WORLD)
    assert old.time == 0
    assert old.resources["salma"]["coin_copper"] == 5
    assert old.resources["tavern"]["coin_copper"] == 0
    actions = [
        ev("EntityCreated", {
            "id": "tavern_cook", "name": "Village Cook",
            "location_id": "tavern", "controller": "npc"}),
        ev("NPCConfigured", {
            "npc_id": "tavern_cook", "role": "cook",
            "needs": {"hunger": 20, "fatigue": 0, "safety": 0},
            "goals": {"earn": 50, "explore": 10, "survive": 30}}),
    ]
    for owner, resource, amount in (
        ("tavern", "food", 0), ("tavern", "hearth", 1),
        ("tavern_cook", "fruit", 0), ("tavern_cook", "cheese", 0),
        ("tavern_cook", "coin_copper", 5),
        ("salma", "food", 0),
    ):
        actions.append(ev("ResourceChanged", {
            "owner_id": owner, "resource": resource, "previous": None,
            "current": amount, "source": "initialization",
        }))
    actions.append(ev("ProductionRecipeConfigured", {
        "id": "fruit-cheese-hot-plate", "site_id": "tavern", "role": "cook",
        "inputs": [
            {"resource": "fruit", "amount": 1},
            {"resource": "cheese", "amount": 1},
        ],
        "output_resource": "food", "output_amount": 1,
        "tool_resource": "hearth", "duration_seconds": 300, "wage_coin": 1,
    }))
    cooked = db.append(WORLD, "tavern:real-kitchen-opening", old.revision,
                       actions, bootstrap=True)
    assert copper(cooked) == copper(old) + 5
    assert cooked.resources["tavern"]["food"] == 0
    assert cooked.resources["tavern"]["fruit"] == cooked.resources["tavern"]["cheese"] == 0
    assert cooked.resources["tavern"]["coin_copper"] == 0
    assert cooked.resources["tavern_cook"]["coin_copper"] == 5
    assert db.verify(WORLD).to_dict() == cooked.to_dict()


@pytest.fixture
def kitchen(tmp_path):
    with SQLiteEventStore(tmp_path / "play49-cooked-tavern.sqlite") as db:
        # Earlier fixture starts Salma with 10 copper. Reassign 5 of THOSE
        # to the added cook at time-zero (5 + 5 = original 10), not a gift.
        prepare(db, copper_buyer=5)
        add_orchard(db)
        add_dairy(db)
        add_tavern(db)
        add_actual_kitchen(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            yield db, clock, NPCMarketService(db, clock)
        finally:
            clock.close_session(WORLD)


def source_and_buy_for_cook(db, clock, market, *, split=False):
    """Huda brings actual fruit/cheese, paid from cook's own finite wallet."""
    opening = source_goods(db, clock, market, split=split)
    walk(db, clock, "huda", "dairy-tavern", "real-chef-supply", 60, split=split)
    post_tavern(db, market)
    state = db.load(WORLD)
    assert state.resources["tavern"]["fruit"] == state.resources["tavern"]["cheese"] == 0
    assert market.local_quotes(WORLD, "tavern_cook")
    market.buy(WORLD, "tavern_cook", "cook-buys-fruit",
               "tavern-fruit-quote", 1, 2, expected_revision=_rev(db))
    bought = market.buy(WORLD, "tavern_cook", "cook-buys-cheese",
                        "tavern-cheese-quote", 1, 3,
                        expected_revision=_rev(db)).state
    assert bought.resources["huda"]["coin_copper"] == 12
    assert bought.resources["tavern_cook"]["coin_copper"] == 0
    assert bought.resources["tavern_cook"]["fruit"] == 1
    assert bought.resources["tavern_cook"]["cheese"] == 1
    assert bought.resources["tavern"]["fruit"] == bought.resources["tavern"]["cheese"] == 0
    assert copper(bought) == copper(opening)
    return opening


def deposit_ingredients(db, clock):
    shop = NPCWorkshopService(db, clock)
    for item in ("fruit", "cheese"):
        shop.deposit(WORLD, "tavern_cook", "tavern", item, 1,
                     command_id="cook-deposits-" + item,
                     expected_revision=_rev(db))
    placed = db.load(WORLD)
    assert placed.resources["tavern"]["fruit"] == 1
    assert placed.resources["tavern"]["cheese"] == 1
    assert placed.resources["tavern_cook"]["fruit"] == 0
    assert placed.resources["tavern_cook"]["cheese"] == 0
    assert db.verify(WORLD).to_dict() == placed.to_dict()


def cook_real_meal(db, clock, *, split=False):
    NPCProductionService(db, clock).start(
        WORLD, "tavern_cook", "fruit-cheese-hot-plate", "real-hot-plate",
        expected_revision=_rev(db))
    started = db.load(WORLD)
    assert started.resources["tavern"]["fruit"] == 0
    assert started.resources["tavern"]["cheese"] == 0
    assert started.resources["tavern"]["food"] == 0
    parts = [150, 150] if split else [300]
    for i, amount in enumerate(parts):
        clock.advance(WORLD, seconds=amount,
                      command_id="hot-plate:time-"+str(i), expected_revision=_rev(db))
    cooked = db.load(WORLD)
    assert cooked.resources["tavern"]["food"] == 1
    assert cooked.production_jobs["real-hot-plate"]["status"] == "completed"
    receipt = cooked.production_jobs["real-hot-plate"]
    assert receipt["input_before_by_resource"] == {"fruit": 1, "cheese": 1}
    assert receipt["input_after_by_resource"] == {"fruit": 0, "cheese": 0}
    assert db.verify(WORLD).to_dict() == cooked.to_dict()
    return cooked


def finish_sale_wage_and_eat(db, clock, market, opening, *, split=False):
    done = cook_real_meal(db, clock, split=split)
    assert done.resources["tavern"]["coin_copper"] == 0
    # A signed wage is NOT a free payout; no employer revenue exists yet.
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "cook:early-unfunded-pay", done.revision, [
            DomainEvent("ProductionWagePaid", None, "unfunded employer",
                        done.time, {"job_id": "real-hot-plate", "amount": 1}),
        ], production_authorized=True)
    assert db.verify(WORLD).to_dict() == done.to_dict()

    market.post(WORLD, "tavern_host", "tavern", "tavern", "cooked-food-quote",
                "food", 1, "coin_copper", 3, expected_revision=_rev(db))
    walk(db, clock, "salma", "bakery-tavern", "salma-comes-for-a-real-meal",
         80, split=split)
    bought = market.buy(WORLD, "salma", "real-cooked-food-sale",
                        "cooked-food-quote", 1, 3,
                        expected_revision=_rev(db)).state
    assert bought.resources["tavern"]["food"] == 0
    assert bought.resources["salma"]["food"] == 1
    assert bought.resources["salma"]["coin_copper"] == opening.resources["salma"]["coin_copper"] - 3
    assert bought.resources["tavern"]["coin_copper"] == 3
    paid = db.append(WORLD, "cook:real-post-sale-wage", bought.revision, [
        DomainEvent("ProductionWagePaid", None, "sale-backed local cook wage",
                    bought.time, {"job_id": "real-hot-plate", "amount": 1}),
    ], production_authorized=True)
    assert paid.resources["tavern"]["coin_copper"] == 2
    assert paid.resources["tavern_cook"]["coin_copper"] == 1
    assert paid.production_jobs["real-hot-plate"]["work_wage"]["amount"] == 1

    ate = NPCConsumptionService(db, clock).eat(
        WORLD, "salma", 1, command_id="salma-eats-real-hot-plate",
        expected_revision=_rev(db))
    state = ate.state
    assert ate.consumed_quantity == 1
    assert state.resources["salma"]["food"] == 0
    assert state.npcs["salma"]["needs"]["hunger"] == 0
    assert state.consumptions[ate.id]["hunger_before"] == 20
    assert state.consumptions[ate.id]["hunger_after"] == 0
    assert copper(state) == copper(opening)
    assert db.verify(WORLD).to_dict() == state.to_dict()
    return state


def test_actual_paid_kitchen_plate_customer_and_no_new_currency(kitchen):
    db, clock, market = kitchen
    opening = db.load(WORLD)
    assert opening.resources["salma"]["coin_copper"] == opening.resources["tavern_cook"]["coin_copper"] == 5
    assert copper(opening) == 22  # Huda 10 + Salma/cook (5+5) + orchard 1 + dairy 1
    source_and_buy_for_cook(db, clock, market)
    deposit_ingredients(db, clock)
    finished = finish_sale_wage_and_eat(db, clock, market, opening)
    assert len(finished.market_stalls) == 4
    assert len(finished.market_trades) == 4
    assert finished.market_trades["real-cooked-food-sale"]["stock_owner_id"] == "tavern"
    assert finished.resources["huda"]["coin_copper"] == 12
    assert finished.resources["cheese_maker"]["coin_copper"] == 1
    assert finished.resources["fruit_farmer"]["coin_copper"] == 1
    assert finished.resources["tavern"]["coin_copper"] == 2
    assert finished.resources["tavern_cook"]["coin_copper"] == 1
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == finished.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not db.db.execute("PRAGMA foreign_key_check").fetchall()


def test_no_meal_before_ingredients_and_untrusted_workshop_deposit_rejected(kitchen):
    db, clock, market = kitchen
    initial = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        NPCProductionService(db, clock).start(
            WORLD, "tavern_cook", "fruit-cheese-hot-plate", "imaginary-meal",
            expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "tavern_host", "tavern", "tavern", "phantom-meal",
                    "food", 1, "coin_copper", 3, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == initial.to_dict()

    source_and_buy_for_cook(db, clock, market)
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "fake-unauthorized-deposit", before.revision, [
            DomainEvent("WorkshopMaterialDeposited", "tavern_cook",
                        "wrong capabilities", before.time, {
                            "site_id": "tavern", "resource": "fruit", "quantity": 1
                        })
        ], production_authorized=True)
    with pytest.raises(InvalidEvent):
        NPCWorkshopService(db, clock).deposit(
            WORLD, "tavern_host", "tavern", "fruit", 1,
            command_id="seller-steals-food", expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        NPCWorkshopService(db, clock).deposit(
            WORLD, "tavern_cook", "tavern", "fruit", 2,
            command_id="fake-second-fruit", expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()


def test_no_unfinished_meal_sale_and_no_duplicate_wage_or_eating(kitchen):
    db, clock, market = kitchen
    opening = db.load(WORLD)
    source_and_buy_for_cook(db, clock, market)
    deposit_ingredients(db, clock)
    NPCProductionService(db, clock).start(
        WORLD, "tavern_cook", "fruit-cheese-hot-plate", "real-hot-plate",
        expected_revision=_rev(db))
    running = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.post(WORLD, "tavern_host", "tavern", "tavern",
                    "unbaked-instant-food", "food", 1, "coin_copper", 3,
                    expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == running.to_dict()
    clock.advance(WORLD, seconds=300, command_id="finish-before-real-sale",
                  expected_revision=_rev(db))
    market.post(WORLD, "tavern_host", "tavern", "tavern", "cooked-food-quote",
                "food", 1, "coin_copper", 3, expected_revision=_rev(db))
    walk(db, clock, "salma", "bakery-tavern", "salma-comes-for-a-real-meal", 80)
    bought = market.buy(WORLD, "salma", "real-cooked-food-sale",
                        "cooked-food-quote", 1, 3, expected_revision=_rev(db)).state
    assert bought.resources["tavern"]["coin_copper"] == 3
    paid = db.append(WORLD, "cook:real-post-sale-wage", bought.revision, [
        DomainEvent("ProductionWagePaid", None, "funded finished job wage",
                    bought.time, {"job_id": "real-hot-plate", "amount": 1})
    ], production_authorized=True)
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "cook:second-payment", paid.revision, [
            DomainEvent("ProductionWagePaid", None, "double wage",
                        paid.time, {"job_id": "real-hot-plate", "amount": 1})
        ], production_authorized=True)
    ate = NPCConsumptionService(db, clock).eat(
        WORLD, "salma", 1, command_id="salma-eats-real-hot-plate",
        expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        NPCConsumptionService(db, clock).eat(
            WORLD, "salma", 1, command_id="salma-eats-twice",
            expected_revision=_rev(db))
    assert copper(ate.state) == copper(opening)
    assert db.verify(WORLD).to_dict() == ate.state.to_dict()


def test_clock_partition_invariant_real_recipe_and_sale(tmp_path):
    seen = []
    for label, split in (("one", False), ("split", True)):
        with SQLiteEventStore(tmp_path / f"{label}.sqlite") as db:
            prepare(db, copper_buyer=5)
            add_orchard(db)
            add_dairy(db)
            add_tavern(db)
            add_actual_kitchen(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            market = NPCMarketService(db, clock)
            opening = db.load(WORLD)
            source_and_buy_for_cook(db, clock, market, split=split)
            deposit_ingredients(db, clock)
            finished = finish_sale_wage_and_eat(
                db, clock, market, opening, split=split)
            seen.append((finished.time, finished.resources,
                         finished.market_trades,
                         finished.production_jobs,
                         finished.consumptions))
            assert db.verify(WORLD).to_dict() == finished.to_dict()
    assert seen[0] == seen[1]
