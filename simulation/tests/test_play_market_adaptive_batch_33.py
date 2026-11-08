"""PLAY-33: opt-in market behaviour emerges from finite local inventory and wallets.

These tests intentionally distinguish pure policy projections from real, durable
event-driven village trials. Projection fixtures never enter the canonical story.
"""
from __future__ import annotations

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine
from carlos_sim.domain import WorldState, apply_event
from carlos_sim.economic_autonomy import (
    TEST_FOOD_PRICE_COPPER,
    choose_local_food_offer,
    choose_local_food_purchase,
    choose_local_offer_retirement,
)
from carlos_sim.store import DuplicateCommand, SQLiteEventStore
from carlos_sim.time_engine import TimeEngine
from test_play_economic_autonomy_batch_24 import WORLD, seed, totals


def _seeded_state(tmp_path, *, copper=3, grain=0):
    with SQLiteEventStore(tmp_path / "policy.sqlite") as db:
        seed(db, copper=copper, grain=grain)
        return db.load(WORLD)


def _snapshot_with_stock(state, *, food=1, hunger=None, buyer_site=None):
    """Validated frozen experimental inputs; not a trusted stock-changing event."""
    raw = state.to_dict()
    raw["resources"]["square"]["food"] = food
    if hunger is not None:
        raw["npcs"]["adel"]["needs"]["hunger"] = hunger
    if buyer_site is not None:
        raw["entities"]["adel"]["location_id"] = buyer_site
    return WorldState.from_dict(raw)


def _offer(price, *, quantity=1):
    return {
        "seller_id": "salma", "stock_owner_id": "square", "site_id": "square",
        "resource": "food", "quantity": quantity, "remaining": quantity,
        "payment_resource": "coin_copper", "unit_price": price,
        "posted_at": 0, "status": "open", "closed_at": None,
    }


@pytest.mark.parametrize("stock,price", [(0, None), (1, 3), (2, 2), (3, 2), (4, 1), (20, 1)])
def test_keeper_prices_only_known_local_site_stock(tmp_path, stock, price):
    initial = _seeded_state(tmp_path)
    state = _snapshot_with_stock(initial, food=stock)
    old = state.to_dict()
    proposed = choose_local_food_offer(state, "salma", adaptive=True)
    assert (proposed.unit_price if proposed is not None else None) == price
    if proposed:
        assert proposed.quantity == stock
        assert proposed.reason.endswith("adaptive=True")
    legacy = choose_local_food_offer(state, "salma")
    assert (legacy is None) if stock == 0 else (legacy.unit_price == TEST_FOOD_PRICE_COPPER)
    assert state.to_dict() == old


def test_keeper_rejects_remote_inventory_and_non_stewards(tmp_path):
    state = _seeded_state(tmp_path)
    raw = state.to_dict()
    raw["resources"].setdefault("home", {})["food"] = 50
    state = WorldState.from_dict(raw)
    assert choose_local_food_offer(state, "salma", adaptive=True) is None
    assert choose_local_food_offer(state, "adel", adaptive=True) is None


@pytest.mark.parametrize("hunger,copper,expected_offer", [
    (75, 3, "z-cheap"), (85, 3, "z-cheap"),
    (75, 1, "z-cheap"), (85, 0, None),
])
def test_buyer_picks_cheapest_visible_affordable_quote(tmp_path, hunger, copper, expected_offer):
    original = _seeded_state(tmp_path, copper=copper)
    raw = _snapshot_with_stock(original, food=2, hunger=hunger).to_dict()
    raw["market_offers"] = {"a-expensive": _offer(3), "z-cheap": _offer(1)}
    state = WorldState.from_dict(raw)
    old = state.to_dict()
    result = choose_local_food_purchase(state, "adel", adaptive=True)
    assert (result.offer_id if result else None) == expected_offer
    if result:
        assert result.price == 1
        assert "own_copper=" in result.reason
    assert state.to_dict() == old


def test_hunger_willingness_does_not_allow_price_spikes_or_remote_quotes(tmp_path):
    original = _seeded_state(tmp_path, copper=4)
    state = _snapshot_with_stock(original, food=1, hunger=75)
    raw = state.to_dict()
    raw["market_offers"] = {"expensive": _offer(3)}
    state = WorldState.from_dict(raw)
    assert choose_local_food_purchase(state, "adel", adaptive=True) is None
    # Legacy policy remains unchanged and can buy the posted unit if funded.
    assert choose_local_food_purchase(state, "adel").price == 3
    raw = state.to_dict()
    raw["npcs"]["adel"]["needs"]["hunger"] = 85
    assert choose_local_food_purchase(WorldState.from_dict(raw), "adel", adaptive=True).price == 3
    raw["entities"]["adel"]["location_id"] = "home"
    assert choose_local_food_purchase(WorldState.from_dict(raw), "adel", adaptive=True) is None


