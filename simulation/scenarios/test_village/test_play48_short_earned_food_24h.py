"""PLAY48 6-hour earned-food trial: authentic same-source 13NPC 24h evidence.

This *single experimental branch* changes only a wage cadence from 36 to 6
simulation hours. It does NOT grant food, coins, jobs, forced NPC behavior,
population changes, or renewable ecology, and a passing test is not GO.
"""
from __future__ import annotations

import json

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import FOOD_WAGE_COOLDOWN_SECONDS
from test_play38_multi_farm_couriers import WORLD
from test_play48_peddler_fast import seed
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures, market_resale_gates

HOUR = 3600


def test_real_24h_short_cadence_world_is_paid_only_from_existing_food(tmp_path):
    assert FOOD_WAGE_COOLDOWN_SECONDS == 6 * HOUR
    path = tmp_path / "play48-real-short-cadence.sqlite"
    initial = seed(path)
    report = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = LivingWorldEngine(
                db, clock, max_events_per_advance=9000,
                decision_cooldown=3600, economic_enabled=True,
                agriculture_enabled=True, navigation_enabled=True,
                routines_enabled=True, consumption_enabled=True,
                survival_enabled=True, supply_enabled=True,
                shopping_routes_enabled=True,
                multi_professional_markets_enabled=True,
                compound_procurement_enabled=True,
                professional_full_life_enabled=True,
                food_for_work_enabled=True,
                food_peddler_enabled=True,
                seek_alternative_food_market_enabled=True,
            )
            for hour in (6, 12, 18, 24):
                prev = db.verify(WORLD)
                state = engine.advance(
                    WORLD, seconds=hour * HOUR - prev.time,
                    command_id=f"short-real-earned-food:{hour}",
                    expected_revision=prev.revision,
                ).state
                assert len(state.npcs) == 13
                assert state.time == hour * HOUR
                assert (state.schema_version, state.rules_version) == (45, 63)
                conserve_diverse(state)
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                money = audit_npc_economy(state)
                assert money["copper_scope_complete"]
                assert money["copper_known_total"] == 12
                by_worker = {}
                for job in state.production_jobs.values():
                    receipt = job.get("food_wage")
                    if receipt is None:
                        continue
                    worker = job["npc_id"]
                    assert job["status"] == "completed"
                    recipe = state.production_recipes[job["recipe_id"]]
                    assert recipe["wage_food"] == receipt["amount"]
                    assert receipt["site_before"] - receipt["site_after"] == receipt["amount"]
                    assert receipt["worker_after"] - receipt["worker_before"] == receipt["amount"]
                    by_worker.setdefault(worker, []).append(receipt["paid_at"])
                for worker, times in by_worker.items():
                    sorted_times = sorted(times)
                    assert all(b - a >= FOOD_WAGE_COOLDOWN_SECONDS
                               for a, b in zip(sorted_times, sorted_times[1:])), worker
                metrics = measures(state)
                metrics["paid_food_portions_by_worker"] = {
                    worker: sum(
                        job["food_wage"]["amount"] for job in
                        state.production_jobs.values()
                        if job["npc_id"] == worker and "food_wage" in job
                    ) for worker in sorted(by_worker)
                }
                metrics["trader_available_customers"] = (
                    market_resale_gates(state)["eligible_on_site_purchases"]
                )
                report.append(metrics)
            assert initial.world_id == db.load(WORLD).world_id
        finally:
            clock.close_session(WORLD)
    print("PLAY48_AUTHENTIC_6H_PAID_WAGE_24H_EXPERIMENT " +
          json.dumps(report, sort_keys=True), flush=True)
