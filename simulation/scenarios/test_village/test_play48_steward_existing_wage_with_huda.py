"""PLAY48 existing real merchant's salary alongside genuine courier salaries.

Original 13 NPC & 12 copper, zero opening food debit; shopkeeper gets only
real market-owned loaf after 2 authentic settled food sales and protects
quotes, customer parcels and one employer operating loaf. No new engine.
"""
from __future__ import annotations
import json
from carlos_sim import SQLiteEventStore, TimeEngine, DomainEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play48_deferred_bakery_grain_wages_ab import seed
from test_play48_real_watch_income_24h import engine as original_engine, HOUR
from test_play38_multi_farm_couriers import WORLD
from test_play48_finite_hunt_fish_roads import conserve_diverse

HOURS=(24,30,36,42,48,54,60)

def initial(path):
    world=seed(path,deferred=True)
    assert world.resources["bakery"]["food"]==1
    assert world.resources["market"]["food"]==2
    with SQLiteEventStore(path) as db:
        world=db.append(WORLD,"sign-authentic-market-food-payroll",
            world.revision,[DomainEvent(
                "MarketStewardFoodContractSigned",None,
                "market steward earns one actual surplus loaf after two real sales",0,
                {"site_id":"market","keeper_id":"salma",
                 "sales_per_wage":2})],bootstrap=True)
        assert db.verify(WORLD).to_dict()==world.to_dict()
    assert world.resources["market"]["food"]==2
    assert (world.schema_version,world.rules_version)==(45,68)
    assert audit_npc_economy(world)["copper_known_total"]==12
    conserve_diverse(world)
    return world


def test_original_market_merchant_salary_genuinely_paid_by_actual_sales(tmp_path):
    path=tmp_path/"real-market-salma-wage.sqlite"
    initial(path)
    found={}
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=original_engine(db,clock,reserve_trader_meal=True,
                                deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.deferred_bakery_grain_wage_enabled=True
            world=db.verify(WORLD)
            for hour in HOURS:
                world=sim.advance(WORLD,seconds=hour*HOUR-world.time,
                    command_id=f"salma-earned-market-service:{hour}",
                    expected_revision=world.revision).state
                conserve_diverse(world)
                assert db.verify(WORLD).to_dict()==world.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                audit=audit_npc_economy(world)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"]==12
                wages=[
                    (tid,t["steward_food_wage"]) for tid,t
                    in world.market_trades.items()
                    if "steward_food_wage" in t
                ]
                stats={
                    "hour":hour,
                    "real_salma_food_wages":len(wages),
                    "real_salma_own_meals":sum(x["npc_id"]=="salma"
                                          for x in world.consumptions.values()),
                    "real_salma_personal_food":world.resources["salma"]["food"],
                    "salma_hunger":world.npcs["salma"]["needs"]["hunger"],
                    "market_stock_food":world.resources["market"]["food"],
                    "market_sales":sum(t["resource"]=="food"
                                       for t in world.market_trades.values()),
                    "all_meals":len(world.consumptions),
                    "hunger100":sum(n["needs"]["hunger"]==100
                                    for n in world.npcs.values()),
                    "all_hungry_ids":[who for who,n in sorted(world.npcs.items())
                                     if n["needs"]["hunger"]==100],
                    "baked_food_jobs":sum(j["status"]=="completed"
                        and j["site_id"]=="bakery"
                        for j in world.production_jobs.values()),
                    "couriers":{
                        who:{
                            "deliveries":world.supply_circuits[who]["deliveries"],
                            "own_meals":sum(c["npc_id"]==who
                                for c in world.consumptions.values()),
                            "hunger":world.npcs[who]["needs"]["hunger"]
                        } for who in ("hana","huda")
                    },
                    "original_money_total":audit["copper_known_total"],
                }
                found[hour]=stats
                print("PLAY48_REAL_SALMA_MARKET_SERVICE_WAGE_H60 "+
                    json.dumps(stats,sort_keys=True),flush=True)
                if hour in (24,48):
                    world=FiniteWaterService(db,clock).record(
                        WORLD,"well",f"fixed-external-rain-day{hour//24}",2,
                        command_id=f"real-attributed-source-day{hour//24}",
                        expected_revision=world.revision).state
            assert db.snapshot(WORLD).to_dict()==world.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict()==world.to_dict()
    # Hard approval gate: a merchant's real wage must improve her access to
    # bread and reduce the number starving, WITHOUT taking a buyer's sale or
    # a real courier delivery. Baseline facts from original exact source
    # Rules68 h60: sale8, bread17, meals22, hunger1005, Hana44,Huda8.
    assert found[60]["real_salma_food_wages"]>=1, (
        "no completed source-owned food sale ever funded steward payroll")
    assert found[60]["real_salma_own_meals"]>=1, (
        "merchant's actual job wage failed to turn into a real meal")
    assert found[60]["market_sales"]>=8
    assert found[60]["baked_food_jobs"]>=17
    assert found[60]["all_meals"]>=22
    assert found[60]["couriers"]["hana"]["deliveries"]>=44
    assert found[60]["couriers"]["huda"]["deliveries"]>=8
    assert found[60]["hunger100"]<5, (
        "salary alone did not improve the verified day3 village famine")
