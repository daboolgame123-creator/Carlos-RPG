"""PLAY49-I: autonomously committed *venue* purchases of actual local inputs.

The driver prepares real PLAY49-G source goods and road shipments; the merchant
decides purchases without direct market.buy_for_site instructions. This does
NOT claim autonomous harvesting, transport, cooking, sales or 96/168h survival.
"""
from __future__ import annotations

import pytest

from carlos_sim import (
    LivingWorldEngine, NPCMarketService, NPCMovementService,
    SQLiteEventStore, TimeEngine,
)
from test_market_02c import _rev
from test_play49_fruit_stall_contract import WORLD, copper
from test_play49_site_funded_procurement import (
    _setup, _first_real_plate, _second_authentic_goods,
)
from carlos_sim.site_market_autonomy import choose_local_site_input_purchase


@pytest.fixture
def ready(tmp_path):
    with SQLiteEventStore(tmp_path / "play49i-venue.sqlite") as db:
        _setup(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            market = NPCMarketService(db, clock)
            _first_real_plate(db, clock, market)
            yield db, clock, market
        finally:
            clock.close_session(WORLD)


def _economy(db, clock, *, enabled):
    return LivingWorldEngine(
        db, clock, economic_enabled=True,
        agriculture_enabled=True, economy_only_enabled=True,
        site_procurement_enabled=enabled,
    )


def test_site_keeper_autonomously_buys_complete_real_batch_with_site_money(ready):
    db, clock, market = ready
    # No fictitious advance stocking or remote knowledge.
    first = db.load(WORLD)
    assert first.resources["tavern"]["coin_copper"] == 5
    assert choose_local_site_input_purchase(first, "tavern") is None
    _second_authentic_goods(db, clock, market)
    before = db.load(WORLD)
    assert before.resources["tavern"]["coin_copper"] == 5
    assert before.resources["huda"]["fruit"] == before.resources["huda"]["cheese"] == 1
    choice = choose_local_site_input_purchase(before, "tavern")
    assert choice is not None
    assert choice.keeper_id == "tavern_host"
    assert choice.site_id == "tavern"
    assert choice.offer_id in ("second-tavern-fruit", "second-tavern-cheese")
    economy = _economy(db, clock, enabled=True)
    a = economy.advance(WORLD, seconds=1, command_id="i-auto-buy-tick1",
                        expected_revision=_rev(db))
    after_one = db.load(WORLD)
    assert len(a.economic_trades) >= 1
    one = [t for t in after_one.market_trades.values()
           if t.get("business_keeper_id") == "tavern_host"]
    assert len(one) == 1
    assert one[0]["buyer_id"] == "tavern"
    assert copper(after_one) == copper(before) == 22

    economy.advance(WORLD, seconds=1, command_id="i-auto-buy-tick2",
                    expected_revision=_rev(db))
    bought = db.load(WORLD)
    receipts = [t for t in bought.market_trades.values()
                if t.get("business_keeper_id") == "tavern_host"]
    assert len(receipts) == 2
    assert {t["resource"] for t in receipts} == {"fruit", "cheese"}
    assert bought.resources["tavern"]["coin_copper"] == 0
    assert bought.resources["tavern"]["fruit"] == bought.resources["tavern"]["cheese"] == 1
    assert bought.resources["huda"]["fruit"] == bought.resources["huda"]["cheese"] == 0
    assert bought.resources["huda"]["coin_copper"] == before.resources["huda"]["coin_copper"] + 5
    assert bought.resources["tavern_cook"]["coin_copper"] == 1
    assert copper(bought) == 22
    assert choose_local_site_input_purchase(bought, "tavern") is None
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == bought.to_dict()
    assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_default_off_still_does_not_buy_prepared_venue_goods(ready):
    db, clock, market = ready
    _second_authentic_goods(db, clock, market)
    before = db.load(WORLD)
    _economy(db, clock, enabled=False).advance(
        WORLD, seconds=1, command_id="i-no-optin",
        expected_revision=_rev(db))
    later = db.load(WORLD)
    assert later.resources["tavern"]["coin_copper"] == 5
    assert later.resources["tavern"]["fruit"] == 0
    assert later.resources["tavern"]["cheese"] == 0
    assert all("business_keeper_id" not in t for t in later.market_trades.values())
    assert copper(later) == copper(before)


def test_missing_one_ingredient_offer_prevents_partial_venue_purchase(ready):
    db, clock, market = ready
    _second_authentic_goods(db, clock, market)
    market.close(WORLD, "huda", "second-tavern-cheese",
                 expected_revision=_rev(db))
    before = db.load(WORLD)
    assert choose_local_site_input_purchase(before, "tavern") is None
    _economy(db, clock, enabled=True).advance(
        WORLD, seconds=1, command_id="i-no-half-recipe",
        expected_revision=_rev(db))
    after = db.load(WORLD)
    assert after.resources["tavern"]["coin_copper"] == 5
    assert after.resources["tavern"]["fruit"] == after.resources["tavern"]["cheese"] == 0
    assert all("business_keeper_id" not in t for t in after.market_trades.values())
    assert copper(after) == copper(before)


def test_keeper_in_transit_cannot_buy_at_absent_venue(ready):
    db, clock, market = ready
    _second_authentic_goods(db, clock, market)
    # The actual tavern's registered keeper departs on a real road.
    NPCMovementService(db, clock).start(
        WORLD, "tavern_host", "dairy-tavern",
        "i-host-left-tavern", expected_revision=_rev(db))
    moving = db.load(WORLD)
    assert choose_local_site_input_purchase(moving, "tavern") is None
    _economy(db, clock, enabled=True).advance(
        WORLD, seconds=1, command_id="i-no-remote-keeper",
        expected_revision=_rev(db))
    after = db.load(WORLD)
    assert all("business_keeper_id" not in t for t in after.market_trades.values())
    assert after.resources["tavern"]["coin_copper"] == 5


def test_opt_in_requires_actual_economic_simulation(ready):
    db, clock, _ = ready
    with pytest.raises(ValueError):
        LivingWorldEngine(db, clock, site_procurement_enabled=True)
