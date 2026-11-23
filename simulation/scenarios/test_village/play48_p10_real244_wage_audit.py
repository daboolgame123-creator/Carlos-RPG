"""P10 no-write authenticated P9 saved h244 evidence: courier pay, market quotes."""
from pathlib import Path
import hashlib,json
from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD,HOUR
src=Path("evidence/p9_real244")
paths=sorted(src.rglob("P9_hunter_visited_well.sqlite"))
assert len(paths)==1,paths
path=paths[0]; old=hashlib.sha256(path.read_bytes()).hexdigest()
with SQLiteEventStore(path) as db:
    s=db.load(WORLD); d=s.to_dict()
    assert s.time==244*HOUR and len(s.npcs)==13
    assert audit_npc_economy(s)["copper_known_total"]==12
    rows={}
    for who in ("huda","hana","salma","basim","layla","omar","farid","nora"):
        c=d["supply_circuits"].get(who)
        rows[who]={
            "role":d["npcs"][who]["role"],
            "location":d["entities"][who]["location_id"],
            "needs":d["npcs"][who]["needs"],
            "wallet":d["resources"][who],
            "circuit":c,
            "contracts":[{"id":i,**v} for i,v in d["courier_provisions"].items()
                          if v["courier_id"]==who],
        }
    stalls={}
    for site in ("market","bakery","riverbank","hunting_woods","farm","farm_east"):
        offers=[{"id":id,**v} for id,v in d["market_offers"].items()
                if v["site_id"]==site and v["status"]=="open"]
        stalls[site]={"stock":d["resources"][site],
            "uncommitted_food":_available_site_food(s,site),
            "offers":offers,
            "stall":d["market_stalls"].get(site)}
    result={"hour":244,"sha":old,"people":rows,"sites":stalls,
            "copper":12,"fiscal_time":d["time"],
            "aid":[{"id":id,**v} for id,v in d["obligations"].items()
                   if v["resource"]=="food" and v["location_id"]=="well"]}
    print("P10_AUTHENTIC244_WAGE_AUDIT "+json.dumps(result,sort_keys=True),flush=True)
assert hashlib.sha256(path.read_bytes()).hexdigest()==old
