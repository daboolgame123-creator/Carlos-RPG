"""PLAY-47 actual 72-hour autonomous joined-world observation.

No player orders, manual trade, forced NPC movement or post-start supply.
This is a *scarcity* endurance experiment, NOT survival success or release.
Two separately initialized SQLite worlds use existing trusted hunger policies.
"""
from __future__ import annotations

import json
from contextlib import ExitStack

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply_diagnostics import audit_courier
from play_physical_supply import DAY, WORLD, audit_physical_supply
from test_play47_joined_professions import _joined_bootstrap, _engine


def _with_slower_metabolism(db, state):
    return db.append(
        WORLD, "play47:72h:slower-physiology", state.revision,
        [DomainEvent(
            "MetabolismPolicyConfigured", None,
            "trusted time-zero existing physiology counterfactual", 0,
            {"hunger_seconds_per_point": 3600, "activity_hunger_percent": 20},
        )],
        bootstrap=True,
    )


@pytest.mark.parametrize("hunger_period_seconds", [300, 3600])
def test_one_real_eleven_npc_world_72_hours_with_finite_food(
    tmp_path, hunger_period_seconds,
):
    path = tmp_path / f"joined-72h-{hunger_period_seconds}.sqlite"
    with ExitStack() as session:
        db = session.enter_context(SQLiteEventStore(path))
        state = _joined_bootstrap(db)
        if hunger_period_seconds == 3600:
            state = _with_slower_metabolism(db, state)
        assert len(state.npcs) == 11
        initial = audit_npc_economy(state)
        assert initial["copper_scope_complete"]
        assert initial["copper_known_total"] == 12
        assert initial["trades"] == 0
        assert initial["completed_jobs"] == 0
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        session.callback(clock.close_session, WORLD)
        engine = _engine(db, clock)
        measures = []
        known_water_at_start = sum(
            entry["water"] for entry in state.resources.values()
            if "water" in entry and entry["water"] is not None
        )
        previous_counts = (0, 0, 0)
        for tick in range(DAY // 4, 3 * DAY + 1, DAY // 4):
            state = engine.advance(
                WORLD, seconds=tick - state.time,
                command_id=f"play47:72h:{hunger_period_seconds}:{tick}",
                expected_revision=state.revision,
            ).state
            assert state.time == tick
            current = audit_npc_economy(state)
            assert current["copper_scope_complete"]
            assert current["copper_known_total"] == 12
            assert len(current["npc_hunger"]) == 11
            assert all(
                type(h) is int and 0 <= h <= 100
                for h in current["npc_hunger"].values()
            )
            current_counts = (
                current["trades"],
                current["completed_jobs"],
                current["wage_receipts"],
            )
            assert all(a >= b for a, b in zip(current_counts, previous_counts))
            previous_counts = current_counts
            known_water_now = sum(
                entry["water"] for entry in state.resources.values()
                if "water" in entry and entry["water"] is not None
            )
            # This closed-world fixture has no authorized rainfall
            # observations. Water is physically carried or consumed,
            # never credited by the test or recreated for free.
            assert known_water_now <= known_water_at_start
            assert not any(
                type(value) is not int or value < 0
                for entry in state.resources.values()
                for value in entry.values() if value is not None
            )
            physical = audit_physical_supply(
                state, seed=1, water=2, buyer_copper=2, initial_market_food=3,
            )
            if tick % DAY == 0:
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                courier = audit_courier(
                    state, "huda", supply_enabled=engine.supply_enabled,
                )
                measures.append({
                    "day": tick // DAY,
                    "hunger_at_100": sum(
                        value == 100 for value in current["npc_hunger"].values()
                    ),
                    "trades": current["trades"],
                    "jobs": current["completed_jobs"],
                    "wages": current["wage_receipts"],
                    "copper": current["copper_known_total"],
                    "known_water": known_water_now,
                    "physical_supply": physical,
                    "courier": courier,
                    "ripe_crops": state.resources["farm"]["crop_ready"],
                    "farm_grain": state.resources["farm"]["grain"],
                    "bakery_grain": state.resources["bakery"]["grain"],
                    "market_food": state.resources["market"]["food"],
                    "completed_food_jobs": {
                        recipe_id: sum(
                            job["recipe_id"] == recipe_id
                            and job["status"] == "completed"
                            for job in state.production_jobs.values()
                        )
                        for recipe_id in ("seed-planting", "finite-harvest", "grain-to-bread")
                    },
                    "meals_eaten": sum(
                        meal["quantity"] for meal in state.consumptions.values()
                    ),
                })
                if tick < 3 * DAY:
                    session.close()
                    db = session.enter_context(SQLiteEventStore(path))
                    assert db.load(WORLD).to_dict() == state.to_dict()
                    clock = TimeEngine(db)
                    clock.open_session(WORLD)
                    session.callback(clock.close_session, WORLD)
                    engine = _engine(db, clock)
        assert state.time == 3 * DAY
        assert current["trades"] >= 6
        assert current["completed_jobs"] >= 2
        assert current["wage_receipts"] >= 1
        if hunger_period_seconds == 300:
            assert measures[0]["hunger_at_100"] == 11
            assert measures[-1]["ripe_crops"] == 1
            assert measures[-1]["completed_food_jobs"]["finite-harvest"] == 0
        else:
            assert measures[-1]["completed_food_jobs"]["finite-harvest"] >= 1
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        print("PLAY47_REAL_JOINED_72H", json.dumps(
            {"hunger_seconds_per_point": hunger_period_seconds,
             "checkpoints": measures}, sort_keys=True,
        ))


def test_worker_provisions_allow_grain_to_reach_basim_before_huda_stops(tmp_path):
    """Move the same three opening loaves to workers at trusted genesis."""
    with SQLiteEventStore(tmp_path / "joined-worker-provisions.sqlite") as db:
        state = _with_slower_metabolism(db, _joined_bootstrap(db, staff_provisions=True))
        assert state.resources["market"]["food"] == 0
        assert all(state.resources[who]["food"] == 1 for who in ("nora", "huda", "basim"))
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            post_harvest_run = DAY + DAY // 4
            checkpoints = (*range(DAY // 4, DAY + 1, DAY // 4),
                           post_harvest_run, post_harvest_run + 2_000)
            for tick in checkpoints:
                state = engine.advance(
                    WORLD, seconds=tick - state.time,
                    command_id=f"play47:staff-provisions:{tick}",
                    expected_revision=state.revision,
                ).state
                assert state.time == tick
                audit_physical_supply(
                    state, seed=1, water=2, buyer_copper=2, initial_market_food=3,
                )
            assert any(
                meal["npc_id"] == "huda" for meal in state.consumptions.values()
            )
            assert any(
                job["npc_id"] == "basim" and job["recipe_id"] == "grain-to-bread"
                and job["status"] == "completed"
                for job in state.production_jobs.values()
            )
            assert state.resources["bakery"]["food"] == 1
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
