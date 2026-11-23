"""P9 read-only audit of real P8 h236: who can lawfully feed Huda next?

Uses immutable event-sourced h236 P8 saved world. No synthetic resource transfer
or state mutation. Reveal local owner balance, donor fatigue and OWN known
physical roads (not remote NPC intentions).
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.navigation import shortest_known_route
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD, HOUR, metrics

SOURCE=Path("evidence/authentic236")
OUT=Path("real236_second_courier_diagnostics")


def main():
    files=sorted(SOURCE.rglob("P8_voluntary_neighbor_well.sqlite"))
    assert len(files)==1, files
    source=files[0]
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    with SQLiteEventStore(source) as db:
        s=db.load(WORLD)
        assert s.time==236*HOUR and len(s.npcs)==13
        cash=audit_npc_economy(s)
        assert cash["copper_scope_complete"] and cash["copper_known_total"]==12
        npcs={}
        for who in sorted(s.npcs):
            who_site=s.entities[who]["location_id"]
            known=s.navigation.get(who,{}).get("known_routes",[])
            seen=s.navigation.get(who,{}).get("visited",[])
            here_roads=[{"id":rid,"to":r["b"] if r["a"]==who_site else r["a"],"seconds":r["seconds"],
                        "known":rid in known} for rid,r in sorted(s.routes.items())
                        if who_site in (r["a"],r["b"])]
            npcs[who]={
                "role":s.npcs[who]["role"],"site":who_site,
                "hunger":s.npcs[who]["needs"]["hunger"],
                "fatigue":s.npcs[who]["needs"]["fatigue"],
                "safety":s.npcs[who]["needs"]["safety"],
                "owned_food":s.resources.get(who,{}).get("food"),
                "owned_copper":s.resources.get(who,{}).get("coin_copper"),
                "workplace":s.npc_routines.get(who,{}).get("workplace_id"),
                "visited":list(seen),"known_roads":list(known),
                "adjacent_roads":here_roads,"own_known_path_to_well":list(shortest_known_route(s,who,"well")),
                "known_food_business":list(s.npcs[who].get("beliefs",{}).keys())[:15],
            }
        site_stocks={place:{"food":s.resources.get(place,{}).get("food"),
                            "copper":s.resources.get(place,{}).get("coin_copper"),
                            "unquoted_food":_available_site_food(s,place)}
                     for place in s.locations}
        reqs=[{"id":oid,"from":o["requester"],"to":o["provider"],"status":o["status"],
               "where":o["location_id"],"created_at":o["created_at"]}
              for oid,o in s.obligations.items()
              if o["location_id"]=="well" and o["resource"]=="food"]
        report={
            "source_sha256":sha,"hour":236,"npcs":npcs,
            "well_assistance":reqs,"site_stocks":site_stocks,
            "community_relief":s.to_dict()["market_stalls"]["market"].get("community_food"),
            "courier_rounds":{k:dict(v) for k,v in s.to_dict()["supply_circuits"].items()},
            "copper_total":12,
        }
        print("PLAY48_REAL236_SECOND_COURIER_AUDIT "+
              json.dumps({k:v for k,v in report.items()
                          if k not in ("courier_rounds","community_relief")},
                         sort_keys=True),flush=True)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
    (OUT/"report.json").write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")


if __name__=="__main__":
    main()
