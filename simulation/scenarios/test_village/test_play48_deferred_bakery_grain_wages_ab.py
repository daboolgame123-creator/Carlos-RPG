"""PLAY48: physically earned, zero-initial-stock deferred bakery grain wage A/B."""
from __future__ import annotations
import json
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine as source_engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse

HOURS = (6, 24, 30, 36, 48)

def seed(path, *, deferred):
    original = signed_genesis(path, worker_ids=("hana",))
    with SQLiteEventStore(path) as db:
        original = db.append(WORLD, "sign-genuine-huda-deferred-"+str(deferred),
            original.revision, [DomainEvent("CourierProvisionConfigured", None,
                "time-zero employer signs without a single starter-loaf reservation", 0,
                {"id": "huda-future-bakery" if deferred else "real-surplus-only-huda",
                 "courier_id": "huda",
                 "payer_site": "bakery" if deferred else "market",
                 "units": 0, "authorized_total_units": 2,
                 **({"deferred_bakery_grain": True} if deferred else {})})],
            bootstrap=True)
        assert db.verify(WORLD).to_dict() == original.to_dict()
    assert (original.schema_version,original.rules_version) == (45,68)
    assert len(original.npcs) == 13
    assert original.resources["bakery"]["food"] == 1
    assert audit_npc_economy(original)["copper_known_total"] == 12
    assert sum(c["remaining"] for c in original.courier_provisions.values()) == 0
    conserve_diverse(original)
    return original

def report(s):
    audit = audit_npc_economy(s)
    assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
    c = next(c for c in s.courier_provisions.values() if c["courier_id"] == "huda")
    proof = c.get("deferred_grain_services", ())
    return {"hour":s.time//HOUR,
       "huda_hunger":s.npcs["huda"]["needs"]["hunger"],
       "huda_owned_food":s.resources["huda"]["food"],
       "huda_meals":sum(x["npc_id"]=="huda" for x in s.consumptions.values()),
       "meals":len(s.consumptions),
       "hunger100":sum(n["needs"]["hunger"]==100 for n in s.npcs.values()),
       "food_sales":sum(x["resource"]=="food" for x in s.market_trades.values()),
       "bakery_food":s.resources["bakery"]["food"],
       "bakery_finished":sum(j["status"]=="completed" and j["site_id"]=="bakery"
          and s.production_recipes[j["recipe_id"]]["output_resource"]=="food"
          for j in s.production_jobs.values()),
       "deliveries":{who:s.supply_circuits[who]["deliveries"]
                     for who in ("hana","huda")},
       "earned_huda_grain_service":len(proof),
       "paid_huda_service":sum(x["paid_at"] is not None for x in proof),
       "unpaid_huda_service":sum(x["paid_at"] is None for x in proof),
       "salma_food_wages":sum("steward_food_wage" in t
                                 for t in s.market_trades.values())}

def simulate(path, *, deferred):
    seed(path,deferred=deferred)
    result={}
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=source_engine(db,clock,reserve_trader_meal=True,
                              deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.deferred_bakery_grain_wage_enabled=deferred
            s=db.verify(WORLD)
            for hour in HOURS:
                s=sim.advance(WORLD,seconds=hour*HOUR-s.time,
                    command_id=f"deferred-bakery-AB:{hour}",
                    expected_revision=s.revision).state
                conserve_diverse(s)
                assert db.verify(WORLD).to_dict()==s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
                result[hour]=report(s)
                if hour==24:
                    s=FiniteWaterService(db,clock).record(
                        WORLD,"well","fixed-external-rain-day1",2,
                        command_id="real-attributed-source-day1",
                        expected_revision=s.revision).state
                    assert db.verify(WORLD).to_dict()==s.to_dict()
            assert db.snapshot(WORLD).to_dict()==s.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict()==s.to_dict()
    return result

def test_deferred_grain_no_payment_without_real_delivery_or_production(tmp_path):
    path=tmp_path/"unearned.sqlite"
    state=seed(path,deferred=True)
    fake=DomainEvent("CourierBakeryDeferredFoodPaid",None,
        "forged service must not produce food",0,
        {"id":"huda-future-bakery","courier_id":"huda",
         "service_deliveries":999,"amount":1})
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            with pytest.raises(InvalidEvent):
                db.append(WORLD,"unauthenticated",state.revision,[fake])
            with pytest.raises(InvalidEvent):
                db.append(WORLD,"authorized-but-unearned",state.revision,[fake],
                    supply_authorized=True,production_authorized=True)
            assert db.verify(WORLD).to_dict()==state.to_dict()
        finally:
            clock.close_session(WORLD)

def test_original_13npc_deferred_bakery_income_acceptance_ab(tmp_path):
    old=simulate(tmp_path/"control.sqlite",deferred=False)
    new=simulate(tmp_path/"deferred.sqlite",deferred=True)
    for hour in HOURS:
        a,b=old[hour],new[hour]
        print("PLAY48_DEFERRED_BAKERY_REAL_HUDA_AB "+
            json.dumps({"hour":hour,"control":a,"candidate":b,
                        "food_sales_delta":b["food_sales"]-a["food_sales"],
                        "meals_delta":b["meals"]-a["meals"],
                        "courier_delivery_delta":{
                            who:b["deliveries"][who]-a["deliveries"][who]
                            for who in ("hana","huda")},
                        "twelve_copper_conserved":True,
                        "physical_food_water_conserved":True,
                        "sqlite_replay_integrity":True,
                        "release_no_go":True},sort_keys=True),flush=True)
        assert b["paid_huda_service"]<=b["earned_huda_grain_service"]
    assert new[30]["earned_huda_grain_service"]>=1, (
        "real Huda grain should have a durable service claim by h30")
    assert new[36]["huda_meals"]>old[36]["huda_meals"], (
        "deferred signed bakery salary did not become a real meal before starvation")
    assert new[36]["huda_hunger"]<old[36]["huda_hunger"]
    for hour in (30,36,48):
        assert new[hour]["food_sales"]>=old[hour]["food_sales"]
        assert new[hour]["meals"]>=old[hour]["meals"]
        assert new[hour]["bakery_finished"]>=old[hour]["bakery_finished"]
        for who in ("hana","huda"):
            assert new[hour]["deliveries"][who]>=old[hour]["deliveries"][who], (
                "deferred bakery wage stole original freight")
