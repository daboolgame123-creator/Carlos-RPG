"""Continue real saved85h event histories to 87h, preserving all real events.

Two original 13-NPC worlds, P0 owner-signed ration vs P1 signed ration
plus cashless learned-road travel. No new bread/copper, NPC teleport,
omniscient lookup, seed replay or fake jobs. Inspect actual transaction
and travel causes at the end. 96/168h official gate remains separate.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics

INPUT = Path("evidence/real85")
OUT = Path("real87")
OUT.mkdir(exist_ok=False)
results = {}
for arm, seek in (("owner_relief_only", False), ("owner_relief_plus_roads", True)):
    src = INPUT / (arm+".sqlite")
    assert src.is_file(), f"authentic complete saved85 is required for {arm}"
    dst = OUT / (arm+".sqlite")
    shutil.copyfile(src, dst)
    original_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    assert hashlib.sha256(dst.read_bytes()).hexdigest() == original_hash
    with SQLiteEventStore(dst) as db:
        before = db.load(WORLD)
        assert len(before.npcs) == 13 and before.time == 85*HOUR
        assert audit_npc_economy(before)["copper_known_total"] == 12
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.community_food_enabled=True
            sim.cashless_relief_walk_enabled=seek
            sim.deferred_bakery_grain_wage_enabled=True
            sim.integrated_livelihoods_enabled=True
            sim.remember_unbought_stalls_enabled=True
            final=sim.advance(
                WORLD, seconds=2*HOUR,
                command_id="true-original-history-85-to87",
                expected_revision=before.revision,
            ).state
            assert final.time == 87*HOUR and len(final.npcs) == 13
            audit=audit_npc_economy(final)
            assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
            db.snapshot(WORLD)
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            new_travel_causes = db.db.execute(
                "SELECT json_extract(payload,'$.actor_id'), "
                "json_extract(payload,'$.cause'), count(*) FROM events "
                "WHERE seq > ? AND json_extract(payload,'$.event_type') = "
                "'NPCTravelStarted' AND json_extract(payload,'$.actor_id') "
                "IN ('miner','burner','smith') GROUP BY 1,2",
                (before.revision,)
            ).fetchall()
            false_food_returns = sum(
                count for who,cause,count in new_travel_causes
                if cause.startswith("cashless starving resident revisiting")
                and "personally witnessed food quote" not in cause
            )
            assert false_food_returns == 0
            m=metrics(final)
            result={
                "arm":arm,"hour":87,"meals":m["meals"],"hungry100":m["starving"],
                "sales":m["sales"],"bread":m["bread"],
                "cash_wages":m["cash_wages"],
                "community_rations":len(final.market_stalls["market"]["community_food"]["payments"]),
                "market_food":final.resources["market"]["food"],
                "copper":12,
                "false_nonfood_food_market_revisit_trips":false_food_returns,
                "new_ore_coal_smith_trip_causes":[
                    {"npc":who,"cause":cause,"count":count}
                    for who,cause,count in new_travel_causes],
                "source85_sha256":original_hash,
                "source85_revision":before.revision,"revision":final.revision,
                "observational_only":True,"release_gate_unchanged":True
            }
            results[arm]=result
            print("PLAY48_SAVED85_TO87_REAL "+json.dumps(result,sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT/"comparison.json").write_text(json.dumps(results,indent=2,sort_keys=True),encoding="utf8")

a,b=results["owner_relief_only"],results["owner_relief_plus_roads"]
print("PLAY48_SAVED85_TO87_DELTA "+json.dumps({
    "hour":87,"roads_minus_relief":{
        key:b[key]-a[key] for key in
        ("meals","hungry100","sales","bread","community_rations","false_nonfood_food_market_revisit_trips")
    },
    "both_copper_conserved":True,
    "release_gate_unchanged":True,
},sort_keys=True),flush=True)
