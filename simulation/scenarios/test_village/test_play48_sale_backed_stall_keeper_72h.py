"""PLAY48 root intervention: one real surplus sale funds the keeper's meal.

Same original 13 people, original 12 copper and 3 loaves, real production,
courier paths and original market. Only at a trusted t=0 market-stall signing
does its actual owner authorize an IN-KIND wage: 1 site-owned, unpromised
loaf for every SECOND *actual paid customer food sale*; no seller food stock
may accrue above one and no reserved customer quote or parcel may be taken.
The existing MarketTradeExecuted itself records the honest salary transfer.

This addresses Salma's h72 merchant starvation; it does NOT by itself
solve wage distribution to the other 7 penniless starving residents.
"""
from __future__ import annotations
import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.store import InvalidEvent
from test_play38_multi_farm_couriers import WORLD, seed_two_field_world
from test_play47_joined_professions import _joined_bootstrap
from test_play47_closure_endurance import DAY
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures

CHECKS = (6,12,24,30,36,48,72)


def _opted_stall_genesis(db,*,initial_market_food,**options):
    assert initial_market_food==3
    assert options=={
        "water":2,"seed":1,"harvest_yield":3,
        "personal_food":0,"market_wallets":True,
        "hungry_market_buyers":True,"one_hungry_market_buyer":False,
    }
    return _joined_bootstrap(
        db,initial_market_food=3,
        wilderness_food_jobs_enabled=True,
        wilderness_food_peddler_enabled=True,
        food_for_work_bakery_enabled=True,bakery_opening_food_wage=True,
        signed_market_watch_service_enabled=True,
        paid_market_keeper_from_real_sales_enabled=True,
    )


def trusted_initial(path):
    with SQLiteEventStore(path) as db:
        seed_two_field_world(
            db,east_growth_seconds=DAY,east_grain_yield=12,
            initial_water=2,initial_market_food=3,
            market_wallets=True,hungry_market_buyers=True,
            cash_return=True,waged_harvest=True,
            harvest_wage_copper=2,bootstrap=_opted_stall_genesis,
        )
        previous=db.load(WORLD)
        start=db.append(WORLD,"fixed-original-source-and-metabolism",previous.revision,[
            DomainEvent("WaterSourceConfigured",None,"same finite well",0,
                        {"site_id":"well","capacity":8}),
            DomainEvent("MetabolismPolicyConfigured",None,"same hunger 1h/pt",0,
                        {"hunger_seconds_per_point":3600,
                         "activity_hunger_percent":20}),
        ],bootstrap=True)
        assert start.market_stalls["market"]["keeper_id"]=="salma"
        assert start.market_stalls["market"]["keeper_food_wage_every"]==2
        assert len(start.npcs)==13
        assert start.resources["market"]["food"]==2
        assert start.resources["bakery"]["food"]==1
        assert start.resources["salma"]["food"]==0
        assert audit_npc_economy(start)["copper_known_total"]==12
        contract=db.append(WORLD,"same-original-Hana-courier-only-contingent-wage",
                           start.revision,[
            DomainEvent("CourierProvisionConfigured",None,"same market surplus job",0,
                        {"id":"real-surplus-only-hana","courier_id":"hana",
                         "payer_site":"market","units":0,
                         "authorized_total_units":2})
        ],bootstrap=True)
        assert db.verify(WORLD).to_dict()==contract.to_dict()
        conserve_diverse(contract)
        return contract


def snapshot(s):
    m=measures(s)
    m["salma"]={
        "hunger":s.npcs["salma"]["needs"]["hunger"],
        "food":s.resources["salma"]["food"],
        "meals":sum(x["npc_id"]=="salma" for x in s.consumptions.values()),
        "at":s.entities["salma"]["location_id"],
        "cash":s.resources["salma"]["coin_copper"],
    }
    m["site_owned_copper"]={
        k: v.get("coin_copper",0) for k,v in sorted(s.resources.items())
        if k in s.locations
    }
    m["real_sale_salary_receipts"]=[
        {"id":k,"food":t["keeper_food_wage"],
         "buyer":t["buyer_id"],"at":t["executed_at"]}
        for k,t in sorted(s.market_trades.items())
        if t.get("keeper_food_wage")
    ]
    m["buyer_count"]=sum(x["resource"]=="food" for x in s.market_trades.values())
    m["hana_wages"]=sum(
        len(c["payments"]) for c in s.courier_provisions.values()
        if c["courier_id"]=="hana"
    )
    m["huda_meals"]=sum(x["npc_id"]=="huda" for x in s.consumptions.values())
    return m


