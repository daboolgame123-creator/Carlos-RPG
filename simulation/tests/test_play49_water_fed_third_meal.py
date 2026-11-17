"""PLAY49-H: a third real plate from explicitly seeded/watered regrowth.

Isolated commanded feasibility, NOT autonomous repeatability or a limitless farm.
No new reducer, world version, synthetic runtime resource or PLAY48 modification.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, NPCMarketService, NPCMovementService, NPCProductionService,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import InvalidEvent
from test_market_02c import ev, _rev
from test_play49_fruit_stall_contract import WORLD, copper
from test_play49_tavern_trade_provenance import walk
from test_play49_site_funded_procurement import (
    _setup, _first_real_plate, _second_authentic_goods, _make_second_meal,
)


def add_finite_renewal_contract(db):
    """Only at time zero: one planted fruit crop and one fed/watered cow cycle."""
    old = db.load(WORLD)
    events = []
    for owner, key, amount in (
        ("orchard", "seed", 1), ("orchard", "crop_seeded", 0),
        ("orchard", "crop_ready", 0), ("orchard", "water", 1),
        ("orchard", "hoe", 1),
        ("dairy", "feed", 1), ("dairy", "water", 1),
        ("dairy", "cow", 1),
    ):
        events.append(ev("ResourceChanged", {
            "owner_id": owner, "resource": key,
            "previous": None, "current": amount, "source": "initialization",
        }))
    events.extend([
        ev("ProductionRecipeConfigured", {
            "id": "orchard-seed-plant", "site_id": "orchard", "role": "farmer",
            "input_resource": "seed", "input_amount": 1,
            "output_resource": "crop_seeded", "output_amount": 1,
            "tool_resource": "hoe", "duration_seconds": 60,
        }),
        ev("ProductionRecipeConfigured", {
            "id": "orchard-ripe-picking", "site_id": "orchard",
            "role": "farmer", "input_resource": "crop_ready",
            "input_amount": 1, "output_resource": "fruit",
            "output_amount": 1, "tool_resource": "fruit_basket",
            "duration_seconds": 120, "wage_coin": 1,
        }),
        ev("ProductionRecipeConfigured", {
            "id": "cow-feed-and-milk", "site_id": "dairy",
            "role": "cheesemaker",
            "inputs": [
                {"resource": "feed", "amount": 1},
                {"resource": "water", "amount": 1},
            ],
            "output_resource": "milk", "output_amount": 2,
            "tool_resource": "cow", "duration_seconds": 7200,
            "wage_coin": 1,
        }),
        ev("FarmPlotConfigured", {
            "site_id": "orchard", "growth_seconds": 86400, "capacity": 1,
        }),
    ])
    state = db.append(WORLD, "play49h:physical-genesis", old.revision, events,
                      bootstrap=True)
    assert state.time == 0
    assert copper(state) == copper(old) == 22
    assert state.resources["orchard"]["seed"] == 1
    assert state.resources["dairy"]["feed"] == 1
    assert db.verify(WORLD).to_dict() == state.to_dict()


def regenerate_one_real_batch(db, clock):
    start = db.load(WORLD)
    assert start.resources["orchard"]["fruit_ready"] == 0
    assert start.resources["dairy"]["milk"] == 0
    assert start.resources["orchard"]["crop_ready"] == 0
    prod = NPCProductionService(db, clock)
    # Neither empty land nor an unfed cow may magically replenish the market.
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "play49h:unplanted-growth", _rev(db), [
            DomainEvent("CropGrowthStarted", None, "unplanted", start.time,
                        {"site_id": "orchard"})
        ], agriculture_authorized=True)
    assert db.verify(WORLD).to_dict() == start.to_dict()

    prod.start(WORLD, "fruit_farmer", "orchard-seed-plant", "h-seed",
               expected_revision=_rev(db))
    prod.start(WORLD, "cheese_maker", "cow-feed-and-milk", "h-milking",
               expected_revision=_rev(db))
    clock.advance(WORLD, seconds=60, command_id="h-plant-done",
                  expected_revision=_rev(db))
    planted = db.load(WORLD)
    assert planted.resources["orchard"]["seed"] == 0
    assert planted.resources["orchard"]["crop_seeded"] == 1
    db.append(WORLD, "h-watered-growth", _rev(db), [
        DomainEvent("CropGrowthStarted", None, "watered growing plant",
                    planted.time, {"site_id": "orchard"})
    ], agriculture_authorized=True)
    growing = db.load(WORLD)
    assert growing.resources["orchard"]["water"] == 0
    assert growing.resources["orchard"]["crop_ready"] == 0
    with pytest.raises(InvalidEvent):
        db.append(WORLD, "h-double-growth", _rev(db), [
            DomainEvent("CropGrowthStarted", None, "forged repeat",
                        growing.time, {"site_id": "orchard"})
        ], agriculture_authorized=True)

    # Exactly one day of logical growth: no manual inventory top-ups.
    clock.advance(WORLD, seconds=86400, command_id="h-one-natural-day",
                  expected_revision=_rev(db))
    mature = db.load(WORLD)
    assert mature.time == planted.time + 86400
    assert mature.farm_plots["orchard"]["matured"] == 1
    assert mature.resources["orchard"]["crop_ready"] == 1
    assert mature.resources["orchard"]["seed"] == 1  # biological seed return
    assert mature.resources["dairy"]["milk"] == 2
    assert mature.resources["dairy"]["feed"] == mature.resources["dairy"]["water"] == 0
    assert mature.production_jobs["h-milking"]["status"] == "completed"

    prod.start(WORLD, "fruit_farmer", "orchard-ripe-picking", "h-fruit",
               expected_revision=_rev(db))
    prod.start(WORLD, "cheese_maker", "milk-to-cheese", "h-cheese",
               expected_revision=_rev(db))
    clock.advance(WORLD, seconds=180, command_id="h-harvest-and-cheese",
                  expected_revision=_rev(db))
    produced = db.load(WORLD)
    assert produced.resources["orchard"]["fruit"] == 1
    assert produced.resources["dairy"]["cheese"] == 1
    assert produced.resources["orchard"]["crop_ready"] == 0
    assert produced.resources["dairy"]["milk"] == 0
    assert copper(produced) == copper(start)

    # Without another known unit of feed/water, even a real cow cannot
    # create an extra milking batch. Nor can an unwatered field start growth.
    with pytest.raises(InvalidEvent):
        prod.start(WORLD, "cheese_maker", "cow-feed-and-milk", "h-free-milk",
                   expected_revision=_rev(db))
    before = db.load(WORLD)
    assert db.verify(WORLD).to_dict() == before.to_dict()


def buy_cook_and_pay_third_plate(db, clock, market):
    # Huda is in tavern with two genuinely owned coins from PLAY49-G.
    s = db.load(WORLD)
    assert s.resources["huda"]["coin_copper"] == 2
    assert s.resources["tavern"]["coin_copper"] == 5
    market.post(WORLD, "fruit_seller", "orchard", "orchard", "h-fruit-offer",
                "fruit", 1, "coin_copper", 1, expected_revision=_rev(db))
    market.post(WORLD, "cheese_seller", "dairy", "dairy", "h-cheese-offer",
                "cheese", 1, "coin_copper", 1, expected_revision=_rev(db))
    with pytest.raises(InvalidEvent):
        market.buy(WORLD, "huda", "h-distant-cheese",
                   "h-cheese-offer", 1, 1, expected_revision=_rev(db))

    walk(db, clock, "huda", "dairy-tavern", "h-to-dairy", 60)
    market.buy(WORLD, "huda", "h-buy-cheese", "h-cheese-offer", 1, 1,
               expected_revision=_rev(db))
    walk(db, clock, "huda", "orchard-dairy", "h-to-orchard", 70)
    market.buy(WORLD, "huda", "h-buy-fruit", "h-fruit-offer", 1, 1,
               expected_revision=_rev(db))
    walk(db, clock, "huda", "orchard-dairy", "h-return-dairy", 70)
    walk(db, clock, "huda", "dairy-tavern", "h-return-tavern", 60)
    assert db.load(WORLD).resources["huda"]["coin_copper"] == 0
    market.post(WORLD, "huda", "huda", "tavern", "h-delivered-fruit",
                "fruit", 1, "coin_copper", 2, expected_revision=_rev(db))
    market.post(WORLD, "huda", "huda", "tavern", "h-delivered-cheese",
                "cheese", 1, "coin_copper", 3, expected_revision=_rev(db))
    market.buy_for_site(WORLD, "tavern_host", "tavern", "h-site-fruit",
                        "h-delivered-fruit", 1, 2, expected_revision=_rev(db))
    market.buy_for_site(WORLD, "tavern_host", "tavern", "h-site-cheese",
                        "h-delivered-cheese", 1, 3, expected_revision=_rev(db))
    purchased = db.load(WORLD)
    assert purchased.resources["tavern"]["coin_copper"] == 0
    assert purchased.resources["huda"]["coin_copper"] == 5
    assert purchased.resources["tavern"]["fruit"] == 1
    assert purchased.resources["tavern"]["cheese"] == 1

    NPCProductionService(db, clock).start(
        WORLD, "tavern_cook", "fruit-cheese-hot-plate", "h-hot-plate",
        expected_revision=_rev(db))
    clock.advance(WORLD, seconds=300, command_id="h-third-plate-cooked",
                  expected_revision=_rev(db))
    market.post(WORLD, "tavern_host", "tavern", "tavern", "h-plate-offer",
                "food", 1, "coin_copper", 5, expected_revision=_rev(db))
    market.buy(WORLD, "huda", "h-third-plate-purchased", "h-plate-offer",
               1, 5, expected_revision=_rev(db))
    sold = db.load(WORLD)
    assert sold.resources["huda"]["coin_copper"] == 0
    assert sold.resources["huda"]["food"] == 2
    assert sold.resources["tavern"]["coin_copper"] == 5
    assert sold.resources["tavern"]["food"] == 0

    # Settlement includes already signed real jobs from the two earlier
    # plates. Only completed unpaid jobs, never fictitious salaries.
    due = []
    for ident, job in sold.production_jobs.items():
        recipe = sold.production_recipes[job["recipe_id"]]
        if (job["status"] == "completed" and "work_wage" not in job
                and "wage_coin" in recipe):
            due.append((ident, recipe["wage_coin"]))
    assert len(due) >= 8  # farm, dairy and the third cooked meal
    events = [
        DomainEvent("ProductionWagePaid", None, "signed completed real job",
                    sold.time, {"job_id": ident, "amount": amount})
        for ident, amount in due
    ]
    paid = db.append(WORLD, "h-settle-all-earned-wages", sold.revision,
                     events, production_authorized=True)
    assert copper(paid) == 22
    assert all("work_wage" in paid.production_jobs[ident] for ident, _ in due)
    assert paid.resources["tavern"]["coin_copper"] == 4
    assert paid.resources["orchard"]["water"] == 0
    assert paid.resources["dairy"]["feed"] == 0
    assert paid.resources["dairy"]["water"] == 0
    assert paid.farm_plots["orchard"]["matured"] == 1
    assert db.verify(WORLD).to_dict() == paid.to_dict()
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == paid.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_third_plate_requires_water_seed_feed_labor_travel_real_cash_and_time(tmp_path):
    with SQLiteEventStore(tmp_path / "play49h-real-third-plate.sqlite") as db:
        _setup(db)
        add_finite_renewal_contract(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            market = NPCMarketService(db, clock)
            _first_real_plate(db, clock, market)
            _second_authentic_goods(db, clock, market)
            _make_second_meal(db, clock, market)
            regenerate_one_real_batch(db, clock)
            buy_cook_and_pay_third_plate(db, clock, market)
        finally:
            clock.close_session(WORLD)
        last = db.verify(WORLD)
        assert copper(last) == 22
        assert last.resources["orchard"]["fruit"] == 0
        assert last.resources["dairy"]["cheese"] == 0
        assert last.resources["tavern"]["food"] == 0
        assert last.farm_plots["orchard"]["matured"] == 1
