"""PLAY48 root fix probe: farm seed is physically recovered from actual grain.

Zero free seed, rain, food, copper, new labor, roads or extra initial harvest.
Two trusted time-zero recipes allow a farmer to spend 1 locally held edible
grain as a durable seed. Existing crop planting still needs an actual seed,
actual physically delivered water and time, and processing takes 240 seconds.

Run the original REAL 13NPC two-field scenario to 72h with fixed external
observed rainfall at days 1 and 2. This is a wet-season counterfactual, NOT
an autonomous-weather implementation or a 96h/168h release success.
"""
from __future__ import annotations
import json

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_peddler_24h_diagnostic import measures

FARMS=("farm","farm_east")
WILD=("hunting_woods","riverbank")
RECIPES={"farm":"save-main-harvest-seed","farm_east":"save-east-harvest-seed"}


def seed_physical_harvest_recovery(path):
    start=signed_genesis(path)
    with SQLiteEventStore(path) as db:
        s=db.verify(WORLD)
        events=[
            DomainEvent("ProductionRecipeConfigured",None,
                        "authorized finite seed saving from 1 genuine grain",0,{
                "id": RECIPES[site],"site_id":site,"role":"farmer",
                "input_resource":"grain","input_amount":1,
                "output_resource":"seed","output_amount":1,
                "tool_resource":"hoe","duration_seconds":240,
            }) for site in FARMS
        ]
        for site in FARMS:
            assert start.resources[site]["seed"] == 1
            assert start.resources[site]["grain"] == 0
            assert start.resources[site]["hoe"] == 1
        saved=db.append(WORLD,"trusted-finite-grain-to-seed-terms",s.revision,
                        events,bootstrap=True)
        assert len(saved.npcs)==13
        assert audit_npc_economy(saved)["copper_known_total"]==12
        assert saved.resources["market"]["food"]==2
        assert saved.resources["bakery"]["food"]==1
        assert db.verify(WORLD).to_dict()==saved.to_dict()
        return saved


def _physical_ledger(state):
    """Food-balance extension: salvaging 1 grain into 1 seed costs 1 loaf.

    The ledger counts the diverted grain ONCE when recovery starts, not as
    new food. The future real harvest is backed by that seed and rain/time.
    """
    stocks=state.resources
    eaten=sum(x["quantity"] for x in state.consumptions.values())
    escrow=sum(c["remaining"] for c in state.courier_provisions.values())
    food=sum(r.get("food",0) for r in stocks.values())+escrow
    grain=sum(r.get("grain",0) for r in stocks.values())
    yields={}
    for site in FARMS:
        y=[r["output_amount"] for r in state.production_recipes.values()
           if r["site_id"]==site and
           r.get("input_resource")=="crop_ready"
           and r["output_resource"]=="grain"]
        assert len(y)==1
        yields[site]=y[0]
    awaiting_bread=sum(
        state.production_recipes[j["recipe_id"]]["input_amount"]
        for j in state.production_jobs.values()
        if j["status"]=="running"
        and state.production_recipes[j["recipe_id"]].get("input_resource")=="grain"
        and state.production_recipes[j["recipe_id"]]["output_resource"]=="food"
    )
    awaiting_harvest=sum(
        yields[j["site_id"]] for j in state.production_jobs.values()
        if j["status"]=="running"
        and state.production_recipes[j["recipe_id"]].get("input_resource")=="crop_ready"
    )
    ripe=sum(stocks[site]["crop_ready"]*yields[site] for site in FARMS)
    grown=sum(state.farm_plots[site]["matured"]*yields[site] for site in FARMS)
    completed_prey=sum(
        j["status"]=="completed" and j["recipe_id"] in
        ("two-portions-hunter","two-portions-fisher")
        for j in state.production_jobs.values()
    )
    grain_spent_for_seed=sum(
        j["recipe_id"] in RECIPES.values()
        for j in state.production_jobs.values()
    )
    assert food+grain+eaten+awaiting_bread+awaiting_harvest+ripe+grain_spent_for_seed==(
        3+grown+2*completed_prey
    ), "Food ledger: saved seed must cost actual local edible grain"
    for site in WILD:
        used=sum(
            j["site_id"]==site and
            j["recipe_id"] in ("two-portions-hunter","two-portions-fisher")
            for j in state.production_jobs.values()
        )
        assert stocks[site]["wild_food"]+stocks[site]["regrowth_reserve"]+used==8
    water=sum(
        stocks[k]["water"] for k in ("well","farm","farm_east","huda","hana")
        if "water" in stocks.get(k,{})
    )
    consumed_crop_water=sum(p["started"] for p in state.farm_plots.values())
    assert water+consumed_crop_water==(
        2+state.hydrology_sources["well"]["received_total"]
    ), "Well water + installed crops exactly equals initially owned plus measured rain"
    cash=audit_npc_economy(state)
    assert cash["copper_scope_complete"] and cash["copper_known_total"]==12


