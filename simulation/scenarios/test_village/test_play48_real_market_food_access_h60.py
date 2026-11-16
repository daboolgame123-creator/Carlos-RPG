"""PLAY48 physical food access diagnosis: who actually owns available bread?

Unmodified original 13-NPC Rules68 village, original exactly 12 coins,
true market/wilderness ownership, same signed courier jobs, same rain.
No fabricated buyers, goods, taxation, charity, locations or selling.
Print what stops each hungry resident buying/eating the existing market stock.
"""
from __future__ import annotations
import json
from collections import Counter

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from carlos_sim.economic_autonomy import choose_local_food_purchase
from carlos_sim.courier_provisions import _market_uncommitted_bread_after_sales
from carlos_sim.food_for_work import _available_site_food
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.market import _present, reserved_trade_units
from test_play48_deferred_bakery_grain_wages_ab import seed
from test_play48_real_watch_income_24h import engine as original_engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play38_multi_farm_couriers import WORLD

HOURS=(24,30,36,42,48,54,60)


def market_access(state):
    market=state.resources["market"]
    quotes=[{
        "id":key, "remaining":offer["remaining"],
        "status":offer["status"],
        "resource":offer["resource"],
        "unit_price":offer["unit_price"],
        "stock_owner":offer["stock_owner_id"],
        "seller":offer["seller_id"],
        "seller_physically_present":_present(
            state.to_dict(),offer["seller_id"],offer["site_id"]),
    } for key,offer in sorted(state.market_offers.items())
      if offer["site_id"]=="market" and offer["status"]=="open"]
    access={}
    for who,n in sorted(state.npcs.items()):
        own=state.resources[who]
        place=state.entities[who]["location_id"]
        running=any(x["npc_id"]==who and x["status"]=="running"
                    for x in state.actions.values())
        working=any(x["npc_id"]==who and x["status"]=="running"
                    for x in state.production_jobs.values())
        traveling=any(x["npc_id"]==who and x["status"]=="traveling"
                      for x in state.travels.values())
        eligible=choose_local_food_purchase(state,who)
        access[who]={
            "role":n["role"],"site":place,
            "hunger":n["needs"]["hunger"],
            "owned_copper":own.get("coin_copper"),
            "owned_food":own.get("food"),
            "market_co_present":place=="market" and not traveling,
            "running_action":running,"working":working,
            "traveling":traveling,
            "physical_purchase_offer":eligible.offer_id if eligible else None,
            "ever_ate":sum(x["npc_id"]==who for x in state.consumptions.values()),
        }
    agg=audit_npc_economy(state)
    return {
        "hour":state.time//HOUR,
        "market_owned_food":market["food"],
        "market_owned_copper":market["coin_copper"],
        "market_uncommitted_food":_market_uncommitted_bread_after_sales(state),
        "market_unpromised_food":_available_site_food(state,"market"),
        "market_outstanding_quotes":quotes,
        "market_reserved_food":reserved_trade_units(
            state.supply_circuits,"market","food"),
        "food_sites":{
            site:{"food":bag["food"],"copper":bag.get("coin_copper")}
            for site,bag in sorted(state.resources.items())
            if site in ("market","bakery","riverbank","hunting_woods")
        },
        "NPC_access":access,
        "market_stall_keeper":state.market_stalls.get("market",{}).get("keeper_id"),
        "food_sales":sum(t["resource"]=="food" for t in state.market_trades.values()),
        "all_meals":len(state.consumptions),
        "starved100":[who for who,n in sorted(state.npcs.items())
                      if n["needs"]["hunger"]==100],
        "bakery_jobs":sum(j["status"]=="completed" and j["site_id"]=="bakery"
                          for j in state.production_jobs.values()),
        "real_courier_deliveries":{
            who:state.supply_circuits[who]["deliveries"]
            for who in ("hana","huda")},
        "copper_total":agg["copper_known_total"],
        "copper_by_owner":agg["copper_known_by_owner"],
        "production_wages":audit_production_wages(state),
    }


def test_original_market_food_surplus_unavailable_to_starving_npcs(tmp_path):
    path=tmp_path/"market-physical-access-60h.sqlite"
    seed(path,deferred=True)
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=original_engine(
                db,clock,reserve_trader_meal=True,
                deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.deferred_bakery_grain_wage_enabled=True
            s=db.verify(WORLD)
            for hour in HOURS:
                s=sim.advance(WORLD,seconds=hour*HOUR-s.time,
                    command_id=f"unmodified-food-access-diagnosis:{hour}",
                    expected_revision=s.revision).state
                conserve_diverse(s)
                assert db.verify(WORLD).to_dict()==s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                row=market_access(s)
                assert row["copper_total"]==12
                print("PLAY48_ACTUAL_MARKET_FOOD_ACCESS "+
                      json.dumps(row,sort_keys=True),flush=True)
                if hour in (24,48):
                    s=FiniteWaterService(db,clock).record(
                        WORLD,"well",f"fixed-external-rain-day{hour//24}",2,
                        command_id=f"real-attributed-source-day{hour//24}",
                        expected_revision=s.revision).state
            assert db.snapshot(WORLD).to_dict()==s.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict()==s.to_dict()
