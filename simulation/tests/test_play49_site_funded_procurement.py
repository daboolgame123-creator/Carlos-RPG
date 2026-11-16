"""PLAY49-G: site-owned cash buys another fully physical tavern input batch.

Isolated prototype of owner-backed local purchasing; no invented copper,
no remote quotes, no personal-cash laundering, no perpetual food stock.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, NPCConsumptionService, NPCMarketService,
    NPCMovementService, NPCProductionService, SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import InvalidEvent
from test_market_02c import ev, prepare, _rev
from test_play49_fruit_stall_contract import WORLD, add_orchard, copper
from test_play49_dairy_stall_contract import add_dairy
from test_play49_tavern_trade_provenance import add_tavern, walk
from test_play49_tavern_cooked_meal import (
    add_actual_kitchen, source_and_buy_for_cook, deposit_ingredients,
    cook_real_meal,
)

def _setup(db):
    prepare(db, copper_buyer=5)
    # Only an extra finite opening batch of REAL inputs; no runtime minting.
    add_orchard(db, ready_stock=2)
    add_dairy(db, milk_stock=4)
    add_tavern(db)
    add_actual_kitchen(db)
    s = db.load(WORLD)
    db.append(WORLD, "site-procurement:known-huda-food", s.revision, [
        ev("ResourceChanged", {
            "owner_id": "huda", "resource": "food",
            "previous": None, "current": 0, "source": "initialization"}),
    ], bootstrap=True)
    assert copper(db.load(WORLD)) == 22

@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path / "two-real-tavern-plates.sqlite") as db:
        _setup(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            yield db, clock, NPCMarketService(db, clock)
        finally:
            clock.close_session(WORLD)

def _first_real_plate(db, clock, market):
    opening = db.load(WORLD)
    source_and_buy_for_cook(db, clock, market)
    deposit_ingredients(db, clock)
    cook_real_meal(db, clock)
    market.post(WORLD, "tavern_host", "tavern", "tavern",
                "first-real-plate", "food", 1, "coin_copper", 6,
                expected_revision=_rev(db))
    first = market.buy(WORLD, "huda", "first-plate-sale",
                       "first-real-plate", 1, 6,
                       expected_revision=_rev(db)).state
    assert first.resources["tavern"]["coin_copper"] == 6
    signed = db.append(WORLD, "first-earned-cook-wage", first.revision, [
        DomainEvent("ProductionWagePaid", None, "first completed hot plate wage",
                    first.time, {"job_id": "real-hot-plate", "amount": 1}),
    ], production_authorized=True)
    assert signed.resources["tavern"]["coin_copper"] == 5
    assert signed.resources["tavern_cook"]["coin_copper"] == 1
    ate = NPCConsumptionService(db, clock).eat(
        WORLD, "huda", 1, command_id="huda-eats-first-plate",
        expected_revision=_rev(db)).state
    assert ate.resources["huda"]["food"] == 0
    assert ate.npcs["huda"]["needs"]["hunger"] == 0
    assert ate.resources["huda"]["coin_copper"] == 6
    assert copper(ate) == copper(opening)
    return opening

def _second_authentic_goods(db, clock, market):
    prod = NPCProductionService(db, clock)
    prod.start(WORLD, "fruit_farmer", "fruit-picking",
               "fruit-second-batch", expected_revision=_rev(db))
    prod.start(WORLD, "cheese_maker", "milk-to-cheese",
               "cheese-second-batch", expected_revision=_rev(db))
    clock.advance(WORLD, seconds=180, command_id="two-authentic-second-batches",
                  expected_revision=_rev(db))
    state = db.load(WORLD)
    assert state.production_jobs["fruit-second-batch"]["status"] == "completed"
    assert state.production_jobs["cheese-second-batch"]["status"] == "completed"
    assert state.resources["orchard"]["fruit"] == 1
    assert state.resources["dairy"]["cheese"] == 1
    assert state.resources["orchard"]["fruit_ready"] == 0
    assert state.resources["dairy"]["milk"] == 0

    market.post(WORLD, "fruit_seller", "orchard", "orchard",
                "second-fruit-quote", "fruit", 1, "coin_copper", 1,
                expected_revision=_rev(db))
    market.post(WORLD, "cheese_seller", "dairy", "dairy",
                "second-cheese-quote", "cheese", 1, "coin_copper", 2,
                expected_revision=_rev(db))
    # Huda is at tavern. Real travel is required to buy at both distant shops.
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.buy(WORLD, "huda", "remote-second-cheese",
                   "second-cheese-quote", 1, 2, expected_revision=_rev(db))
    assert db.load(WORLD).to_dict() == before.to_dict()
    walk(db, clock, "huda", "dairy-tavern", "huda-back-to-dairy", 60)
    market.buy(WORLD, "huda", "second-cheese-wholesale",
               "second-cheese-quote", 1, 2, expected_revision=_rev(db))
    walk(db, clock, "huda", "orchard-dairy", "huda-back-to-orchard", 70)
    market.buy(WORLD, "huda", "second-fruit-wholesale",
               "second-fruit-quote", 1, 1, expected_revision=_rev(db))
    walk(db, clock, "huda", "orchard-dairy", "huda-back-to-dairy", 70)
    walk(db, clock, "huda", "dairy-tavern", "huda-returns-with-goods", 60)

    goods = db.load(WORLD)
    assert goods.resources["huda"]["fruit"] == 1
    assert goods.resources["huda"]["cheese"] == 1
    assert goods.resources["huda"]["coin_copper"] == 3
    market.post(WORLD, "huda", "huda", "tavern",
                "second-tavern-fruit", "fruit", 1, "coin_copper", 2,
                expected_revision=_rev(db))
    market.post(WORLD, "huda", "huda", "tavern",
                "second-tavern-cheese", "cheese", 1, "coin_copper", 3,
                expected_revision=_rev(db))
    return db.load(WORLD)

def _make_second_meal(db, clock, market):
    # Employee and venue have *different* wallets: all 5 coins move out of
    # the actual venue ledger directly to the actual owner of the merchandise.
    old = db.load(WORLD)
    assert old.resources["tavern"]["coin_copper"] == 5
    assert old.resources["tavern_cook"]["coin_copper"] == 1
    market.buy_for_site(WORLD, "tavern_host", "tavern", "second-site-fruit",
                        "second-tavern-fruit", 1, 2, expected_revision=_rev(db))
    bought = market.buy_for_site(WORLD, "tavern_host", "tavern", "second-site-cheese",
                                 "second-tavern-cheese", 1, 3,
                                 expected_revision=_rev(db)).state
    assert bought.resources["tavern"]["coin_copper"] == 0
    assert bought.resources["tavern"]["fruit"] == bought.resources["tavern"]["cheese"] == 1
    assert bought.resources["huda"]["fruit"] == bought.resources["huda"]["cheese"] == 0
    assert bought.resources["huda"]["coin_copper"] == old.resources["huda"]["coin_copper"] + 5
    assert bought.resources["tavern_cook"]["coin_copper"] == 1
    assert bought.market_trades["second-site-cheese"]["business_keeper_id"] == "tavern_host"
    assert bought.market_trades["second-site-cheese"]["buyer_id"] == "tavern"

    NPCProductionService(db, clock).start(
        WORLD, "tavern_cook", "fruit-cheese-hot-plate",
        "second-real-hot-plate", expected_revision=_rev(db))
    clock.advance(WORLD, seconds=300, command_id="cook-second-300s",
                  expected_revision=_rev(db))
    cooked = db.load(WORLD)
    assert cooked.resources["tavern"]["food"] == 1
    assert cooked.production_jobs["second-real-hot-plate"]["status"] == "completed"
    assert cooked.resources["tavern"]["fruit"] == cooked.resources["tavern"]["cheese"] == 0

    market.post(WORLD, "tavern_host", "tavern",
                "tavern", "second-real-plate", "food", 1,
                "coin_copper", 6, expected_revision=_rev(db))
    # Huda's physical 2nd delivery was sold for 5c, so she really can buy
    # the second 6c plate. This is not an external subsidy.
    sold = market.buy(WORLD, "huda", "second-plate-sale",
                      "second-real-plate", 1, 6,
                      expected_revision=_rev(db)).state
    assert sold.resources["tavern"]["coin_copper"] == 6
    paid = db.append(WORLD, "second-signed-cook-wage", sold.revision, [
        DomainEvent("ProductionWagePaid", None, "second genuine completed plate",
                    sold.time, {"job_id": "second-real-hot-plate", "amount": 1}),
    ], production_authorized=True)
    assert paid.resources["tavern"]["coin_copper"] == 5
    assert paid.resources["tavern_cook"]["coin_copper"] == 2
    assert paid.resources["huda"]["coin_copper"] == 2
    assert paid.resources["huda"]["food"] == 1
    assert paid.resources["orchard"]["fruit_ready"] == paid.resources["dairy"]["milk"] == 0
    assert copper(paid) == 22
    assert db.verify(WORLD).to_dict() == paid.to_dict()
    return paid

def test_two_bounded_meals_second_financed_by_real_venue_receipts(village):
    db, clock, market = village
    start = _first_real_plate(db, clock, market)
    _second_authentic_goods(db, clock, market)
    done = _make_second_meal(db, clock, market)
    assert done.production_jobs["real-hot-plate"]["status"] == "completed"
    assert done.production_jobs["second-real-hot-plate"]["status"] == "completed"
    assert done.resources["tavern"]["coin_copper"] == 5
    assert done.market_trades["second-site-fruit"]["buyer_id"] == "tavern"
    assert done.market_trades["second-site-cheese"]["buyer_id"] == "tavern"
    assert done.resources["tavern_cook"]["coin_copper"] == 2
    assert copper(done) == copper(start)
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == done.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not db.db.execute("PRAGMA foreign_key_check").fetchall()

def test_site_funds_never_spend_without_seller_inventory_or_a_local_recipe(village):
    db, clock, market = village
    _first_real_plate(db, clock, market)
    # Site funds 5 but no second batch exists yet. Host cannot buy distant
    # goods or conjure a local listing.
    before = db.load(WORLD)
    with pytest.raises(InvalidEvent):
        market.buy_for_site(WORLD, "tavern_host", "tavern", "fake-out-of-town",
                            "second-cheese-quote", 1, 2,
                            expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()
    _second_authentic_goods(db, clock, market)
    start = db.load(WORLD)
    with pytest.raises(PermissionError):
        market.buy_for_site(WORLD, "tavern_cook", "tavern", "fake-chef",
                            "second-tavern-cheese", 1, 3,
                            expected_revision=_rev(db))
    with pytest.raises(PermissionError):
        market.buy_for_site(WORLD, "tavern_host", "dairy", "fake-remote-buyer",
                            "second-tavern-cheese", 1, 3,
                            expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == start.to_dict()
    market.post(WORLD, "huda", "huda", "tavern",
                "noninput-bread", "bread", 1, "coin_copper", 1,
                expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        market.buy_for_site(WORLD, "tavern_host", "tavern", "unrelated-food",
                            "noninput-bread", 1, 1,
                            expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
    _make_second_meal(db, clock, market)

def test_site_cannot_purchase_without_cash_even_with_true_local_seller(village):
    db, clock, market = village
    # The actual first production seller is on-site; tavern treasury is ZERO
    # until a real customer pays for cooked food.
    from test_play49_tavern_trade_provenance import source_goods, post_tavern
    source_goods(db, clock, market)
    walk(db, clock, "huda", "dairy-tavern", "huda-puts-real-fruit-on-sale", 60)
    post_tavern(db, market)
    before = db.load(WORLD)
    assert before.resources["tavern"]["coin_copper"] == 0
    assert before.resources["huda"]["fruit"] == 1
    with pytest.raises(InvalidEvent):
        market.buy_for_site(WORLD, "tavern_host", "tavern",
                            "no-minted-funding", "tavern-fruit-quote",
                            1, 2, expected_revision=_rev(db))
    assert db.verify(WORLD).to_dict() == before.to_dict()
