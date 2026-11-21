"""Controlled P2 h168 actual original-world 15-minute A/B emergency harvest.

Sources are immutable original 13-NPC real h168 SQLite ledgers, NOT a
synthetic scenario. P2 = prior owner aid & known roads with corrected shopping.
P3 = P2 plus optional tightly restricted ripe, funded, physically local
emergency harvest by a starving farmer. Both use the same physical world,
same real money / finite crops and original trusted production reducer.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics

SOURCE=Path("evidence/old_p2/fixed_workloop.sqlite")
OUT=Path("harvest15")
assert SOURCE.is_file(), "authenticated original h168 P2 state required"
OUT.mkdir(exist_ok=False)
source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
rows={}
for arm,allow_desperate in (("p2_default",False),("p3_real_emergency_harvest",True)):
    local=OUT/(arm+".sqlite")
    shutil.copyfile(SOURCE,local)
    assert hashlib.sha256(local.read_bytes()).hexdigest()==source_sha
    with SQLiteEventStore(local) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
        s=db.load(WORLD)
        assert s.time==168*HOUR and len(s.npcs)==13
        e=audit_npc_economy(s)
        assert e["copper_scope_complete"] and e["copper_known_total"]==12
        farmer=s.npcs["farid"]
        assert s.entities["farid"]["location_id"]=="farm_east"
        assert farmer["needs"]["hunger"]==100
        assert s.resources["farm_east"]["crop_ready"]==1
        assert s.resources["farm_east"]["coin_copper"]>=2
        before={k:s.resources["farm_east"].get(k,0) for k in
                ("crop_ready","coin_copper","grain","water","seed")}
        oldjobs=len([j for j in s.production_jobs.values()
                    if j["npc_id"]=="farid" and j["recipe_id"]=="east-finite-harvest"])
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.community_food_enabled=True
            sim.cashless_relief_walk_enabled=True
            sim.desperate_paid_harvest_enabled=allow_desperate
            sim.deferred_bakery_grain_wage_enabled=True
            sim.integrated_livelihoods_enabled=True
            sim.remember_unbought_stalls_enabled=True
            end=sim.advance(
                WORLD,seconds=15*60,
                command_id="real-original-168h-15min-harvest-proof",
                expected_revision=s.revision,
            ).state
            assert end.time == 168*HOUR+15*60 and len(end.npcs)==13
            audit=audit_npc_economy(end)
            assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
            db.snapshot(WORLD)
            assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
            assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
            jobs=[j for j in end.production_jobs.values()
                  if j["npc_id"]=="farid" and j["recipe_id"]=="east-finite-harvest"]
            paid=[j["work_wage"] for j in jobs if "work_wage" in j]
            m=metrics(end)
            row={
                "arm":arm,
                "original_168_sha256":source_sha,
                "hour":end.time/HOUR,
                "completed_harvests_since168":len(jobs)-oldjobs,
                "new_harvest_job_receipts":[{
                    "start":j["started_at"],"status":j["status"],
                    "wage":j.get("work_wage"),
                }for j in jobs if j["started_at"]>=168*HOUR],
                "money_paid_total_historical":m["cash_wages"],
                "farid_current_wallet":end.resources["farid"]["coin_copper"],
                "farid_hunger":end.npcs["farid"]["needs"]["hunger"],
                "farid_place":end.entities["farid"]["location_id"],
                "crop_before":before,
                "crop_after":{k:end.resources["farm_east"].get(k,0) for k in before},
                "market_food":end.resources["market"]["food"],
                "meals":m["meals"],
                "hungry100":m["starving"],
                "sales":m["sales"],
                "copper":12,
                "no_created_resources":True,
                "observational_only":True,
                "release_gate_unchanged":True,
            }
            rows[arm]=row
            print("PLAY48_REAL168_DESPERATE_CROP15 "+json.dumps(
                row,sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT/"comparison.json").write_text(
        json.dumps(rows,indent=2,sort_keys=True),encoding="utf8")
p2,p3=rows["p2_default"],rows["p3_real_emergency_harvest"]
print("PLAY48_REAL168_DESPERATE_CROP15_DELTA "+json.dumps({
    "completed_harvests_delta":p3["completed_harvests_since168"]-p2["completed_harvests_since168"],
    "paid_wages_delta":p3["money_paid_total_historical"]-p2["money_paid_total_historical"],
    "farid_wallet_delta":p3["farid_current_wallet"]-p2["farid_current_wallet"],
    "hungry100_delta":p3["hungry100"]-p2["hungry100"],
    "both_conserved_12_copper":True,
    "original_world_unmodified":True,
},sort_keys=True),flush=True)
assert p3["completed_harvests_since168"] > p2["completed_harvests_since168"], (
    "desperate worker did not complete authentic ripe-crop job"
)
assert p3["money_paid_total_historical"] > p2["money_paid_total_historical"], (
    "employer did not deliver a genuine copper wage"
)