def test_oversubscribed_quote_retired_only_by_real_on_site_seller(tmp_path):
    original = _seeded_state(tmp_path)
    raw = _snapshot_with_stock(original, food=1).to_dict()
    raw["market_offers"] = {"stale": _offer(2, quantity=2)}
    state = WorldState.from_dict(raw)
    retirement = choose_local_offer_retirement(state, "salma")
    assert retirement is not None and retirement.offer_id == "stale"
    before = state.resources["square"]["food"]
    event = DomainEvent("MarketOfferClosed", "salma", retirement.reason, state.time,
                        {"id": retirement.offer_id})
    with pytest.raises(ValueError):
        apply_event(state, event)
    closed = apply_event(state, event, market_authorized=True)
    assert closed.market_offers["stale"]["status"] == "closed"
    assert closed.resources["square"]["food"] == before
    assert closed.resources["square"]["coin_copper"] == 0
    assert choose_local_offer_retirement(closed, "salma") is None


def _play(path, *, grain=1, copper=3, competitor=False):
    with SQLiteEventStore(path) as db:
        seed(db, grain=grain, copper=copper, second_buyer=competitor)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(db, clock, economic_enabled=True,
                                       adaptive_market_enabled=True,
                                       consumption_enabled=True, survival_enabled=True)
            initial = db.load(WORLD)
            before = totals(initial)
            result = engine.advance(WORLD, seconds=90, command_id="adaptive-tick",
                                    expected_revision=initial.revision)
            final = result.state
            assert totals(final) == before
            assert db.verify(WORLD).to_dict() == final.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            with pytest.raises(DuplicateCommand):
                engine.advance(WORLD, seconds=90, command_id="adaptive-tick",
                               expected_revision=initial.revision)
            return final.to_dict(), before
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("grain,copper,trades,copper_to_market", [
    (1, 3, 1, 3), (1, 2, 0, 0), (0, 3, 0, 0)
])
def test_real_npc_market_is_material_backed_and_cannot_issue_credit(
        tmp_path, grain, copper, trades, copper_to_market):
    final, initial_totals = _play(tmp_path / "economy.sqlite", grain=grain, copper=copper)
    assert len(final["market_trades"]) == trades
    assert final["resources"]["square"]["coin_copper"] == copper_to_market
    assert initial_totals == (grain, copper)
    if grain:
        assert next(iter(final["market_offers"].values()))["unit_price"] == 3
    if trades:
        trade = next(iter(final["market_trades"].values()))
        assert trade["buyer_id"] == "adel"
        assert trade["total_paid"] == 3
        assert len(final["consumptions"]) == 1


def test_one_loaf_cannot_be_sold_twice_under_competing_wallets(tmp_path):
    state, start = _play(tmp_path / "compete.sqlite", competitor=True)
    assert start == (1, 5)
    assert len(state["market_trades"]) == 1
    assert state["resources"]["square"]["coin_copper"] == 3
    assert state["resources"]["amir"]["coin_copper"] == 2


def test_multiple_separate_worlds_are_deterministic_and_reopen_cleanly(tmp_path):
    a, _ = _play(tmp_path / "a.sqlite")
    b, _ = _play(tmp_path / "b.sqlite")
    assert a == b
    with SQLiteEventStore(tmp_path / "a.sqlite") as db:
        assert db.verify(WORLD).to_dict() == a


@pytest.mark.parametrize("value", [None, 1, 0, "true", [], {}])
def test_adaptive_policy_flag_is_strict_and_requires_economic_mode(tmp_path, value):
    state = _seeded_state(tmp_path)
    with pytest.raises(ValueError, match="adaptive"):
        choose_local_food_offer(state, "salma", adaptive=value)
    with pytest.raises(ValueError, match="adaptive"):
        choose_local_food_purchase(state, "adel", adaptive=value)
    with SQLiteEventStore(tmp_path / "options.sqlite") as db:
        clock = TimeEngine(db)
        with pytest.raises(ValueError, match="adaptive_market_enabled"):
            LivingWorldEngine(db, clock, economic_enabled=True,
                              adaptive_market_enabled=value)
        with pytest.raises(ValueError, match="adaptive_market_enabled"):
            LivingWorldEngine(db, clock, adaptive_market_enabled=True)
