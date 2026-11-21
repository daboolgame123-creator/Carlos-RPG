"""Real saved h180 P4 farm/market A-B: consented P5 planting vs default.

Independent copies of the exact original 13-NPC, 12-copper h180 event
ledger. No new characters, rainfall, currency, food, seeds, water or receipts.
Existing engine reducers alone produce all harvest wages and purchases.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SOURCE = Path("evidence/genuine180")
OUT = Path("funded_seed222")
HOURS = (193, 217, 222)


def run_arm(source: Path, arm: str, funded_planting: bool) -> dict:
    dest = OUT / (arm + ".sqlite")
    shutil.copyfile(source, dest)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    assert hashlib.sha256(dest.read_bytes()).hexdigest() == before
    rows = {}
    with SQLiteEventStore(dest) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s = db.load(WORLD)
            assert s.time == 180 * HOUR and len(s.npcs) == 13
            assert audit_npc_economy(s)["copper_known_total"] == 12
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            sim.community_food_enabled = True
            sim.cashless_relief_walk_enabled = True
            sim.desperate_paid_harvest_enabled = True
            sim.deferred_bakery_grain_wage_enabled = True
            sim.integrated_livelihoods_enabled = True
            sim.remember_unbought_stalls_enabled = True
            sim.reserve_signed_relief_offer_enabled = True
            sim.desperate_funded_planting_enabled = funded_planting
            for hour in HOURS:
                s = sim.advance(
                    WORLD, seconds=hour * HOUR - s.time,
                    command_id=f"real180-optional-plant-{arm}-{hour}",
                    expected_revision=s.revision).state
                assert s.time == hour * HOUR and len(s.npcs) == 13
                conserve_diverse(s)
                audit = audit_npc_economy(s)
                assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
                db.snapshot(WORLD)
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                info = metrics(s)
                npc = info["npcs"]["farid"]
                row = {
                    "arm": arm, "hour": hour,
                    "hungry100": info["starving"], "meals": info["meals"],
                    "sales": info["sales"], "wages": info["cash_wages"],
                    "bread": info["bread"],
                    "farm_east_seed": s.resources["farm_east"]["seed"],
                    "farm_east_water": s.resources["farm_east"]["water"],
                    "farm_east_grain": s.resources["farm_east"]["grain"],
                    "farm_east_copper": s.resources["farm_east"]["coin_copper"],
                    "farm_east_field": s.farm_plots["farm_east"]["status"],
                    "farid": npc,
                    "east_seed_jobs": sum(j["status"] == "completed" and
                                          j["recipe_id"] == "east-seed-planting"
                                          for j in s.production_jobs.values()),
                    "east_harvest_jobs": sum(j["status"] == "completed" and
                                             j["recipe_id"] == "east-finite-harvest"
                                             for j in s.production_jobs.values()),
                    "east_cash_paid": sum("work_wage" in j and
                                         j["recipe_id"] == "east-finite-harvest"
                                         for j in s.production_jobs.values()),
                    "original_record_untouched": True, "total_copper": 12,
                    "release_gate": "PLAY48_NO_GO",
                }
                rows[str(hour)] = row
                print("PLAY48_REAL180_FUNDED_SEED " + json.dumps(
                    row, sort_keys=True), flush=True)
                (OUT / (arm + "-observations.json")).write_text(
                    json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")
        finally:
            clock.close_session(WORLD)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    return rows


def main() -> None:
    originals = sorted(SOURCE.rglob("P4_signed_quote_relief.sqlite"))
    assert len(originals) == 1, originals
    source = originals[0]
    OUT.mkdir(exist_ok=False)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    rows = {
        "P4_control": run_arm(source, "P4_control", False),
        "P5_funded_seed": run_arm(source, "P5_funded_seed", True),
    }
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    for hour in HOURS:
        p4, p5 = (rows[arm][str(hour)] for arm in rows)
        delta = {key: p5[key] - p4[key] for key in
                 ("hungry100", "meals", "sales", "wages",
                  "east_seed_jobs", "east_harvest_jobs", "east_cash_paid")}
        print("PLAY48_REAL180_FUNDED_SEED_DELTA " + json.dumps({
            "hour": hour, "P5_minus_P4": delta, "release_gate": "PLAY48_NO_GO",
            "source_sha256": before,
        }, sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")


if __name__ == "__main__":
    main()
