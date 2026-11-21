"""Read-only compare actual 13-NPC P0 and P1 h168 economics and work.

The factual, original 96→168 saved SQLite event ledgers came from Actions
44894923168 and include every authenticated physical trip, wage and ration.
No world progression, reset, intervention, seeded resources, or PR merge.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, metrics

FILES=Path("evidence/saved168")
for arm in ("owner_relief_only", "owner_relief_plus_roads"):
    path=FILES / (arm+".sqlite")
    assert path.exists(), f"Real h168 history missing: {path}"
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
        world=db.load(WORLD)
        assert world.time == 168*HOUR and len(world.npcs)==13
        econ=audit_npc_economy(world)
        assert econ["copper_scope_complete"] and econ["copper_known_total"] == 12
        events=db.db.execute(
            "SELECT json_extract(payload,'$.event_type'),"
            "json_extract(payload,'$.actor_id'),"
            "json_extract(payload,'$.data.job_id'),"
            "json_extract(payload,'$.data.npc_id'),"
            "json_extract(payload,'$.data.recipient_id'),"
            "json_extract(payload,'$.cause'),COUNT(*) "
            "FROM events WHERE json_extract(payload,'$.time') >= ? "
            "GROUP BY 1,2,3,4,5,6 ORDER BY 1,2,3,4,5,6",
            (96*HOUR,)
        ).fetchall()
        pay_events=db.db.execute(
            "SELECT json_extract(payload,'$.time'),"
            "json_extract(payload,'$.data.job_id'),"
            "json_extract(payload,'$.data.amount') "
            "FROM events WHERE json_extract(payload,'$.time') >= ? "
            "AND json_extract(payload,'$.event_type')='ProductionWagePaid' "
            "ORDER BY seq", (96*HOUR,)
        ).fetchall()
        grants=db.db.execute(
            "SELECT json_extract(payload,'$.time'),"
            "json_extract(payload,'$.data.recipient_id') FROM events "
            "WHERE json_extract(payload,'$.time') >= ? "
            "AND json_extract(payload,'$.event_type')='MarketCommunityRationIssued' "
            "ORDER BY seq", (96*HOUR,)
        ).fetchall()
        # Distinguish economically useful movements from commuting/exploration.
        travel_cause_by_npc=Counter()
        for et,actor,job,who,recipient,cause,count in events:
            if et=="NPCTravelStarted":
                travel_cause_by_npc[(actor,cause)] += count
        event_counts=Counter()
        for et,actor,job,who,recipient,cause,count in events:
            event_counts[et] += count

    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha, "audit may not modify original evidence"
    m=metrics(world)
    payday=Counter()
    for time,job_id,amount in pay_events:
        job=world.production_jobs.get(job_id,{})
        worker=job.get("npc_id") or job.get("worker_id")
        if worker is None:
            worker=str(job_id)
        payday[str(worker)]+=int(amount or 0)

    tripcounts=Counter()
    for (who,cause),count in travel_cause_by_npc.items():
        tripcounts[who]+=count
    NPC={}
    for who,n in sorted(world.npcs.items()):
        owned=world.resources[who]
        nav=world.navigation.get(who)
        old=m["npcs"][who]
        NPC[who]={
            "role":n["role"],
            "hunger":old["hunger"],
            "fatigue":old["fatigue"],
            "location":old["site"],
            "cash":old["cash"],
            "food":old["food"],
            "meals":old["meals"],
            "purchases":old["purchases"],
            "real_wages_after96":payday.get(who,0),
            "travel_after96":tripcounts.get(who,0),
            "known_road_count":len(nav["known_routes"]) if nav else 0,
            "visited":len(nav["visited"]) if nav else 0,
            "workplace":world.npc_routines.get(who,{}).get("workplace_id"),
        }
    physical_sites={
        site:{key:num for key,num in inv.items()
              if key in ("coin_copper","food","grain") and num>0}
        for site,inv in world.resources.items()
        if site not in world.npcs
    }
    production=Counter()
    for job in world.production_jobs.values():
        production[(job.get("recipe_id"),job.get("status"))]+=1
    quotes=[{
        "site":o.get("site_id"),"seller":o.get("seller_id"),
        "owner":o.get("stock_owner_id"),"food_units":o.get("remaining"),
        "price":o.get("unit_price")
    }for o in world.market_offers.values()
      if o.get("resource")=="food" and o.get("status")=="open"]
    out={
        "arm":arm,"hour":168,"sha256":sha,
        "meals":m["meals"],"hungry100":m["starving"],
        "sales":m["sales"],"bread":m["bread"],"cash_wages":m["cash_wages"],
        "copper":12,"charity":len(world.market_stalls["market"]["community_food"]["payments"]),
        "market_stock":world.resources["market"]["food"],
        "npc":NPC,
        "site_inventory":physical_sites,
        "food_quotes":quotes,
        "production_jobs":{str(k):v for k,v in production.items()},
        "wages_paid_since96":[{"time":t,"job_id":j,"amount":a} for t,j,a in pay_events],
        "rations_since96":[{"time":t,"npc_id":who} for t,who in grants],
        "event_counts_96_to168":dict(event_counts),
        "travel_by_cause_96_to168":[{"npc":who,"cause":cause,"n":n}
          for (who,cause),n in sorted(travel_cause_by_npc.items(),
               key=lambda item:(-item[1],item[0]))[:22]],
        "read_only":True,
    }
    print("PLAY48_168_REAL_CAUSAL_AUDIT "+json.dumps(out,sort_keys=True),flush=True)
