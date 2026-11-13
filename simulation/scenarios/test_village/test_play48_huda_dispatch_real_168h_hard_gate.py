"""PLAY48 HARD post-freight-fix 96/168h RELEASE_NO_GO gate.

This is the exact existing 13-NPC genuine economic engine + narrowly fixed
physically *already loaded* Huda WELL->FARM water departure. No new food,
money, water or NPC is injected during gameplay. Two water units at each
predeclared day1..day6 rain boundary are EXOGENOUS source measurements,
exactly as in the previous PR100 comparator, never adaptive relief.
A green technical test is not release acceptance: lack of actual post72
production, deliveries, meals, sales, wage or no-starvation must FAIL.
"""
from __future__ import annotations
import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_peddler_24h_diagnostic import measures
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKPOINTS=(6,12,24,30,36,48,72,96,120,144,168)
DAY=24*HOUR
RAIN_DAYS=(1,2,3,4,5,6)


def _real_receipts(s):
    m=measures(s)
    m["workers"]={
        who:{"hunger":s.npcs[who]["needs"]["hunger"],
             "food":s.resources[who].get("food",0),
             "meals":sum(x["npc_id"]==who for x in s.consumptions.values()),
             "where":s.entities[who]["location_id"],
             "freight":s.supply_circuits[who]["deliveries"],
             "food_wages":sum(len(c["payments"])
                        for c in s.courier_provisions.values()
                        if c["courier_id"]==who)}
        for who in ("hana","huda")
    }
    m["farm_cycles"]={
        who:{"planted":s.farm_plots[who]["started"],
             "matured":s.farm_plots[who]["matured"],
             "owned_seed":s.resources[who]["seed"],
             "water":s.resources[who]["water"],
             "grain":s.resources[who]["grain"]}
        for who in ("farm","farm_east")
    }
    m["actual_hungry100"]=[
        who for who,npc in sorted(s.npcs.items())
        if npc["needs"]["hunger"]==100
    ]
    m["rain_physical_units"]=s.hydrology_sources["well"]["received_total"]
    m["late_completed_jobs"]=sum(
        j["status"]=="completed" and j.get("completed_at",0)>72*HOUR
        for j in s.production_jobs.values()
    )
    m["late_sales"]=sum(t["executed_at"]>72*HOUR
                         for t in s.market_trades.values()
                         if t["resource"]=="food")
    m["late_meals"]=sum(c["consumed_at"]>72*HOUR
                       for c in s.consumptions.values())
    m["late_paid_courier_work"]=sum(
        p["paid_at"]>72*HOUR for v in s.courier_provisions.values()
        for p in v["payments"]
    )
    return m


def test_no_spurious_recovery_without_genuine_post72_freight_and_food(tmp_path):
    path=tmp_path/"real-13npc-postloaded-water-168h.sqlite"
    first=signed_genesis(path)
    assert len(first.npcs)==13
    assert audit_npc_economy(first)["copper_known_total"]==12
    measured=[]
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner=engine(db,clock,reserve_trader_meal=True,
                          deferred_market_courier_wage=True)
            hydrology=FiniteWaterService(db,clock)
            for hour in CHECKPOINTS:
                before=db.verify(WORLD)
                state=runner.advance(
                    WORLD,seconds=hour*HOUR-before.time,
                    expected_revision=before.revision,
                    command_id=f"preloaded-water-hard-gate:{hour}"
                ).state
                assert state.time==hour*HOUR
                assert len(state.npcs)==13
                conserve_diverse(state)
                conserved=audit_npc_economy(state)
                assert conserved["copper_scope_complete"]
                assert conserved["copper_known_total"]==12
                assert db.verify(WORLD).to_dict()==state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                row=_real_receipts(state)
                measured.append(row)
                print("PLAY48_ACTUAL_HUDA_DISPATCH_HARD_168H "+
                      json.dumps(row,sort_keys=True),flush=True)
                if hour%24==0 and hour//24 in RAIN_DAYS:
                    day=hour//24
                    now=hydrology.record(
                        WORLD,"well",f"precommitted-real-rain-{day}",2,
                        command_id=f"precommitted-water-event-{day}",
                        expected_revision=state.revision
                    ).state
                    conserve_diverse(now)
                    assert db.verify(WORLD).to_dict()==now.to_dict()
            end=db.verify(WORLD)
            assert end.time==168*HOUR
            assert end.hydrology_sources["well"]["received_total"]==12
            ref72=next(r for r in measured if r["hour"]==72)
            last=measured[-1]
            print("PLAY48_POST_FIX_96_168_RELEASE_GATE "+
                  json.dumps({
                      "h72":ref72,"h96":next(r for r in measured if r["hour"]==96),
                      "h168":last,
                      "water_delivery_post72":all(
                          last["workers"][who]["freight"] >
                          ref72["workers"][who]["freight"]
                          for who in ("huda","hana")
                      ),
                  },sort_keys=True),flush=True)
            assert all(r["hunger100"]==0
                       for r in measured if r["hour"]>=96), (
                "RELEASE_NO_GO: original NPCs at hunger100 during days 4..7")
            assert last["late_completed_jobs"]>0, (
                "RELEASE_NO_GO: actual completed production stopped after 72h")
            assert last["late_sales"]>0, (
                "RELEASE_NO_GO: actual market food sales stopped after 72h")
            assert last["late_meals"]>0, (
                "RELEASE_NO_GO: all actual eating stopped after 72h")
            assert last["late_paid_courier_work"]>0, (
                "RELEASE_NO_GO: no real paid courier work after 72h")
            for who in ("huda","hana"):
                assert (last["workers"][who]["freight"]>
                        ref72["workers"][who]["freight"]), (
                    f"RELEASE_NO_GO: {who} did not deliver any real post72 cargo")
        finally:
            clock.close_session(WORLD)
