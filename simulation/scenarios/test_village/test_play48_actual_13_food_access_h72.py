"""PLAY48 read-only 13-resident subsistence blocker at h48/h72.

Causal audit of the same exact PR103 source, autonomous 13 NPCs and 12
existing copper. Scarcity is not measured only as site food: each resident
must physically reach a real quoted food seller, have sufficient OWN copper,
or earn personal food through completed work.

This is a diagnosis, not a new gameplay feature or a release success.
No simulated intervention, manual location change, gifts or new jobs.
"""
from __future__ import annotations
import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.economic_autonomy import choose_local_food_purchase
from carlos_sim.market import _present
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKS=(24,30,36,48,72)
RAIN_DAYS=(24,48)


def inspect(state):
    quotes=state.market_offers
    actual=state.to_dict()
    people=[]
    for who,npc in sorted(state.npcs.items()):
        here=state.entities[who]["location_id"]
        owned=state.resources[who]
        food=owned.get("food")
        cash=owned.get("coin_copper")
        local_quotes=[
            {"site":o["site_id"],"seller":o["seller_id"],
             "unit_price":o["unit_price"],"remaining":o["remaining"],
             "physically_available_seller":_present(actual,o["seller_id"],here)}
            for o in quotes.values()
            if o["status"]=="open" and o["site_id"]==here
            and o["resource"]=="food" and o["remaining"]>0
        ]
        intent=choose_local_food_purchase(state,who)
        actual_meals=sum(r["npc_id"]==who for r in state.consumptions.values())
        actual_jobs=sum(j["npc_id"]==who and j["status"]=="completed"
                        for j in state.production_jobs.values())
        people.append({
            "id":who,"role":npc["role"],"at":here,
            "hunger":npc["needs"]["hunger"],"fatigue":npc["needs"]["fatigue"],
            "owned_food":food,"owned_copper":cash,
            "actual_meals":actual_meals,"completed_real_jobs":actual_jobs,
            "real_local_food_offers":local_quotes,
            "eligible_buyer_now":intent is not None,
            "local_market_present":here in state.market_stalls,
            "shop_food_owned_on_site":state.resources.get(here,{}).get("food",0),
            "reason_if_no_personal_meal":(
                "already_holds_food" if (food or 0)>0 else
                "no_personal_cash" if cash == 0 else
                "no_local_quoted_food" if not local_quotes else
                "insufficient_cash_or_unavailable_seller_or_work_gate"
            ),
        })
    r={
        "hour":state.time//HOUR,
        "original_people":len(state.npcs),
        "known_copper":audit_npc_economy(state)["copper_known_total"],
        "site_food":{
            k:r.get("food",0)
            for k,r in sorted(state.resources.items())
            if k in ("market","bakery","farm","farm_east","hunting_woods","riverbank")
        },
        "open_food_offers":[
            {"site":v["site_id"],"price":v["unit_price"],
             "remaining":v["remaining"],"seller":v["seller_id"]}
            for v in quotes.values()
            if v["status"]=="open" and v["resource"]=="food" and v["remaining"]>0
        ],
        "real_food_trades":sum(
            t["resource"]=="food" for t in state.market_trades.values()),
        "completed_jobs":sum(j["status"]=="completed"
                             for j in state.production_jobs.values()),
        "actual_consumed_meals":len(state.consumptions),
        "people":people,
    }
    return r


def test_actual_13_person_physical_cash_food_access_isolated(tmp_path):
    path=tmp_path/"not-a-grant-13-real-residents.sqlite"
    original=signed_genesis(path)
    assert len(original.npcs)==13
    assert audit_npc_economy(original)["copper_known_total"]==12
    rows=[]
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            rainfall=FiniteWaterService(db,clock)
            for hour in CHECKS:
                prev=db.verify(WORLD)
                new=sim.advance(
                    WORLD,seconds=hour*HOUR-prev.time,
                    command_id=f"actual-food-access-audit:{hour}",
                    expected_revision=prev.revision).state
                assert len(new.npcs)==13 and new.time==hour*HOUR
                conserve_diverse(new)
                aud=audit_npc_economy(new)
                assert aud["copper_scope_complete"] and aud["copper_known_total"]==12
                assert db.verify(WORLD).to_dict()==new.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                row=inspect(new)
                rows.append(row)
                print("PLAY48_ORIGINAL_ALL_THIRTEEN_PHYSICAL_FOOD_ACCESS "+
                      json.dumps(row,sort_keys=True),flush=True)
                if hour in RAIN_DAYS:
                    after=rainfall.record(
                        WORLD,"well",f"fixed-external-rain-day{hour//24}",2,
                        command_id=f"real-attributed-source-day{hour//24}",
                        expected_revision=new.revision).state
                    conserve_diverse(after)
                    assert db.verify(WORLD).to_dict()==after.to_dict()
            at72=rows[-1]
            hungry=[p for p in at72["people"] if p["hunger"]==100]
            assert len(hungry)>=1, (
                "Expected current PLAY48 reproduction of original starvation")
            assert at72["site_food"]["market"]>=1, (
                "Expected genuine market inventory for access-vs-production diagnosis")
            assert sum(p["owned_copper"] for p in at72["people"] if isinstance(p["owned_copper"],int))<=12
            print("PLAY48_72H_FOOD_ACCESS_ROOT_SUMMARY "+
                json.dumps({
                    "starving":len(hungry),
                    "at_market_with_money":sum(p["at"]=="market" and
                        (p["owned_copper"] or 0)>=1 for p in hungry),
                    "starving_zero_personal_copper":sum(
                        p["owned_copper"]==0 for p in hungry),
                    "starving_not_at_market":sum(
                        p["at"]!="market" for p in hungry),
                    "starving_owned_food":sum((p["owned_food"] or 0)>0 for p in hungry),
                    "shop_market_food":at72["site_food"]["market"],
                    "open_quotes":at72["open_food_offers"],
                    "starving_ids":[p["id"] for p in hungry],
                },sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
