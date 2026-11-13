"""READ-ONLY exact PLAY48 source audit for starving courier and dormant farms.

Do not change any producer decision or money, do not conjure food or seeds.
A declared single 2-unit rain observation at exactly h24 follows the prior
hard wet-season source. Trace Huda's physical circuit, local fatigue/needs,
next departure, stock, farming seed and genuinely completed work at h24-36.
The trace is diagnostic, NOT an endurance pass.
"""
from __future__ import annotations
import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.routines import routine_allows_work
from carlos_sim.supply import choose_cargo_manifest, choose_courier_leg
from carlos_sim.economic_autonomy import choose_local_production
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

CHECKS = (6, 12, 18, 24, 24.5, 25, 26, 27, 28, 29, 30, 32, 34, 36)
FARMS = ("farm", "farm_east")


def _audit(s):
    report = {"hour": s.time / HOUR, "copper": audit_npc_economy(s)["copper_known_total"],
              "water_in_well": s.resources["well"]["water"],
              "rain_cumulative": s.hydrology_sources["well"]["received_total"],
              "market_food": s.resources["market"]["food"],
              "food_by_warehouse": {w: s.resources[w].get("food", 0)
                                    for w in ("market","bakery","well","farm","farm_east",
                                              "hunting_woods","riverbank")},
              "work_since_start": sum(j["status"]=="completed" for j in s.production_jobs.values())}
    report["farms"] = {}
    for site in FARMS:
        plot = s.farm_plots[site]
        worker = "nora" if site == "farm" else "farid"
        r = s.resources[site]
        report["farms"][site] = {
            "worker": worker, "hunger": s.npcs[worker]["needs"]["hunger"],
            "fatigue": s.npcs[worker]["needs"]["fatigue"],
            "where": s.entities[worker]["location_id"],
            "workable": routine_allows_work(s, worker),
            "seed": r["seed"], "grain": r["grain"],
            "crop_ready": r["crop_ready"], "crop_seeded": r["crop_seeded"],
            "water": r["water"], "started": plot["started"],
            "matured": plot["matured"], "status": plot["status"],
            "current_proposal": None if choose_local_production(
                s, worker, agriculture_enabled=True) is None else
                choose_local_production(s, worker, agriculture_enabled=True).recipe_id,
        }
    report["couriers"] = {}
    for who in ("huda","hana"):
        p=s.supply_circuits[who]
        person=s.npcs[who]
        load=choose_cargo_manifest(s,who)
        trip=choose_courier_leg(s,who)
        report["couriers"][who]={
            "at":s.entities[who]["location_id"],
            "hunger":person["needs"]["hunger"],
            "fatigue":person["needs"]["fatigue"],"safety":person["needs"]["safety"],
            "owned_food":s.resources[who]["food"],
            "held_water":s.resources[who]["water"],
            "circuit_index":p["index"],
            "rounds":p["rounds"],"delivery_count":p["deliveries"],
            "carry":dict(p["carry"]) if p["carry"] is not None else None, "next_departure":p["next_departure"],
            "cargo_action":load, "next_leg":trip,
            "wage_receipts": sum(len(c["payments"]) for c in s.courier_provisions.values()
                                if c["courier_id"]==who),
            "meals": sum(m["npc_id"]==who for m in s.consumptions.values()),
        }
    return report


def test_real_wet_season_courier_seed_and_work_gates(tmp_path):
    path=tmp_path/"actual-stop-times.sqlite"
    s=signed_genesis(path)
    assert len(s.npcs)==13
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner=engine(db,clock,reserve_trader_meal=True,
                          deferred_market_courier_wage=True)
            water_service=FiniteWaterService(db,clock)
            for h in CHECKS:
                before=db.verify(WORLD)
                target=int(h*HOUR)
                state=runner.advance(WORLD,seconds=target-before.time,
                    command_id="huda-physical-timing-"+str(h),
                    expected_revision=before.revision).state
                assert state.time==target
                conserve_diverse(state)
                assert audit_npc_economy(state)["copper_known_total"]==12
                assert db.verify(WORLD).to_dict()==state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                report=_audit(state)
                print("PLAY48_ACTUAL_24H_36H_HUDA_FARM_COURIER_GATES "+
                      json.dumps(report,sort_keys=True),flush=True)
                if h==24:
                    wet=water_service.record(WORLD,"well","precommitted-wet-day1",2,
                        command_id="same-24h-real-rain",expected_revision=state.revision).state
                    assert wet.hydrology_sources["well"]["received_total"]==2
                    assert db.verify(WORLD).to_dict()==wet.to_dict()
            assert db.verify(WORLD).time==36*HOUR
        finally:
            clock.close_session(WORLD)
