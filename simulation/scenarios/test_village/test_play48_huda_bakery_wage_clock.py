"""PLAY48 narrow read-only time-sequencing diagnostic of Huda's earned bread.

A genuine grain delivery creates Huda's due service, but she can be out
of the bakery before finished bread exists. Report exact scheduler time,
worker location, quote-protected bread, completed bakery jobs and
pending signed service for each real checkpoint. No production/routing change.
"""
from __future__ import annotations

import json
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_for_work import _available_site_food, _worker_present_and_free
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.deferred_bakery_payroll import (
    choose_deferred_bakery_payment, _genuine_later_bread,
)
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_bakery_grain_wages_ab import seed
from test_play48_real_watch_income_24h import engine as source_engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

# Each point is an exact simulated second, not a wall-clock approximation.
TIMES = (24*HOUR, 24*HOUR+360, 24*HOUR+420, 24*HOUR+480,
         24*HOUR+540, 24*HOUR+600, 24*HOUR+720, 24*HOUR+900,
         24*HOUR+1200, 24*HOUR+1800, 25*HOUR, 26*HOUR, 30*HOUR)


def view(s):
    claimed = next(c for c in s.courier_provisions.values()
                   if c["courier_id"] == "huda")
    claims = claimed.get("deferred_grain_services", ())
    bakery_finished = sorted(
        ({ "started":j["started_at"], "due":j["due"],
           "finished":j["finished_at"],
           "output_amount":s.production_recipes[j["recipe_id"]]["output_amount"] }
         for j in s.production_jobs.values()
         if j["site_id"]=="bakery" and j["status"]=="completed"
         and s.production_recipes[j["recipe_id"]]["output_resource"]=="food"),
        key=lambda x:(x["finished"], x["started"]),
    )
    claim = claims[0] if claims else None
    earned = claim["earned_at"] if claim else None
    later = (bool(claim) and _genuine_later_bread(
                s.production_jobs, s.production_recipes, earned, s.time))
    free = _available_site_food(s,"bakery")
    ready = choose_deferred_bakery_payment(s,"huda")
    return {
        "at_hours":round(s.time/HOUR,5),
        "huda_site":s.entities["huda"]["location_id"],
        "huda_route_index":s.supply_circuits["huda"]["index"],
        "huda_cargo":s.supply_circuits["huda"]["carry"],
        "huda_traveling":any(t["npc_id"]=="huda" and t["status"]=="traveling"
                             for t in s.travels.values()),
        "huda_hunger":s.npcs["huda"]["needs"]["hunger"],
        "huda_owned_food":s.resources["huda"]["food"],
        "bakery_owned_food":s.resources["bakery"]["food"],
        "bakery_unquoted_unescrowed_food":free,
        "open_bakery_food_quotes":sum(q["remaining"] for q in s.market_offers.values()
              if q["stock_owner_id"]=="bakery" and q["status"]=="open"
              and q["resource"]=="food"),
        "bakery_completed_bread_jobs":len(bakery_finished),
        "first_completed_bread_after_service":next(
            (j for j in bakery_finished if earned is not None and
              j["finished"] > earned),None),
        "service_claim":dict(claim) if claim else None,
        "later_actual_bread_exists":later,
        "worker_present_and_free":_worker_present_and_free(s,"huda","bakery"),
        "salary_eligible":ready is not None,
        "blockers":{
            "no_authentic_grain_receipt": not bool(claim),
            "no_later_finished_bread":not later,
            "less_than_two_unpromised_loaves":free<2,
            "worker_not_physically_available_at_bakery":
              not _worker_present_and_free(s,"huda","bakery"),
        },
    }


def test_huda_post_grain_service_exact_timing_without_engine_edits(tmp_path):
    path=tmp_path/"original-huda-clock.sqlite"
    seed(path,deferred=True)
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=source_engine(db,clock,reserve_trader_meal=True,
                              deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.deferred_bakery_grain_wage_enabled=True
            last=db.verify(WORLD)
            for goal in TIMES:
                last=sim.advance(WORLD,seconds=goal-last.time,
                    command_id=f"real-grain-pay-clock-{goal}",
                    expected_revision=last.revision).state
                conserve_diverse(last)
                assert db.verify(WORLD).to_dict()==last.to_dict()
                assert audit_npc_economy(last)["copper_known_total"]==12
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                print("PLAY48_HUDA_BAKERY_ACTUAL_CLOCK "+
                    json.dumps(view(last),sort_keys=True),flush=True)
                if goal==24*HOUR:
                    last=FiniteWaterService(db,clock).record(
                        WORLD,"well","fixed-external-rain-day1",2,
                        command_id="real-attributed-source-day1",
                        expected_revision=last.revision).state
            # Real ordered event log: exact grain parcel & Huda's actual
            # departure, plus bakery fresh job and bakery-to-market freight.
            entries=[]
            for seq,raw in db.db.execute(
                "SELECT seq,payload FROM events WHERE world_id=? ORDER BY seq",(WORLD,)):
                e=json.loads(raw)
                t=e["time"]
                if not 24*HOUR<=t<=27*HOUR: continue
                kind=e["event_type"]
                who=e["actor_id"]
                data=e["data"]
                if ((who in ("huda","hana") and kind in (
                    "SupplyCargoPicked","SupplyCargoDelivered","NPCTravelStarted"))
                    or kind == "CourierBakeryDeferredFoodPaid"):
                    entries.append({
                        "seq":seq,"hour":round(t/HOUR,5),
                        "kind":kind,"actor":who,"resource":data.get("resource"),
                        "origin":data.get("origin"),"destination":data.get("destination"),
                    })
            print("PLAY48_HUDA_REAL_GRAIN_TO_BREAD_TIMELINE "+
                json.dumps({"events":entries[:200],
                "total_relevant_events":len(entries),
                "pay_claims":view(last)["service_claim"],
                "physical_12_copper":True,"replay":True},sort_keys=True),flush=True)
            assert db.snapshot(WORLD).to_dict()==last.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict()==last.to_dict()
