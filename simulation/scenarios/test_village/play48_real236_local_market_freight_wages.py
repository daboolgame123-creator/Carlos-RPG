"""P10: genuine P8 h236 same-ledger P9-vs-P10 real food-work A/B.

No synthetic food, jobs, rights, route, coin, customer quote or transfer.
Only prospective on-site agreement and subsequent verified, paid freight.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

SRC=Path("evidence/authentic236")
OUT=Path("real236_local_market_food_wage")
CHECKPOINTS=(237,240,244)


def info(s, arm):
    m=metrics(s)
    hc=s.supply_circuits["huda"].get("food_payroll", {})
    return {
        "arm":arm,"hour":s.time//HOUR,"starving":m["starving"],
        "bread":m["bread"],"meals":m["meals"],"sales":m["sales"],
        "deliveries":m["deliveries"],
        "huda":m["npcs"]["huda"],"hana":m["npcs"]["hana"],
        "market_owned_food":s.resources["market"]["food"],
        "huda_signed_local_market_wage":bool(hc.get("signed_at")),
        "huda_authentic_market_service_receipts":len(hc.get("receipts",[])),
        "huda_actual_paid_market_wages":sum(x["payment"] is not None for x in hc.get("receipts",[])),
        "huda_original_bakery_contracts":{
            ident:{"payments":len(row["payments"]),
                   "deferred_grain_services":len(row.get("deferred_grain_services",[]))}
            for ident,row in s.courier_provisions.items()
            if row["courier_id"]=="huda"},
        "money":audit_npc_economy(s)["copper_known_total"],
    }


def run_arm(original,arm,new_wages):
    dest=OUT/(arm+".sqlite")
    shutil.copyfile(original,dest)
    assert hashlib.sha256(dest.read_bytes()).digest()==hashlib.sha256(original.read_bytes()).digest()
    rows={}
    with SQLiteEventStore(dest) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s=db.load(WORLD)
            assert len(s.npcs)==13 and s.time==236*HOUR
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
            sim.hunter_well_food_visit_enabled=True
            sim.local_market_freight_wage_enabled=new_wages
            for hour in CHECKPOINTS:
                s=sim.advance(WORLD,seconds=hour*HOUR-s.time,
                              command_id=f"p10-{arm}-{hour}",
                              expected_revision=s.revision).state
                conserve_diverse(s)
                cash=audit_npc_economy(s)
                assert cash["copper_scope_complete"] and cash["copper_known_total"]==12
                db.snapshot(WORLD)
                assert db.verify(WORLD).to_dict()==s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                rows[str(hour)]=info(s,arm)
                print("PLAY48_P10_GENUINE "+json.dumps(rows[str(hour)],sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT/(arm+".json")).write_text(json.dumps(rows,sort_keys=True,indent=2),encoding="utf8")
    return rows


def main():
    matches=sorted(SRC.rglob("P8_voluntary_neighbor_well.sqlite"))
    assert len(matches)==1,matches
    original=matches[0]
    sha=hashlib.sha256(original.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    a=run_arm(original,"P9_hunter_control",False)
    b=run_arm(original,"P10_market_food_wage",True)
    assert hashlib.sha256(original.read_bytes()).hexdigest()==sha
    delta={}
    for hour in CHECKPOINTS:
        x,y=a[str(hour)],b[str(hour)]
        delta[str(hour)]={
            "hour":hour,
            "huda_paid_wages":y["huda_actual_paid_market_wages"]-x["huda_actual_paid_market_wages"],
            "huda_meals":y["huda"]["meals"]-x["huda"]["meals"],
            "huda_hunger":y["huda"]["hunger"]-x["huda"]["hunger"],
            "huda_deliveries":y["deliveries"]["huda"]-x["deliveries"]["huda"],
            "starving_reduction":x["starving"]-y["starving"],
            "money":12, "source_sha256":sha,
            "release_gate":"PLAY48_NO_GO",
        }
        print("PLAY48_P10_MINUS_P9 "+json.dumps(delta[str(hour)],sort_keys=True),flush=True)
    (OUT/"comparison.json").write_text(
        json.dumps({"control":a,"candidate":b,"delta":delta},
                   sort_keys=True,indent=2),encoding="utf8")


if __name__=="__main__":
    main()
