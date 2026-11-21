"""Read-only causal overview of genuine original saved96h P0/P1 village.

Inspect real local inventories, jobs, wages, hunger, known roads and signed
community food; do not change the simulation, re-seed or add resources.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from collections import Counter

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.navigation import shortest_known_route
from play48_integrated_acceptance import WORLD, HOUR, metrics

ROOT=Path("evidence/saved96")
for arm in ("owner_relief_only","owner_relief_plus_roads"):
    original=ROOT/(arm+".sqlite")
    assert original.is_file()
    sha=hashlib.sha256(original.read_bytes()).hexdigest()
    with SQLiteEventStore(original) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
        s=db.load(WORLD)
        assert len(s.npcs)==13 and s.time==96*HOUR
        audit=audit_npc_economy(s)
        assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
    assert hashlib.sha256(original.read_bytes()).hexdigest()==sha
    m=metrics(s)

    goods={}
    for place,inv in s.resources.items():
        if place in s.npcs:
            continue
        stocked={k:v for k,v in inv.items()
                 if type(v) is int and v!=0}
        if stocked:
            goods[place]=stocked

    starving=[]
    for who,n in sorted(s.npcs.items()):
        d=m["npcs"][who]
        nav=s.navigation.get(who)
        routes=tuple(nav.get("known_routes",())) if nav else ()
        reachable=bool(shortest_known_route(s,who,"market")) if nav else False
        record={
            "npc":who,
            "role":n.get("role"),
            **d,
            "known_market_path":reachable,
            "known_road_count":len(routes),
            "visited_location_count":len(nav["visited"]) if nav else 0,
            "workplace":s.npc_routines.get(who,{}).get("workplace_id"),
        }
        if d["hunger"]>=75:
            starving.append(record)

    by_job=Counter()
    last_finished={}
    for job in s.production_jobs.values():
        cat=(job.get("recipe_id"),job.get("status"))
        by_job[str(cat)] += 1
        if job["status"]=="completed":
            key=job.get("recipe_id")
            last_finished[key]=max(last_finished.get(key,-1),job.get("completed_at",-1) or -1)

    offer_stats=Counter()
    quoted=[]
    for offer in s.market_offers.values():
        typ=(offer.get("resource"),offer.get("status"))
        offer_stats[str(typ)]+=1
        if offer.get("resource")=="food" and offer.get("status")=="open":
            quoted.append({
                "site":offer.get("site_id"),
                "owner":offer.get("stock_owner_id"),
                "seller":offer.get("seller_id"),
                "remaining":offer.get("remaining"),
                "price":offer.get("unit_price"),
            })

    d={
        "variant":arm,
        "hour":96,
        "sha256":sha,
        "copper":12,
        "meals":m["meals"],
        "hungry100":m["starving"],
        "sales":m["sales"],
        "bread":m["bread"],
        "cash_wages":m["cash_wages"],
        "market_charity_recipients":[x["recipient_id"] for x
                                     in s.market_stalls["market"]["community_food"]["payments"]],
        "market_food_available":s.resources["market"]["food"],
        "hungry75_details":starving,
        "non_npc_physical_inventory":goods,
        "production_jobs":dict(by_job),
        "last_completed_production_at":last_finished,
        "open_food_quotes":quoted,
        "offer_counts":dict(offer_stats),
        "grain_delivery_counts":m["deliveries"],
        "grain_settlement_stats":m["grain_settlements"],
        "cash_by_owner":m["copper_by_owner"],
        "read_only":True,
    }
    print("PLAY48_GENUINE96_INCOME_FOOD_DIAGNOSTIC "+json.dumps(d,sort_keys=True,default=str),flush=True)
