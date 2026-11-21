"""Read-only causal accounting of authentic farm and wage decline at day 7.

Inspect immutable P0/P1 original h96/h168 and bounded work-trip P2 h168 ledgers.
No resimulation, resource changes, inferred wages or new world state.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, metrics

INPUTS=(
    ("p0_h96",Path("evidence/original96/owner_relief_only.sqlite")),
    ("p1_h96",Path("evidence/original96/owner_relief_plus_roads.sqlite")),
    ("p0_h168",Path("evidence/original168/owner_relief_only.sqlite")),
    ("p1_h168",Path("evidence/original168/owner_relief_plus_roads.sqlite")),
    ("p2_h168",Path("evidence/fixed168/fixed_workloop.sqlite")),
)
for label, path in INPUTS:
    assert path.is_file(), f"Required authenticated saved world missing: {path}"
    before_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
        s=db.load(WORLD)
        audit=audit_npc_economy(s)
        assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
        expected=96 if label.endswith("h96") else 168
        assert s.time==expected*HOUR and len(s.npcs)==13
        # Actual job receipts preserve worker, workplace and pay chronology.
        jobs=[{
            "recipe":j.get("recipe_id"),
            "npc":j.get("npc_id"),
            "status":j.get("status"),
            "started":j.get("started_at"),
            "completed":j.get("completed_at"),
            "work_wage":j.get("work_wage"),
            "work_food_wage":j.get("work_food_wage"),
        }for j in s.production_jobs.values()
         if j.get("recipe_id") in (
             "east-finite-harvest","east-seed-planting","finite-harvest",
             "seed-planting","grain-to-bread",
         )]
        sql=sqlite3.connect("file:"+str(path.resolve())+"?mode=ro",uri=True)
        try:
            counts=sql.execute(
                "SELECT json_extract(payload,'$.event_type'),"
                "json_extract(payload,'$.data.recipe_id'),count(*) FROM events "
                "WHERE json_extract(payload,'$.time') >= ? AND "
                "json_extract(payload,'$.event_type') IN "
                "('ProductionStarted','ProductionWagePaid','CropGrowthStarted',"
                "'SupplyCargoDelivered','SupplyCargoPicked','NPCFoodConsumed',"
                "'MarketTradeExecuted','RecurringFreightWagePaid') "
                "GROUP BY 1,2 ORDER BY 1,2",
                (96*HOUR,),
            ).fetchall()
            wages=sql.execute(
                "SELECT json_extract(payload,'$.time'),"
                "json_extract(payload,'$.data.job_id'),"
                "json_extract(payload,'$.data.amount') FROM events "
                "WHERE json_extract(payload,'$.time') >= ? "
                "AND json_extract(payload,'$.event_type')='ProductionWagePaid' "
                "ORDER BY seq",(96*HOUR,)
            ).fetchall()
        finally:
            sql.close()
    assert before_sha==hashlib.sha256(path.read_bytes()).hexdigest()
    m=metrics(s)
    sites={}
    for site in ("farm","farm_east","bakery","well","market"):
        sites[site]={
            "inventory":{k:v for k,v in s.resources.get(site,{}).items()
                         if k in ("coin_copper","grain","seed","water","crop_ready","food","fuel")},
            "farm_plot":s.farm_plots.get(site),
            "supply_circuit":s.supply_circuits.get(site),
        }
    residents={}
    for who in ("farid","nora","basim","hana","huda","salma"):
        npc=s.npcs[who];nav=s.navigation.get(who)
        residents[who]={
            "hunger":npc["needs"]["hunger"],
            "fatigue":npc["needs"]["fatigue"],
            "place":s.entities[who]["location_id"],
            "wallet":s.resources[who].get("coin_copper",0),
            "food":s.resources[who].get("food",0),
            "routine":s.npc_routines.get(who),
            "roads":len(nav["known_routes"]) if nav else 0,
            "recent_meals":m["npcs"][who]["meals"],
        }
    jcounts=Counter((j["recipe"],j["status"]) for j in jobs)
    out={
        "variant":label,"hour":expected,"source_sha256":before_sha,
        "meals":m["meals"],"hungry100":m["starving"],"sales":m["sales"],
        "bread":m["bread"],"cash_wages":m["cash_wages"],"copper":12,
        "sites":sites,"residents":residents,
        "job_counts":{str(k):v for k,v in jcounts.items()},
        "east_farm_jobs":[x for x in jobs if x["recipe"] in ("east-finite-harvest","east-seed-planting")],
        "since96_events":[{"type":t,"recipe":r,"count":n} for t,r,n in counts],
        "paid_wages":[{"time":t,"job_id":job,"copper":c} for t,job,c in wages],
        "read_only":True,
    }
    print("PLAY48_ORIGINAL_FARM_CASH_CAUSE "+json.dumps(out,sort_keys=True,default=str),flush=True)