def run(path, *, wage_signed):
    start=trusted_initial(path) if wage_signed else signed_genesis(
        path,worker_ids=("hana",))
    assert len(start.npcs)==13
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner=engine(db,clock,reserve_trader_meal=True,
                          deferred_market_courier_wage=True)
            rain=FiniteWaterService(db,clock)
            checks=[]
            for hour in CHECKS:
                old=db.verify(WORLD)
                now=runner.advance(
                    WORLD,seconds=hour*HOUR-old.time,
                    expected_revision=old.revision,
                    command_id=f"actual-keeper-site-income:{wage_signed}:{hour}"
                ).state
                assert now.time==hour*HOUR and len(now.npcs)==13
                conserve_diverse(now)
                audit=audit_npc_economy(now)
                assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
                assert db.verify(WORLD).to_dict()==now.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                entry=snapshot(now)
                checks.append(entry)
                print("PLAY48_AUTHENTIC_SALE_FUNDED_KEEPER_72H "+
                      json.dumps({"treatment":wage_signed,"row":entry},
                                 sort_keys=True),flush=True)
                if hour in (24,48):
                    wet=rain.record(WORLD,"well",f"fixed-wet-day-{hour//24}",2,
                        command_id=f"same-separate-rain-{hour//24}",
                        expected_revision=now.revision).state
                    conserve_diverse(wet)
                    assert db.verify(WORLD).to_dict()==wet.to_dict()
            return start,checks
        finally:
            clock.close_session(WORLD)


def test_original_market_keeper_earned_real_sale_wage_not_pretend_food(tmp_path):
    a0,base=run(tmp_path/"no-seller-salary.sqlite",wage_signed=False)
    b0,treatment=run(tmp_path/"sale-backed-stall-salary.sqlite",
                     wage_signed=True)
    assert set(a0.npcs)==set(b0.npcs)
    assert sum(r.get("food",0) for r in a0.resources.values())==3
    assert sum(r.get("food",0) for r in b0.resources.values())==3
    assert a0.resources["market"]["food"]==b0.resources["market"]["food"]==2
    assert a0.resources["bakery"]["food"]==b0.resources["bakery"]["food"]==1
    assert audit_npc_economy(a0)["copper_known_total"]==12
    assert audit_npc_economy(b0)["copper_known_total"]==12
    control=base[-1]
    paid=treatment[-1]
    print("PLAY48_13NPC_SALE_BACKED_KEEPER_72H_AB "+
          json.dumps({"control":base,"paid":treatment},
                     sort_keys=True),flush=True)
    assert paid["real_sale_salary_receipts"], (
        "RELEASE_NO_GO: no authorized real customer trades funded any food wage"
    )
    assert paid["salma"]["meals"]>=1, (
        "RELEASE_NO_GO: site-paid real wage was not actually eaten by Salma"
    )
    assert paid["salma"]["hunger"]<100, (
        "RELEASE_NO_GO: site merchant still becomes incapacitated at h72"
    )
    assert paid["food_eaten_meals"]>=control["food_eaten_meals"], (
        "RELEASE_NO_GO: do not rescue seller by starving someone else"
    )
    assert paid["total_food_sales"]>=control["total_food_sales"], (
        "RELEASE_NO_GO: cannot choke real buyers by taking promised food"
    )
    assert paid["courier_deliveries"]["hana"]>=control["courier_deliveries"]["hana"], (
        "RELEASE_NO_GO: genuine courier goods must not decrease"
    )
    assert paid["hunger100"]<=control["hunger100"], (
        "RELEASE_NO_GO: genuine local seller income cannot worsen mass hunger"
    )


def test_unsigned_stalls_and_fake_salary_contract_rejected(tmp_path):
    source=trusted_initial(tmp_path/"no-late-rewritten-stall.sqlite")
    assert source.market_stalls["market"]["keeper_food_wage_every"]==2
    with SQLiteEventStore(tmp_path/"no-late-rewritten-stall.sqlite") as db:
        prev=db.verify(WORLD)
        with pytest.raises((ValueError,InvalidEvent)):
            db.append(WORLD,"forged-sale-keeper-salary",prev.revision,[
                DomainEvent("MarketStallConfigured",None,
                            "try to add wages to already signed stall",0,
                            {"site_id":"market","keeper_id":"salma",
                             "keeper_food_wage_every":2})
            ],bootstrap=True)
        assert db.verify(WORLD).to_dict()==prev.to_dict()
