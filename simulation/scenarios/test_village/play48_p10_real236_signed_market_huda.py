"""P10 genuine saved h236 autonomy vs immutable P9 h244 control.

Zero intervention into the world: no genesis contract rewrite, no food/cash
injection. A new local *prospective* contract must be signed autonomously
after an actual delivery by an able Huda at the same physical market as Salma.
It only pays actual later food freight, debiting real unquoted merchant food.
"""
from __future__ import annotations
import hashlib,json,shutil
from pathlib import Path
from carlos_sim import SQLiteEventStore,TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD,HOUR,engine,metrics,conserve_diverse

SOURCE=Path("evidence/p8_real236")
CONTROL=Path("evidence/p9_real244")
OUT=Path("real236_signed_market_courier")
HOURS=(237,240,244)


def facts(s,arm):
    m=metrics(s); c=s.supply_circuits["huda"]
    contract=c.get("food_payroll")
    return {"arm":arm,"hour":s.time//HOUR,
            "huda":m["npcs"]["huda"],"hana":m["npcs"]["hana"],
            "huda_deliveries":c["deliveries"],
            "huda_has_new_signed_contract":contract is not None,
            "huda_authentic_service_receipts":(
                s.to_dict()["supply_circuits"]["huda"]["food_payroll"]["receipts"]
                if contract else []),
            "huda_paid_food_wages":sum(r["payment"] is not None for r in contract["receipts"]) if contract else 0,
            "market_food":s.resources["market"]["food"],
            "market_unquoted_food":_available_site_food(s,"market"),
            "meals":m["meals"],"sales":m["sales"],
            "bread":m["bread"],"starving100":m["starving"],"cash":12}


def main():
    sources=sorted(SOURCE.rglob("P8_voluntary_neighbor_well.sqlite"))
    controls=sorted(CONTROL.rglob("P9_hunter_visited_well.sqlite"))
    assert len(sources)==len(controls)==1,(sources,controls)
    source,control=sources[0],controls[0]
    sh=hashlib.sha256(source.read_bytes()).hexdigest()
    refsha=hashlib.sha256(control.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    with SQLiteEventStore(control) as db:
        old=db.load(WORLD)
        assert old.time==244*HOUR and len(old.npcs)==13
        assert audit_npc_economy(old)["copper_known_total"]==12
        baseline=facts(old,"P9_verified_control")
    copied=OUT/"P10_signed_market_employment.sqlite"
    shutil.copyfile(source,copied)
    assert hashlib.sha256(copied.read_bytes()).hexdigest()==sh
    reports={}
    with SQLiteEventStore(copied) as db:
        clock=TimeEngine(db);clock.open_session(WORLD)
        try:
            s=db.load(WORLD)
            assert s.time==236*HOUR and len(s.npcs)==13
            assert "food_payroll" not in s.supply_circuits["huda"]
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            for flag in (
                "merchant_food_wage_enabled","community_food_enabled",
                "cashless_relief_walk_enabled","desperate_paid_harvest_enabled",
                "deferred_bakery_grain_wage_enabled","integrated_livelihoods_enabled",
                "remember_unbought_stalls_enabled","reserve_signed_relief_offer_enabled",
                "desperate_funded_planting_enabled","hungry_paid_baker_return_enabled",
                "signed_steward_wage_quote_rescue_enabled",
                "voluntary_well_food_visit_enabled","hunter_well_food_visit_enabled",
                "local_market_freight_employment_enabled",
            ):
                setattr(sim,flag,True)
            for hour in HOURS:
                s=sim.advance(WORLD,seconds=hour*HOUR-s.time,
                    command_id=f"p10-signed-market-{hour}",expected_revision=s.revision).state
                conserve_diverse(s)
                money=audit_npc_economy(s)
                assert money["copper_scope_complete"] and money["copper_known_total"]==12
                assert len(s.npcs)==13
                db.snapshot(WORLD)
                assert db.load(WORLD).to_dict()==s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0]=="ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                reports[str(hour)]=facts(s,"P10_candidate")
                print("P10_AUTHENTIC_REAL236 "+json.dumps(reports[str(hour)],sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    result=reports["244"]
    comparison={
        "source_h236_sha256":sh,"control_h244_sha256":refsha,
        "control":baseline,"candidate":result,
        "huda_meal_delta":result["huda"]["meals"]-baseline["huda"]["meals"],
        "huda_hunger_delta":result["huda"]["hunger"]-baseline["huda"]["hunger"],
        "huda_deliveries_delta":result["huda_deliveries"]-baseline["huda_deliveries"],
        "hungry100_delta":result["starving100"]-baseline["starving100"],
        "same_13_npcs":True,"conserved_copper":12,
        "release_gate":"PLAY48_NO_GO",
    }
    print("P10_VS_P9_AUTHENTIC_H244 "+json.dumps(comparison,sort_keys=True),flush=True)
    (OUT/"comparison.json").write_text(json.dumps(comparison,indent=2,sort_keys=True),encoding="utf8")
    (OUT/"candidate.json").write_text(json.dumps(reports,indent=2,sort_keys=True),encoding="utf8")
    assert hashlib.sha256(source.read_bytes()).hexdigest()==sh
    assert hashlib.sha256(control.read_bytes()).hexdigest()==refsha
    # Do not call it success unless the canonical event ledger shows an ACTUAL
    # new agreement, a completed delivery receipt, a PAID real portion and meal.
    assert result["huda_has_new_signed_contract"],"No authentic on-site employment agreement"
    assert result["huda_paid_food_wages"]>=1,"No authentic actual cargo-funded food wage"
    assert result["huda"]["meals"]>baseline["huda"]["meals"],"New wage did not yield an eaten meal"
    assert result["huda"]["hunger"]<baseline["huda"]["hunger"],"Huda not better fed than control"


if __name__=="__main__":
    main()
