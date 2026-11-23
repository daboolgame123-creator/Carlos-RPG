"""PLAY48 P11: two genuine saved h240 worlds, no synthetic subsidy.

The proven P10 and P11 h240 SQLite ledgers are immutable inputs. Advance
both with unchanged feature flags through h244, h252 and h264. A *new* later
paid receipt requires an actual later grain delivery and physical market visit;
no salary is granted merely because time passed. Conservation, 13 NPCs,
legitimate historic event replay and real deliveries remain mandatory.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD,HOUR,engine,metrics,conserve_diverse

SOURCE=Path("evidence/p11_real240")
OUT=Path("real240_renewable_market_wage")
CHECKPOINTS=(244,252,264)
FLAGS=(
    "merchant_food_wage_enabled","community_food_enabled",
    "cashless_relief_walk_enabled","desperate_paid_harvest_enabled",
    "deferred_bakery_grain_wage_enabled","integrated_livelihoods_enabled",
    "remember_unbought_stalls_enabled","reserve_signed_relief_offer_enabled",
    "desperate_funded_planting_enabled","hungry_paid_baker_return_enabled",
    "signed_steward_wage_quote_release_enabled",
    "offshift_steward_homeward_enabled",
    "local_emergency_courier_help_enabled","hunter_well_visit_enabled",
)

def facts(s,arm):
    m=metrics(s)
    c=s.to_dict()["supply_circuits"]["huda"]
    contract=c.get("food_payroll")
    return {"arm":arm,"hour":s.time//HOUR,
            "huda":m["npcs"]["huda"],"adel":m["npcs"]["adel"],
            "huda_deliveries":c["deliveries"],"hana_deliveries":m["deliveries"]["hana"],
            "huda_signed_contract":contract,
            "huda_paid_receipts":sum(x["payment"] is not None
                for x in (contract or {}).get("receipts",[])),
            "huda_earned_receipts":len((contract or {}).get("receipts",[])),
            "starving":m["starving"],"meals":m["meals"],
            "market_food":s.resources["market"]["food"],
            "bakery_food":s.resources["bakery"]["food"],
            "copper":audit_npc_economy(s)["copper_known_total"]}

def arm(src,name,paid):
    dest=OUT/(name+".sqlite")
    shutil.copyfile(src,dest)
    rows={}
    with SQLiteEventStore(dest) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s=db.load(WORLD)
            assert s.time==240*HOUR and len(s.npcs)==13
            assert bool(s.supply_circuits["huda"].get("food_payroll"))==paid
            cash=audit_npc_economy(s)
            assert cash["copper_scope_complete"] and cash["copper_known_total"]==12
            sim=engine(db,clock,reserve_trader_meal=True,deferred_market_courier_wage=True)
            for flag in FLAGS:
                setattr(sim,flag,True)
            sim.local_market_freight_wage_enabled=paid
            rows["240"]=facts(s,name)
            for hour in CHECKPOINTS:
                s=sim.advance(WORLD,seconds=hour*HOUR-s.time,
                    command_id=f"p11-long-{name}-{hour}",expected_revision=s.revision).state
                conserve_diverse(s)
                cash=audit_npc_economy(s)
                assert cash["copper_scope_complete"] and cash["copper_known_total"]==12
                assert len(s.npcs)==13
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                db.snapshot(WORLD)
                assert db.load(WORLD).to_dict()==s.to_dict()
                rows[str(hour)]=facts(s,name)
                print("PLAY48_P11_LONG "+json.dumps(rows[str(hour)],sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT/(name+".json")).write_text(json.dumps(rows,indent=2,sort_keys=True),encoding="utf8")
    return rows

def main():
    sources={name:sorted(SOURCE.rglob(name+".sqlite"))
             for name in ("P10_rescue_only","P11_real_wage")}
    assert all(len(v)==1 for v in sources.values()),sources
    sha={k:hashlib.sha256(v[0].read_bytes()).hexdigest()
         for k,v in sources.items()}
    OUT.mkdir(exist_ok=False)
    a=arm(sources["P10_rescue_only"][0],"P10_rescue_only",False)
    b=arm(sources["P11_real_wage"][0],"P11_real_wage",True)
    assert sha=={k:hashlib.sha256(v[0].read_bytes()).hexdigest()
                 for k,v in sources.items()}
    comparison={}
    for hour in CHECKPOINTS:
        u,v=a[str(hour)],b[str(hour)]
        comparison[str(hour)]={
            "hour":hour,"huda_hunger_delta":v["huda"]["hunger"]-u["huda"]["hunger"],
            "huda_delivery_delta":v["huda_deliveries"]-u["huda_deliveries"],
            "market_food_delta":v["market_food"]-u["market_food"],
            "huda_meal_delta":v["huda"]["meals"]-u["huda"]["meals"],
            "extra_paid_receipts_after_h240":v["huda_paid_receipts"]-b["240"]["huda_paid_receipts"],
            "starving_delta":v["starving"]-u["starving"],
            "copper":12,"release_gate":"PLAY48_NO_GO",
        }
        print("PLAY48_P11_LONG_COMPARISON "+json.dumps(comparison[str(hour)],sort_keys=True),flush=True)
    (OUT/"comparison.json").write_text(json.dumps({
        "sources":sha,"control":a,"candidate":b,
        "differences":comparison,"status":"PLAY48_NO_GO"
    },indent=2,sort_keys=True),encoding="utf8")
    assert b["264"]["huda_paid_receipts"]>b["240"]["huda_paid_receipts"], (
        "signed market salary has not renewed from later physical freight")
    assert b["264"]["huda"]["hunger"]<a["264"]["huda"]["hunger"],(
        "genuine freight salary failed to improve later worker hunger")

if __name__=="__main__":
    main()
