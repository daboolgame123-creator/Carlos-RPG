"""PLAY48 Option A security and genuine 13-NPC physical-food-wage trial.

Uses authentic production/service events and the normal engine: no direct
NPC orders, remote market debits, new copper or post-genesis food gifts.
A transaction can pass while village survival still fails.
"""
from __future__ import annotations

import json

import pytest
from carlos_sim import (
    DomainEvent, InvalidEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine,
)
from carlos_sim.hydrology import FiniteWaterService
from test_play38_multi_farm_couriers import seed_two_field_world, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY
from test_play48h3_early_market_wage import _conserve

HOUR = 3600


def _food_payroll_bootstrap(db, *, initial_market_food, **options):
    assert initial_market_food == 3
    assert options == {
        "water": 2, "seed": 1, "harvest_yield": 3, "personal_food": 0,
        "market_wallets": True, "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    return _joined_bootstrap(
        db, initial_market_food=3,
        bakery_opening_food_wage=True,
        food_for_work_bakery_enabled=True,
    )


def seed(path):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True,
            harvest_wage_copper=2, bootstrap=_food_payroll_bootstrap,
        )
        state = db.load(WORLD)
        state = db.append(WORLD, "food-work:original-needs-and-rain", state.revision, [
            DomainEvent("WaterSourceConfigured", None, "finite original well", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "ordinary hunger", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)
        assert len(state.npcs) == 13
        assert (state.schema_version, state.rules_version) == (45, 63)
        assert state.resources["market"]["food"] == 2
        assert state.resources["bakery"]["food"] == 1
        assert state.production_recipes["grain-to-bread"]["wage_food"] == 1
        assert "wage_coin" not in state.production_recipes["grain-to-bread"]
        assert sum(v.get("coin_copper", 0) for v in state.resources.values()) == 12
        _conserve(state)
        assert db.verify(WORLD).to_dict() == state.to_dict()
        return state


def test_genesis_signing_is_funded_and_forged_job_cannot_extract_food(tmp_path):
    path = tmp_path / "genuine-first-market-salable-two-bread.sqlite"
    genesis = seed(path)
    with SQLiteEventStore(path) as db:
        initial = db.verify(WORLD).to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            for command, who, amount, authorized in (
                ("no-job", None, 1, True),
                ("impersonation", "basim", 1, True),
                ("invalid-quantity", None, 2, True),
                ("no-capability", None, 1, False),
            ):
                evt = DomainEvent("ProductionFoodWagePaid", who,
                    "unearned or unauthorized wage", 0,
                    {"job_id": "fake-baking", "amount": amount})
                with pytest.raises(InvalidEvent):
                    db.append(WORLD, command, genesis.revision, [evt],
                              production_authorized=authorized)
                assert db.verify(WORLD).to_dict() == initial
        finally:
            clock.close_session(WORLD)


def test_real_bakery_jobs_receive_only_existing_local_loaves(tmp_path):
    path = tmp_path / "real-bakery-food-work-hours.sqlite"
    seed(path)
    timeline = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=5000,
                decision_cooldown=3600, economic_enabled=True,
                agriculture_enabled=True, navigation_enabled=True,
                routines_enabled=True, consumption_enabled=True,
                survival_enabled=True, supply_enabled=True,
                shopping_routes_enabled=True,
                multi_professional_markets_enabled=True,
                compound_procurement_enabled=True,
                professional_full_life_enabled=True,
                food_for_work_enabled=True,
            )
            for hour in (6, 12, 18, 24, 30, 36, 42, 48):
                current = db.verify(WORLD)
                state = engine.advance(
                    WORLD, seconds=hour * HOUR - current.time,
                    command_id=f"real:food-work:{hour}",
                    expected_revision=current.revision,
                ).state
                if hour in (24, 48):
                    state = FiniteWaterService(db, clock).record(
                        WORLD, "well", f"food-work-observed-rain-{hour}", 2,
                        command_id=f"food-work-rain-{hour}",
                        expected_revision=state.revision,
                    ).state
                _conserve(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                receipts = [
                    (key, job["food_wage"])
                    for key, job in state.production_jobs.items()
                    if "food_wage" in job
                ]
                assert all(job["worker_id"] == "basim" and
                           job["site_id"] == "bakery" and
                           job["site_before"] == job["site_after"] + 1 and
                           job["worker_after"] == job["worker_before"] + 1
                           for _, job in receipts)
                assert sum(v.get("coin_copper", 0)
                           for v in state.resources.values()) == 12
                timeline.append({
                    "h": hour, "food_wages": len(receipts),
                    "actual_jobs": sum(j["status"] == "completed"
                                       for j in state.production_jobs.values()),
                    "meals": len(state.consumptions),
                    "market_loaves": state.resources["market"]["food"],
                    "bakery_loaves": state.resources["bakery"]["food"],
                    "basim_personal_bread": state.resources["basim"]["food"],
                    "hunger_100": sum(n["needs"]["hunger"] == 100
                                      for n in state.npcs.values()),
                })
            assert receipts, "no real eligible food work was paid"
            paid_id, _ = receipts[0]
            snapshot = db.verify(WORLD).to_dict()
            for who, amount in ((None, 1), ("basim", 1), (None, 2)):
                with pytest.raises(InvalidEvent):
                    db.append(WORLD, f"repeat-food-wage:{who}:{amount}",
                              state.revision, [
                        DomainEvent("ProductionFoodWagePaid", who,
                                    "must reject repeated or forged payment",
                                    state.time, {"job_id": paid_id,
                                                 "amount": amount}),
                    ], production_authorized=True)
                assert db.verify(WORLD).to_dict() == snapshot
        finally:
            clock.close_session(WORLD)
    print("PLAY48_ACTUAL_SITE_FUNDED_FOOD_FOR_WORK " +
          json.dumps(timeline, sort_keys=True))
