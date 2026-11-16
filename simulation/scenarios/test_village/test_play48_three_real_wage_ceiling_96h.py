"""PLAY48 alternative bounded income: 3 real signed wages instead of 2.

No new source resources, no new event type and no change to the engine:
same original 13NPC + 12 coins, genuine moving cargo, true owned food.
Both Hana market and Huda bakery employment signed at t0 with MAX_UNIT=3.
A third wage exists only if the original employer *owns unpromised bread*
AFTER a separately authenticated physical courier delivery.
"""
from __future__ import annotations
import json
from collections import Counter

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play48_real_watch_income_24h import seed as original_seed
from test_play48_real_watch_income_24h import engine as original_engine, HOUR
from test_play38_multi_farm_couriers import WORLD
from test_play48_finite_hunt_fish_roads import conserve_diverse

HOURS=(24,36,48,60,72,84,96)

def true_signed_three(path):
    old=original_seed(path)
    assert old.resources["bakery"]["food"]==1
    with SQLiteEventStore(path) as db:
        state=db.append(WORLD,"signed-contingent-market-employment",
            old.revision,[DomainEvent("CourierProvisionConfigured",None,
                "bounded real future FOOD deliveries fund at most three wages",0,
                {"id":"real-surplus-only-hana","courier_id":"hana",
                 "payer_site":"market","units":0,
                 "authorized_total_units":3})],bootstrap=True)
        state=db.append(WORLD,"sign-genuine-huda-deferred-True",
            state.revision,[DomainEvent("CourierProvisionConfigured",None,
                "bounded real grain deliveries may fund three later loaves",0,
                {"id":"huda-future-bakery","courier_id":"huda",
                 "payer_site":"bakery","units":0,
                 "authorized_total_units":3,"deferred_bakery_grain":True})],
            bootstrap=True)
        assert db.verify(WORLD).to_dict()==state.to_dict()
    assert (state.schema_version,state.rules_version)==(45,69)
    assert len(state.npcs)==13
    assert state.resources["bakery"]["food"]==1
    assert audit_npc_economy(state)["copper_known_total"]==12
    assert sum(x["remaining"] for x in state.courier_provisions.values())==0
    conserve_diverse(state)
    return state


def test_96h_original_physical_3wage_employer_financed_endurance(tmp_path):
    path=tmp_path/"original-three-signed-wages.sqlite"
    true_signed_three(path)
    records={}
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=original_engine(db,clock,reserve_trader_meal=True,
                                deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.deferred_bakery_grain_wage_enabled=True
            state=db.verify(WORLD)
            for hour in HOURS:
                state=sim.advance(WORLD,seconds=hour*HOUR-state.time,
                    command_id=f"three-signed-real-food-wages:{hour}",
                    expected_revision=state.revision).state
                conserve_diverse(state)
                assert db.verify(WORLD).to_dict()==state.to_dict()
                audit=audit_npc_economy(state)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"]==12
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                worker_payroll={
                    who:{
                        "market_paid":sum(len(c["payments"]) for c
                            in state.courier_provisions.values()
                            if c["courier_id"]==who),
                        "bakery_paid":sum(
                            row["paid_at"] is not None
                            for c in state.courier_provisions.values()
                            if c["courier_id"]==who
                            for row in c.get("deferred_grain_services",())),
                        "food":state.resources[who]["food"],
                        "hunger":state.npcs[who]["needs"]["hunger"],
                        "deliveries":state.supply_circuits[who]["deliveries"],
                        "meals":sum(x["npc_id"]==who
                            for x in state.consumptions.values()),
                    } for who in ("hana","huda")
                }
                row={
                    "hour":hour,
                    "hunger100":sum(n["needs"]["hunger"]==100
                        for n in state.npcs.values()),
                    "starving":sorted(who for who,n in state.npcs.items()
                        if n["needs"]["hunger"]==100),
                    "meals":len(state.consumptions),
                    "bread_jobs":sum(j["status"]=="completed" and
                        j["site_id"]=="bakery"
                        for j in state.production_jobs.values()),
                    "market_food_sales":sum(t["resource"]=="food"
                        for t in state.market_trades.values()),
                    "market_food_owned":state.resources["market"]["food"],
                    "east_grain_owned":state.resources["farm_east"]["grain"],
                    "worker_payroll":worker_payroll,
                    "conserved_copper":12,
                    "strict_sqlite_replay":True,
                    "economic_release_approved":False,
                }
                records[hour]=row
                print("PLAY48_3WAGE_FINITE_EARNED_PAY_96H "+
                      json.dumps(row,sort_keys=True),flush=True)
                if hour in (24,48,72):
                    state=FiniteWaterService(db,clock).record(
                        WORLD,"well",
                        f"fixed-external-rain-day{hour//24}",2,
                        command_id=f"real-attributed-source-day{hour//24}",
                        expected_revision=state.revision).state
            assert db.snapshot(WORLD).to_dict()==state.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict()==state.to_dict()
    assert records[36]["worker_payroll"]["huda"]["meals"]>=1
    assert records[48]["hunger100"]==0
    # Historic two-wage candidate produced only 17 food jobs and 8 hunger100
    # at h96. A change to wage capacity alone must demonstrate REAL recovery,
    # not merely extra claims or repeat source bootstrap.
    assert records[96]["bread_jobs"]>17, (
        "signed third wage did not recover any actual day4 bread production")
    assert records[96]["hunger100"]<8, (
        "signed third wage did not improve day4 village famine")
    assert records[96]["meals"]>records[72]["meals"]
