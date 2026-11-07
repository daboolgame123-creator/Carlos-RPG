"""PLAY-24: actual NPC decisions, material-backed jobs and local market trades."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine
from carlos_sim.store import (DuplicateCommand, InvalidEvent, RevisionConflict,
                              SQLiteEventStore)
from carlos_sim.time_engine import AdvanceLimitExceeded, TimeEngine
from carlos_sim.economic_autonomy import (
    choose_local_production, choose_local_food_offer, choose_local_food_purchase,
)

WORLD = "play24-physical-village"


def seed(store, *, grain=1, copper=2, seller=True, second_buyer=False,
         worker_shift=(0, 600), seller_fatigue=10, worker_fatigue=10,
         buyer_site="square"):
    """Only time-zero material and bank balances; no runtime resource subsidy."""
    store.create_world(WORLD)
    people = [
        ("basim", "square", "baker", 20, worker_fatigue, 0),
        ("salma", "square", "merchant", 20, seller_fatigue, 100),
        ("adel", buyer_site, "guard", 80, 10, 100),
    ]
    if second_buyer:
        people.append(("amir", "square", "guard", 80, 10, 100))
    def e(kind, payload):
        return DomainEvent(kind, None, "PLAY-24 disposable setup", 0, payload)
    events = [
        e("LocationCreated", {"id": "square", "name": "Village Square"}),
        e("LocationCreated", {"id": "home", "name": "Baker Home"}),
        e("EntityCreated", {"id": "carlos", "name": "Carlos",
                            "controller": "player", "location_id": "home"}),
    ]
    for who, site, role, hunger, fatigue, explore in people:
        events.extend([
            e("EntityCreated", {"id": who, "name": who,
                                "controller": "npc", "location_id": site}),
            e("NPCConfigured", {"npc_id": who, "role": role,
                                "needs": {"hunger": hunger, "fatigue": fatigue, "safety": 0},
                                "goals": {"earn": 0, "explore": explore, "survive": 30}}),
            *[e("ResourceChanged", {
                "owner_id": who, "resource": resource, "previous": None,
                "current": 0, "source": "initialization",
            }) for resource in ("labor_units", "investigation_attempts", "food")],
        ])
    for who, item, amount in (
        ("square", "grain", grain),
        ("square", "oven", 1),
        ("square", "food", 0),
        ("square", "coin_copper", 0),
        ("adel", "coin_copper", copper),
        *((("amir", "coin_copper", 2),) if second_buyer else ()),
    ):
        events.append(e("ResourceChanged", {
            "owner_id": who, "resource": item, "previous": None,
            "current": amount, "source": "initialization",
        }))
    events.extend([
        e("NPCRoutineConfigured", {
            "npc_id": "basim", "home_id": "home", "workplace_id": "square",
            "work_start": worker_shift[0], "work_end": worker_shift[1],
        }),
        e("ProductionRecipeConfigured", {
            "id": "one-grain-meal", "site_id": "square", "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 1,
            "tool_resource": "oven", "duration_seconds": 90,
        }),
    ])
    if seller:
        events.append(e("MarketStallConfigured", {
            "site_id": "square", "keeper_id": "salma",
        }))
    store.append(WORLD, "seed-play24", 0, events, bootstrap=True)


def begin(path, **kwargs):
    store = SQLiteEventStore(path)
    try:
        seed(store, **kwargs)
        clock = TimeEngine(store)
        clock.open_session(WORLD)
        engine = LivingWorldEngine(
            store, clock, economic_enabled=True,
            consumption_enabled=True, survival_enabled=True)
        return store, clock, engine
    except BaseException:
        store.close()
        raise


def advance(store, engine, seconds=90, ident="wait"):
    return engine.advance(WORLD, seconds=seconds, command_id=ident,
                          expected_revision=store.load(WORLD).revision)


def totals(state):
    stock = state.resources
    meals = sum(m["quantity"] for m in state.consumptions.values())
    people = ("adel", "amir", "basim", "salma")
    food = (stock["square"]["food"] + stock["square"]["grain"] +
            sum(stock[x].get("food", 0) for x in people if x in stock) + meals)
    copper = (stock["square"]["coin_copper"] +
              sum(stock[x].get("coin_copper", 0) for x in people if x in stock))
    return food, copper


def test_entire_chain_is_npc_autonomous_during_same_living_world_wait(tmp_path):
    db, clock, engine = begin(tmp_path / "chain.sqlite")
    try:
        initial = db.load(WORLD)
        assert totals(initial) == (1, 2)
        result = advance(db, engine)
        final = result.state
        assert final.time == 90
        assert len(final.production_jobs) == 1
        assert len(final.market_offers) == 1
        assert len(final.market_trades) == 1
        assert len(final.consumptions) == 1
        assert result.economic_jobs and result.economic_offers and result.economic_trades
        assert final.production_jobs[result.economic_jobs[0]]["status"] == "completed"
        assert final.market_trades[result.economic_trades[0]]["buyer_id"] == "adel"
        assert final.market_trades[result.economic_trades[0]]["total_paid"] == 2
        assert final.npcs["adel"]["needs"]["hunger"] == 60  # 80 + 5 time hunger - 25 meal
        assert final.resources["adel"]["coin_copper"] == 0
        assert final.resources["square"]["coin_copper"] == 2
        assert totals(final) == (1, 2)
        meal = next(iter(final.consumptions.values()))
        assert (meal["hunger_before"], meal["hunger_after"]) == (85, 60)
        assert db.verify(WORLD).to_dict() == final.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("opts,jobs,offers,trades", [
    ({"grain": 0}, 0, 0, 0),
    ({"copper": 1}, 1, 1, 0),
    ({"seller": False}, 1, 0, 0),
    ({"worker_shift": (200, 600)}, 0, 0, 0),
    ({"worker_fatigue": 70}, 0, 0, 0),
    ({"seller_fatigue": 80}, 1, 0, 0),
    ({"buyer_site": "home"}, 1, 1, 0),
])
def test_no_miracle_outcomes_when_constraints_fail(tmp_path, opts, jobs, offers, trades):
    db, clock, engine = begin(tmp_path / "counterfactual.sqlite", **opts)
    try:
        before = db.load(WORLD)
        after = advance(db, engine).state
        assert len(after.production_jobs) == jobs
        assert len(after.market_offers) == offers
        assert len(after.market_trades) == trades
        assert totals(after) == totals(before)
        assert db.verify(WORLD).to_dict() == after.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_two_hungry_buyers_compete_for_one_physical_loaf(tmp_path):
    db, clock, engine = begin(tmp_path / "competition.sqlite", second_buyer=True)
    try:
        result = advance(db, engine)
        final = result.state
        assert len(final.production_jobs) == 1
        assert len(final.market_trades) == 1
        assert len(final.consumptions) == 1
        # Sorted, stable local competition chooses the first actually eligible NPC.
        assert next(iter(final.market_trades.values()))["buyer_id"] == "adel"
        assert final.resources["amir"]["coin_copper"] == 2
        assert final.resources["adel"]["coin_copper"] == 0
        assert totals(final) == (1, 4)
        assert db.verify(WORLD).to_dict() == final.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_opt_in_default_off_keeps_old_world_without_economic_events(tmp_path):
    db, clock, _engine = begin(tmp_path / "legacy.sqlite")
    try:
        old = LivingWorldEngine(db, clock, consumption_enabled=True,
                                survival_enabled=True)
        result = advance(db, old)
        assert not result.economic_jobs and not result.economic_offers
        assert not result.economic_trades
        assert result.state.production_jobs == {}
        assert result.state.market_trades == {}
        assert totals(result.state) == (1, 2)
    finally:
        clock.close_session(WORLD)
        db.close()


def test_budget_exhaustion_commits_nothing(tmp_path):
    db, clock, _engine = begin(tmp_path / "budget.sqlite")
    try:
        tiny = LivingWorldEngine(db, clock, economic_enabled=True,
                                 consumption_enabled=True, survival_enabled=True,
                                 max_events_per_advance=1)
        before = db.load(WORLD).to_dict()
        count = db.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
        with pytest.raises(AdvanceLimitExceeded):
            advance(db, tiny)
        assert db.load(WORLD).to_dict() == before
        assert db.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0] == count
    finally:
        clock.close_session(WORLD)
        db.close()


def test_determinism_and_replay_across_independent_databases(tmp_path):
    results = []
    for label in ("a", "b"):
        db, clock, engine = begin(tmp_path / (label + ".sqlite"))
        try:
            first = advance(db, engine)
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == first.state.to_dict()
            results.append(db.load(WORLD).to_dict())
        finally:
            clock.close_session(WORLD)
            db.close()
    assert results[0] == results[1]


def test_reopen_stale_duplicate_and_explicit_resumed_clock(tmp_path):
    path = tmp_path / "resume.sqlite"
    db, clock, engine = begin(path)
    try:
        advance(db, engine)
        saved = db.verify(WORLD).to_dict()
        db.snapshot(WORLD)
    finally:
        clock.close_session(WORLD)
        db.close()
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == saved
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(db, clock, economic_enabled=True,
                                       consumption_enabled=True, survival_enabled=True)
            with pytest.raises(DuplicateCommand):
                engine.advance(WORLD, seconds=1, command_id="wait",
                               expected_revision=db.load(WORLD).revision)
            with pytest.raises(RevisionConflict):
                engine.advance(WORLD, seconds=1, command_id="stale",
                               expected_revision=saved["revision"] - 1)
            assert db.load(WORLD).to_dict() == saved
            assert advance(db, engine, 10, "resume").state.time == 100
            assert db.verify(WORLD).time == 100
        finally:
            clock.close_session(WORLD)


def test_pure_policies_do_not_modify_world_or_choose_nonlocal_trade(tmp_path):
    db, clock, engine = begin(tmp_path / "pure.sqlite", buyer_site="home")
    try:
        initial = db.load(WORLD)
        frozen = initial.to_dict()
        assert choose_local_production(initial, "basim") is not None
        assert choose_local_food_offer(initial, "salma") is None
        assert choose_local_food_purchase(initial, "adel") is None
        assert db.load(WORLD).to_dict() == frozen
        advance(db, engine)
        after = db.load(WORLD)
        assert choose_local_food_purchase(after, "adel") is None
        assert db.verify(WORLD).to_dict() == after.to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_economic_gate_only_accepts_boolean(tmp_path):
    db, clock, _engine = begin(tmp_path / "gate.sqlite")
    try:
        for value in (1, "true", None):
            with pytest.raises(ValueError, match="economic_enabled"):
                LivingWorldEngine(db, clock, economic_enabled=value)
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.mark.parametrize("grain,copper,expected_jobs,expected_offers,expected_trades", [
    (1, 2, 1, 1, 1),
    (1, 1, 1, 1, 0),
    (0, 2, 0, 0, 0),
])
def test_real_seven_npc_village_runs_without_scripted_market_orders(
        tmp_path, grain, copper, expected_jobs, expected_offers, expected_trades):
    sys.path.insert(0, str(SIM / "scenarios" / "test_village"))
    from play_economic_autonomy import run_economic_village
    result = run_economic_village(tmp_path / "village.sqlite",
                                  grain=grain, buyer_copper=copper)
    assert result["logical_seconds"] == 180
    assert result["verified_replay"] is True
    audit = result["private_test_audit_only"]
    assert audit["npcs"] == 7
    assert audit["finished_jobs"] == expected_jobs
    assert audit["offers"] == expected_offers
    assert audit["trades"] == expected_trades
    assert audit["buyers"] == (["adel"] if expected_trades else [])
    assert audit["autonomous_actions"] >= 6
    assert audit["player_commanded_npc_actions"] == 0
    assert audit["copper_total"] == 10 + copper
    assert audit["final_food_and_coins"]["copper_total"] == 10 + copper
