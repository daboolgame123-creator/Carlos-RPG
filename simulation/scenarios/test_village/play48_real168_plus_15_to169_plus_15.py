"""Genuine P2/P3 saved 168h+15m histories extended one physical hour.

Purpose: determine whether actual 2 copper employer-paid to the starving
farmer becomes a food purchase and meal; never guarantee or subsidize it.
Both original 13-NPC worlds are preserved and started at the same
original event history. Everything remains observational, not a release gate.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics

INPUT=Path("evidence/real15")
OUT=Path("real169")
OUT.mkdir(exist_ok=False)
rows={}
for arm,enabled in (("p2_default",False),("p3_real_emergency_harvest",True)):
    original=INPUT/(arm+".sqlite")
    assert original.is_file(), "Required genuine h168+15 evidence is missing"
    copy=OUT/(arm+".sqlite")
    shutil.copyfile(original,copy)
    sha=hashlib.sha256(original.read_bytes()).hexdigest()
    assert hashlib.sha256(copy.read_bytes()).hexdigest()==sha
    with SQLiteEventStore(copy) as db:
        old=db.load(WORLD)
        assert old.time==168*HOUR+15*60 and len(old.npcs)==13
        assert audit_npc_economy(old)["copper_known_total"]==12
        before_meals=metrics(old)["npcs"]["farid"]["meals"]
        before_purchases=metrics(old)["npcs"]["farid"]["purchases"]
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.community_food_enabled=True
            sim.cashless_relief_walk_enabled=True
            sim.desperate_paid_harvest_enabled=enabled
            sim.deferred_bakery_grain_wage_enabled=True
            sim.integrated_livelihoods_enabled=True
            sim.remember_unbought_stalls_enabled=True
            end=sim.advance(
                WORLD,seconds=HOUR,
                command_id="physical-followup-168h15-to169h15",
                expected_revision=old.revision
            ).state
            assert end.time == 169*HOUR+15*60 and len(end.npcs)==13
            audit=audit_npc_economy(end)
            assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
            db.snapshot(WORLD)
            assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
            m=metrics(end)
            row={
                "arm":arm,"sim_hour":169.25,
                "source_168h15m_sha256":sha,
                "farid_hunger":end.npcs["farid"]["needs"]["hunger"],
                "farid_wallet":end.resources["farid"]["coin_copper"],
                "farid_food":end.resources["farid"]["food"],
                "farid_site":end.entities["farid"]["location_id"],
                "farid_meals_new":m["npcs"]["farid"]["meals"]-before_meals,
                "farid_purchases_new":m["npcs"]["farid"]["purchases"]-before_purchases,
                "farm_east_grain":end.resources["farm_east"]["grain"],
                "farm_east_copper":end.resources["farm_east"]["coin_copper"],
                "market_food":end.resources["market"]["food"],
                "meals":m["meals"],"hungry100":m["starving"],
                "sales":m["sales"],"cash_wages":m["cash_wages"],
                "copper":12,"observational_only":True,"release_gate_unchanged":True,
            }
            rows[arm]=row
            print("PLAY48_REAL169_HARVEST_FOOD "+json.dumps(row,sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT/"comparison.json").write_text(json.dumps(rows,indent=2,sort_keys=True),encoding="utf8")
a,b=rows["p2_default"],rows["p3_real_emergency_harvest"]
print("PLAY48_REAL169_HARVEST_FOOD_DELTA "+json.dumps({
    "farid_meals":b["farid_meals_new"]-a["farid_meals_new"],
    "farid_purchases":b["farid_purchases_new"]-a["farid_purchases_new"],
    "farid_hunger":b["farid_hunger"]-a["farid_hunger"],
    "all_hunger100":b["hungry100"]-a["hungry100"],
    "wages":b["cash_wages"]-a["cash_wages"],
    "sales":b["sales"]-a["sales"],
    "copper_conserved":True,
},sort_keys=True),flush=True)
