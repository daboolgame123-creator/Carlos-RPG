"""PLAY-42: physical NPC market journeys and strictly funded purchases.

The farmer must work for REAL site money, explore ONLY surveyed local roads,
arrive at the staffed market and then either buy at the actual posted price or
fail. No global stock oracle, teleport, free food or coin minting.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.market_navigation import choose_known_market_walk, wants_local_market
from test_play38_multi_farm_couriers import (
    WORLD, EAST, COURIER, FARMER, seed_two_field_world,
)


def _engine(db, clock, *, enable=True):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=5000,
        decision_cooldown=3600, navigation_enabled=True,
        routines_enabled=True, survival_enabled=True,
        consumption_enabled=True, supply_enabled=True,
        economic_enabled=True, adaptive_market_enabled=True,
        agriculture_enabled=True, economy_only_enabled=True,
        shopping_routes_enabled=enable,
    )


def _advance(db, engine, target):
    before = db.load(WORLD)
    result = engine.advance(
        WORLD, seconds=target - before.time,
        command_id=f"play42:advance:{target}",
        expected_revision=before.revision,
    )
    state = result.state
    assert state.time == target
    assert db.verify(WORLD).to_dict() == state.to_dict()
    db.snapshot(WORLD)
    assert db.verify(WORLD).to_dict() == state.to_dict()
    assert sum(v.get("coin_copper", 0) for v in state.resources.values()) == 12
    assert all(n >= 0 for b in state.resources.values() for n in b.values()
               if type(n) is int)
    for t in state.travels.values():
        assert t["due"] - t["start"] == state.routes[t["route_id"]]["seconds"]
        assert {t["origin"], t["destination"]} == {
            state.routes[t["route_id"]]["a"],
            state.routes[t["route_id"]]["b"],
        }
        if t["status"] == "arrived":
            assert t["arrived_at"] == t["due"]
    return state


@pytest.mark.parametrize("wage,expected_purchase", [
    (1, False), (2, True),
])
def test_farmer_earns_walks_known_roads_then_fails_or_buys_and_eats(
        tmp_path, wage, expected_purchase):
    with SQLiteEventStore(tmp_path / f"shopper-{wage}.sqlite") as db:
        seed_two_field_world(
            db, cash_return=True, waged_harvest=True,
            hungry_waged_farmer=True, harvest_wage_copper=wage,
            market_wallets=True, hungry_market_buyers=False,
            initial_market_food=3,
        )
        before = db.verify(WORLD)
        assert before.resources[FARMER]["coin_copper"] == 0
        assert before.resources[FARMER]["food"] == 0
        assert before.npcs[FARMER]["needs"]["hunger"] == 80
        assert not wants_local_market(before, FARMER)
        assert choose_known_market_walk(before, FARMER) is None
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            rows = []
            state = before
            for target in (300, 1200, 3600, 3900, 4800, 7200, 8400, 12000):
                state = _advance(db, engine, target)
                sales = [t for t in state.market_trades.values()
                         if t["buyer_id"] == FARMER]
                meals = [m for m in state.consumptions.values()
                         if m["npc_id"] == FARMER]
                wage_receipts = [j["work_wage"] for j in state.production_jobs.values()
                                 if "work_wage" in j
                                 and j["npc_id"] == FARMER]
                rows.append({
                    "time": target,
                    "farmer_place": state.entities[FARMER]["location_id"],
                    "copper": state.resources[FARMER]["coin_copper"],
                    "paid_jobs": len(wage_receipts),
                    "shops": len(sales), "meals": len(meals),
                    "market_bread": state.resources["market"]["food"],
                })
            receipts = [j["work_wage"] for j in state.production_jobs.values()
                        if "work_wage" in j and j["npc_id"] == FARMER]
            assert receipts, "farmer never earned an actual wage"
            assert all(r["amount"] == wage for r in receipts)
            farmer_legs = [t for t in state.travels.values()
                           if t["npc_id"] == FARMER]
            assert farmer_legs, "worker never traversed any road"
            assert any(t["destination"] == "market" and t["status"] == "arrived"
                       for t in farmer_legs), "worker never physically arrived at market"
            assert all(t["start"] >= receipts[0]["paid_at"]
                       for t in farmer_legs), "journey started before funded pay"
            assert len({(t["start"], t["route_id"]) for t in farmer_legs}) == len(farmer_legs)
            assert state.entities[FARMER]["location_id"] == "market"
            sales = [t for t in state.market_trades.values()
                     if t["buyer_id"] == FARMER]
            meals = [m for m in state.consumptions.values()
                     if m["npc_id"] == FARMER]
            if expected_purchase:
                assert len(sales) == 1
                assert sales[0]["total_paid"] == wage == 2
                assert sales[0]["site_id"] == "market"
                assert len(meals) == 1
                assert meals[0]["consumed_at"] >= sales[0]["executed_at"]
                assert meals[0]["hunger_after"] < meals[0]["hunger_before"]
                assert state.resources[FARMER]["coin_copper"] == 0
                assert state.resources[FARMER]["food"] == 0
            else:
                assert not sales, "one copper must not buy a two-copper loaf"
                assert not meals, "unaffordable food must not be eaten"
                assert state.resources[FARMER]["coin_copper"] == 1
            print("PLAY42_REAL_SHOPPER", wage,
                  json.dumps(rows, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_unpaid_hungry_farmer_does_not_move_without_money(tmp_path):
    with SQLiteEventStore(tmp_path / "zero-copper.sqlite") as db:
        seed_two_field_world(
            db, cash_return=True, waged_harvest=True,
            hungry_waged_farmer=True, market_wallets=True,
            initial_market_food=0,
        )
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = _advance(db, _engine(db, clock), 5000)
            assert state.resources[FARMER]["coin_copper"] == 0
            assert not [t for t in state.travels.values()
                        if t["npc_id"] == FARMER]
            assert state.entities[FARMER]["location_id"] == EAST
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("bad", [None, 0, 1, "true", []])
def test_market_journey_is_strictly_opt_in(tmp_path, bad):
    with SQLiteEventStore(tmp_path / "invalid-flags.sqlite") as db:
        clock = TimeEngine(db)
        with pytest.raises(ValueError, match="shopping_routes_enabled"):
            LivingWorldEngine(db, clock, shopping_routes_enabled=bad)


def test_market_journey_requires_navigation_and_real_needs(tmp_path):
    with SQLiteEventStore(tmp_path / "missing-deps.sqlite") as db:
        clock = TimeEngine(db)
        with pytest.raises(ValueError, match="shopping_routes_enabled"):
            LivingWorldEngine(
                db, clock, economic_enabled=True, agriculture_enabled=True,
                economy_only_enabled=True, shopping_routes_enabled=True,
            )


def test_disabled_market_journey_preserves_exact_legacy_event_replay(tmp_path):
    states = []
    for explicit in (False, True):
        with SQLiteEventStore(tmp_path / f"legacy-{explicit}.sqlite") as db:
            seed_two_field_world(
                db, cash_return=True, waged_harvest=True,
                hungry_waged_farmer=True, market_wallets=True,
                hungry_market_buyers=False, initial_market_food=3,
            )
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                # The explicit-False setting must be indistinguishable from
                # historical default-OFF behavior at the event/replay level.
                if explicit:
                    engine = _engine(db, clock, enable=False)
                else:
                    engine = LivingWorldEngine(
                        db, clock, max_events_per_advance=5000,
                        decision_cooldown=3600, navigation_enabled=True,
                        routines_enabled=True, survival_enabled=True,
                        consumption_enabled=True, supply_enabled=True,
                        economic_enabled=True, adaptive_market_enabled=True,
                        agriculture_enabled=True, economy_only_enabled=True,
                    )
                state = _advance(db, engine, 4800)
                assert not [t for t in state.travels.values()
                            if t["npc_id"] == FARMER]
                states.append(state.to_dict())
            finally:
                clock.close_session(WORLD)
    assert states[0] == states[1]
