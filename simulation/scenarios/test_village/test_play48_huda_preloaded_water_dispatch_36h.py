"""PLAY48 physical wet-source courier release; no material or wage mint.

Prior verified exact-source h24.5: Huda physically owns 1 water at well,
next departure h30, hunger80. By h30 hunger92, so old route decision
stranded the water and no further deliveries occurred. This tests a narrow
same-source, already-picked-up-cargo departure, still bound by genuine
physical route, real water, safe human hunger and injury guards.
"""
from __future__ import annotations
import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply import check_leg, choose_courier_leg
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKPOINTS=(6,12,18,24,24.5,25,26,27,28,30,36)


def test_real_13npc_physical_preloaded_water_delivered_before_huda_incapacitated(tmp_path):
    path=tmp_path/"preloaded-water-original-13npc.sqlite"
    initial=signed_genesis(path)
    assert len(initial.npcs)==13
    reports=[]
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            rain=FiniteWaterService(db,clock)
            for h in CHECKPOINTS:
                before=db.verify(WORLD)
                state=sim.advance(WORLD,seconds=int(h*HOUR)-before.time,
                    command_id="actual-preloaded-source-route:"+str(h),
                    expected_revision=before.revision).state
                assert len(state.npcs)==13 and state.time==int(h*HOUR)
                conserve_diverse(state)
                copper=audit_npc_economy(state)
                assert copper["copper_scope_complete"]
                assert copper["copper_known_total"]==12
                assert db.verify(WORLD).to_dict()==state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                huda=state.supply_circuits["huda"]
                hana=state.supply_circuits["hana"]
                row={"h":h,"huda_at":state.entities["huda"]["location_id"],
                     "huda_hunger":state.npcs["huda"]["needs"]["hunger"],
                     "huda_delivery":huda["deliveries"],
                     "huda_water":state.resources["huda"]["water"],
                     "huda_carry":None if huda["carry"] is None else dict(huda["carry"]),
                     "next_departure":huda["next_departure"],
                     "hana_delivery":hana["deliveries"],
                     "farm_water":state.resources["farm"]["water"],
                     "farm_crops_started":state.farm_plots["farm"]["started"],
                     "huda_meals":sum(m["npc_id"]=="huda"
                                      for m in state.consumptions.values()),
                     "huda_wages":sum(len(c["payments"]) for c in
                         state.courier_provisions.values() if c["courier_id"]=="huda")}
                reports.append(row)
                print("PLAY48_REAL_HUDA_LOADED_WATER_EARLY_DISPATCH "+
                      json.dumps(row,sort_keys=True),flush=True)
                if h==24:
                    observed=rain.record(WORLD,"well","fixed-wet-day1",2,
                        command_id="real-physical-two-units-at-day1",
                        expected_revision=state.revision).state
                    assert observed.hydrology_sources["well"]["received_total"]==2
                    conserve_diverse(observed)
                    assert db.verify(WORLD).to_dict()==observed.to_dict()
                if h==24.5 and state.entities["huda"]["location_id"]=="well" and huda["carry"] is not None:
                    route=choose_courier_leg(state,"huda")
                    assert route is not None, "preloaded real water must NOT remain trapped"
                    assert route[1:3]==("well","farm")
                    check_leg(state.to_dict(),"huda",route[0],route[1],route[2])
            byh={r["h"]:r for r in reports}
            assert byh[25]["huda_delivery"] > byh[24]["huda_delivery"], (
                "RELEASE_NO_GO: Huda still cannot physically deliver the loaded water")
            assert byh[25]["huda_hunger"] < 90, (
                "real delivery must occur before the established incapacity limit")
            assert byh[36]["huda_delivery"] >= byh[25]["huda_delivery"]
            print("PLAY48_PRELOADED_WATER_GATE "+
                  json.dumps({"h24":byh[24],"h25":byh[25],"h36":byh[36]},
                             sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
