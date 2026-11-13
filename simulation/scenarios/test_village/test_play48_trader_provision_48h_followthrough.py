"""PLAY48 exact-resourced 48h observation of a true two-unit merchant supply.

No substitutions for natural physical biology. A successful 24h local meal
does not prove the village can survive the depleted aquifer/wild ecology.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_real_watch_income_24h import seed, engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures


def test_genuine_48h_post24_trader_meal_protection_does_not_claim_new_resources(tmp_path):
    path = tmp_path / "two-real-forest-portions-through-48h.sqlite"
    start = seed(path)
    assert len(start.npcs) == 13
    assert audit_npc_economy(start)["copper_known_total"] == 12
    checkpoints = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            trial = engine(db, clock, reserve_trader_meal=True)
            for hour in (6, 12, 24, 30, 36, 48):
                before = db.verify(WORLD)
                now = trial.advance(
                    WORLD, seconds=hour*HOUR - before.time,
                    command_id=f"real-trader-physical-48h:{hour}",
                    expected_revision=before.revision,
                ).state
                assert len(now.npcs) == 13
                assert now.time == hour*HOUR
                conserve_diverse(now)
                assert db.verify(WORLD).to_dict() == now.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                budget = audit_npc_economy(now)
                assert budget["copper_scope_complete"]
                assert budget["copper_known_total"] == 12
                row = measures(now)
                row["food_by_person"] = {
                    who: now.resources[who].get("food", 0)
                    for who in sorted(now.npcs)
                }
                row["hunger_by_person"] = {
                    who: info["needs"]["hunger"] for who, info
                    in sorted(now.npcs.items())
                }
                row["meals_by_person"] = {
                    who: sum(m["npc_id"] == who for m in now.consumptions.values())
                    for who in sorted(now.npcs)
                }
                row["hunter_source_food_purchased"] = sum(
                    t["quantity"] for t in now.market_trades.values()
                    if t["buyer_id"] == "repairman"
                    and t["site_id"] == "hunting_woods"
                    and t["resource"] == "food"
                )
                row["sold_to_guard_by_peddler"] = sum(
                    t["quantity"] for t in now.market_trades.values()
                    if t["buyer_id"] == "adel" and t["seller_id"] == "repairman"
                    and t["site_id"] == "market" and t["resource"] == "food"
                )
                row["genuine_salaries_paid"] = sum(
                    "work_wage" in j or "food_wage" in j
                    for j in now.production_jobs.values()
                )
                checkpoints.append(row)
                print("PLAY48_TRADER_TWO_REAL_UNITS_48H_PHYSICAL_CHECK " +
                      json.dumps(row, sort_keys=True), flush=True)
            assert checkpoints[-1]["hunger_by_person"]["repairman"] < 100
            assert checkpoints[-1]["hunter_source_food_purchased"] >= 2
            assert checkpoints[-1]["sold_to_guard_by_peddler"] >= 1
            assert checkpoints[-1]["meals_by_person"]["repairman"] >= 1
        finally:
            clock.close_session(WORLD)
