"""PLAY48 P9 saved 13-NPC h236: honest P8 vs P9 real hunter well-aid A/B.

Both worlds copy identical P8 genuine event save. No new seeds, money,
assistance contract, food, road or travel instant. A willing hunter may
discover known public well routes from physically surveyed adjacent roads;
an actual hungry recipient must still ask and receive authentic ONE food.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SOURCE = Path("evidence/authentic236")
OUT = Path("real236_hunter_second_courier")
CHECKPOINTS=(237, 240, 244)


def report(s, arm):
    m=metrics(s)
    actual_huda_help=[
        {"donor":o["provider"],"recipient":o["requester"],"at":o["resolved_at"]}
        for o in s.obligations.values()
        if o["requester"]=="huda" and o["location_id"]=="well"
        and o["resource"]=="food" and o["status"]=="fulfilled"]
    return {
        "arm":arm,"hour":s.time//HOUR,"bread":m["bread"],
        "meals":m["meals"],"sales":m["sales"],"hungry100":m["starving"],
        "deliveries":m["deliveries"],"freight_wages":m["freight_wages"],
        "huda":m["npcs"]["huda"],"hana":m["npcs"]["hana"],
        "omar":m["npcs"]["omar"],"layla":m["npcs"]["layla"],
        "huda_real_well_food_help":actual_huda_help,
        "omar_known_roads":list(s.navigation["omar"]["known_routes"]),
        "omar_personally_visited":list(s.navigation["omar"]["visited"]),
        "market_food":s.resources["market"]["food"],
        "copper_total":audit_npc_economy(s)["copper_known_total"],
    }


def run_arm(source, arm, enabled):
    copied=OUT/(arm+".sqlite")
    shutil.copyfile(source,copied)
    assert hashlib.sha256(copied.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
    rows={}
    with SQLiteEventStore(copied) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s=db.load(WORLD)
            assert s.time==236*HOUR and len(s.npcs)==13
            assert s.npcs["huda"]["needs"]["hunger"]==100
            assert s.resources["omar"]["food"]>=1
            assert s.resources["huda"]["food"]==0
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.community_food_enabled=True
            sim.cashless_relief_walk_enabled=True
            sim.desperate_paid_harvest_enabled=True
            sim.deferred_bakery_grain_wage_enabled=True
            sim.integrated_livelihoods_enabled=True
            sim.remember_unbought_stalls_enabled=True
            sim.reserve_signed_relief_offer_enabled=True
            sim.desperate_funded_planting_enabled=True
            sim.hungry_paid_baker_return_enabled=True
            sim.signed_steward_wage_quote_rescue_enabled=True
            sim.voluntary_well_food_visit_enabled=True
            sim.hunter_well_food_visit_enabled=enabled
            for hr in CHECKPOINTS:
                s=sim.advance(WORLD,seconds=hr*HOUR-s.time,
                    command_id=f"real236-hunter-{arm}-{hr}",
                    expected_revision=s.revision).state
                conserve_diverse(s)
                cash=audit_npc_economy(s)
                assert cash["copper_scope_complete"] and cash["copper_known_total"]==12
                assert len(s.npcs)==13
                db.snapshot(WORLD)
                assert db.load(WORLD).to_dict()==s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                rows[str(hr)]=report(s,arm)
                print("PLAY48_REAL236_HUNTER_SECOND_COURIER "+json.dumps(rows[str(hr)],sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT/(arm+"-report.json")).write_text(
        json.dumps(rows,indent=2,sort_keys=True),encoding="utf-8")
    return rows


def main():
    matches=sorted(SOURCE.rglob("P8_voluntary_neighbor_well.sqlite"))
    assert len(matches)==1,matches
    source=matches[0]
    original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    a=run_arm(source,"P8_control",False)
    b=run_arm(source,"P9_hunter_visited_well",True)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==original_hash
    difference={}
    for h in CHECKPOINTS:
        old,new=a[str(h)],b[str(h)]
        difference[str(h)]={
            "hour":h,
            "huda_rescues":len(new["huda_real_well_food_help"])-len(old["huda_real_well_food_help"]),
            "huda_meals":new["huda"]["meals"]-old["huda"]["meals"],
            "huda_hunger":new["huda"]["hunger"]-old["huda"]["hunger"],
            "huda_deliveries":new["deliveries"]["huda"]-old["deliveries"]["huda"],
            "total_hungry100":new["hungry100"]-old["hungry100"],
            "copper_total":12,"same_original_sha256":original_hash,
            "release_gate":"PLAY48_NO_GO",
        }
        print("PLAY48_P9_MINUS_P8 "+json.dumps(difference[str(h)],sort_keys=True),flush=True)
    (OUT/"comparison.json").write_text(
        json.dumps({"control":a,"candidate":b,"difference":difference},
                   indent=2,sort_keys=True),encoding="utf-8")


if __name__=="__main__":
    main()
