"""Extend genuine persisted h84+10m P0/P1 ledgers to the true 85h mark.

This does NOT restart, mint, shortcut, teleport or inject an NPC's route.
The same engine and real underlying 12-copper economy run in both arms.
Avoid full-genesis replay for this incremental observational benchmark.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics

ROOT = Path("evidence/short84")
OUT = Path("real85")
OUT.mkdir(exist_ok=False)
rows = {}
for arm, roads in (("owner_relief_only", False), ("owner_relief_plus_roads", True)):
    original = ROOT / (arm+".sqlite")
    assert original.is_file(), f"authentic h84+10m source is mandatory: {arm}"
    out = OUT / (arm+".sqlite")
    shutil.copyfile(original, out)
    sha = hashlib.sha256(original.read_bytes()).hexdigest()
    assert hashlib.sha256(out.read_bytes()).hexdigest() == sha
    with SQLiteEventStore(out) as db:
        start = db.load(WORLD)
        assert start.time == 84*HOUR + 600 and len(start.npcs) == 13
        assert audit_npc_economy(start)["copper_known_total"] == 12
        travel_start = {who: sum(t["npc_id"] == who for t in start.travels.values())
                        for who in ("miner","burner","smith")}
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            sim.community_food_enabled = True
            sim.cashless_relief_walk_enabled = roads
            sim.deferred_bakery_grain_wage_enabled = True
            sim.integrated_livelihoods_enabled = True
            sim.remember_unbought_stalls_enabled = True
            final = sim.advance(
                WORLD, seconds=50*60,
                command_id="fixed-84h10m-to85h",
                expected_revision=start.revision,
            ).state
            assert final.time == 85*HOUR and len(final.npcs) == 13
            db.snapshot(WORLD)
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
            balance = audit_npc_economy(final)
            assert balance["copper_scope_complete"] and balance["copper_known_total"] == 12
            travel_end = {who: sum(t["npc_id"] == who for t in final.travels.values())
                          for who in travel_start}
            introduced = db.db.execute(
                "SELECT json_extract(payload,'$.actor_id'),"
                "json_extract(payload,'$.cause') FROM events "
                "WHERE seq > ? AND json_extract(payload,'$.event_type')='NPCTravelStarted' "
                "AND json_extract(payload,'$.actor_id') IN ('miner','burner','smith')",
                (start.revision,),
            ).fetchall()
            assert len(introduced) == sum(travel_end[w]-travel_start[w] for w in travel_start)
            false_food_returns = sum(
                cause.startswith("cashless starving resident revisiting")
                and "personally witnessed food quote" not in cause
                for who,cause in introduced
            )
            row = metrics(final)
            report = {
                "arm":arm, "hour":85,"meals":row["meals"],"hungry100":row["starving"],
                "sales":row["sales"],"bread":row["bread"],"cash_wages":row["cash_wages"],
                "copper":12,"charity":len(final.market_stalls["market"]["community_food"]["payments"]),
                "new_three_npc_trips_since84h10":len(introduced),
                "false_nonfood_market_revisits":false_food_returns,
                "source_sha256":sha,"source_revision":start.revision,"end_revision":final.revision,
                "observational_only":True,"release_gate_unchanged":True,
            }
            assert false_food_returns == 0
            rows[arm] = report
            print("PLAY48_REAL85 " + json.dumps(report, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT / "comparison.json").write_text(json.dumps(rows,indent=2,sort_keys=True),encoding="utf8")

a,b=rows["owner_relief_only"],rows["owner_relief_plus_roads"]
print("PLAY48_REAL85_DELTA " + json.dumps({
    "hour":85,"roads_minus_owner": {
        key:b[key]-a[key] for key in ("meals","hungry100","sales","charity",
                                      "false_nonfood_market_revisits")},
    "both_preserve_12_copper":True,
    "observational_only":True,
},sort_keys=True),flush=True)