def test_seed_salvage_72h_is_consumed_grain_not_new_material(tmp_path):
    path=tmp_path/"actual-farm-physical-seed-savings.sqlite"
    first=seed_physical_harvest_recovery(path)
    _physical_ledger(first)
    reports=[]
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            climate=FiniteWaterService(db,clock)
            for hour in (6,12,24,30,36,48,54,60,72):
                old=db.verify(WORLD)
                now=sim.advance(
                    WORLD,seconds=hour*HOUR-old.time,
                    command_id=f"actual-seed-72h:{hour}",
                    expected_revision=old.revision).state
                assert now.time==hour*HOUR
                _physical_ledger(now)
                assert db.verify(WORLD).to_dict()==now.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                r=measures(now)
                r["farm_progress"]={
                    site:{
                        "seed":now.resources[site]["seed"],
                        "grain":now.resources[site]["grain"],
                        "crop_status":now.farm_plots[site]["status"],
                        "crops_started":now.farm_plots[site]["started"],
                        "harvests_matured":now.farm_plots[site]["matured"],
                        "seed_saving_jobs":sum(
                            j["recipe_id"]==RECIPES[site]
                            for j in now.production_jobs.values()),
                        "completed_seed_savings":sum(
                            j["recipe_id"]==RECIPES[site] and j["status"]=="completed"
                            for j in now.production_jobs.values()),
                    } for site in FARMS
                }
                r["hunger_hana"]=now.npcs["hana"]["needs"]["hunger"]
                r["hunger_huda"]=now.npcs["huda"]["needs"]["hunger"]
                r["actual_water_attested"]=now.hydrology_sources["well"]["received_total"]
                reports.append(r)
                print("PLAY48_REAL_SECOND_HARVEST_72H_PHYSICAL_REPORT "+
                      json.dumps(r,sort_keys=True),flush=True)
                if hour in (24,48):
                    after=climate.record(
                        WORLD,"well",f"predeclared-wet-day-{hour//24}",2,
                        command_id=f"physical-rain-day-{hour//24}",
                        expected_revision=now.revision).state
                    _physical_ledger(after)
                    assert db.verify(WORLD).to_dict()==after.to_dict()
            final=db.verify(WORLD)
            assert final.hydrology_sources["well"]["received_total"]==4
            assert sum(
                j["recipe_id"] in RECIPES.values() and j["status"]=="completed"
                for j in final.production_jobs.values()
            )>=1, "NO_GO: neither farmer recovered a physical crop seed from grain"
            print("PLAY48_REAL_SEED_RECOVERY_72H_GATE "+
                  json.dumps({"second_crops_started":{
                      s:final.farm_plots[s]["started"] for s in FARMS
                  },"saved_seed_jobs":{
                      s:sum(j["recipe_id"]==RECIPES[s] and
                            j["status"]=="completed"
                            for j in final.production_jobs.values())
                      for s in FARMS
                  },"hunger100":reports[-1]["hunger100"],
                  "meals":reports[-1]["food_eaten_meals"],
                  "new_production_post48":reports[-1]["production_jobs_completed"]-
                                            next(v for v in reports if v["hour"]==48)["production_jobs_completed"],
                  },sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
