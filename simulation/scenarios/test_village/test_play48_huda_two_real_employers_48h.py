"""PLAY48 source-pinned 13NPC 48h: two DISTINCT earned local courier wages.

Existing PR103 fixes Huda's genuine well-water dispatch, but she delivers
real cargo without food and still reaches hunger100 at h36. The original
bakery site holds one ORIGINAL loaf at time-zero; compare two otherwise
identical physical worlds (13 people, 12 copper, three starting loaves):
control bakery owns it; treatment signs ONE genuinely owned bakery loaf
payable after authentic GRAIN delivery, PLUS zero-initial-stock market contract
payable ONLY after a separate physically verified MARKET FOOD delivery
with at least two non-quoted market loaves. No double payment for one job.

Unlike negative PR97, market opening bread remains fully saleable and Hana's
separate deferred market wages remain the same in BOTH worlds. We strictly
measure displaced baker nutrition and market availability, not just Huda pay.
"""
from __future__ import annotations

import json
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.store import InvalidEvent
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_courier_market_income import signed_genesis
from test_play48_real_watch_income_24h import engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures


CHECKS=(6,12,24,24.5,25,30,36,48)


def actual_genesis(path, *, funded_huda):
    state=signed_genesis(path,worker_ids=("hana",))
    assert len(state.npcs)==13
    assert state.resources["market"]["food"]==2
    assert state.resources["bakery"]["food"]==1
    assert state.resources["huda"]["food"]==0
    assert audit_npc_economy(state)["copper_known_total"]==12
    if not funded_huda:
        return state
    with SQLiteEventStore(path) as db:
        prev=db.verify(WORLD)
        next_=db.append(
            WORLD,"bakery-owns-one-genuine-grain-service-wage",prev.revision,
            [DomainEvent("CourierProvisionConfigured",None,
                "trusted employer pays actual grain arrival only",0,
                {"id":"bakery-huda-real-grain", "courier_id":"huda",
                 "payer_site":"bakery","units":1}),
             DomainEvent("CourierProvisionConfigured",None,
                "second employer may pay ONLY later unquoted received market food",0,
                {"id":"market-huda-later-real-food",
                 "courier_id":"huda","payer_site":"market","units":0,
                 "authorized_total_units":2})],
            bootstrap=True
        )
        assert next_.resources["market"]["food"]==2
        assert next_.resources["bakery"]["food"]==0
        assert next_.courier_provisions["bakery-huda-real-grain"]["remaining"]==1
        assert next_.courier_provisions["market-huda-later-real-food"]["remaining"]==0
        assert sum(x["remaining"] for x in
                   next_.courier_provisions.values())==1
        assert (sum(q.get("food",0) for q in next_.resources.values())
                + sum(x["remaining"] for x in
                      next_.courier_provisions.values()))==3
        assert db.verify(WORLD).to_dict()==next_.to_dict()
        conserve_diverse(next_)
        return next_


def report(s):
    r=measures(s)
    for who in ("hana","huda","basim"):
        r[who]={
            "hunger":s.npcs[who]["needs"]["hunger"],
            "eaten":sum(c["npc_id"]==who for c in s.consumptions.values()),
            "owned_food":s.resources[who].get("food",0),
            "where":s.entities[who]["location_id"],
        }
    for who in ("hana","huda"):
        r[who]["deliveries"]=s.supply_circuits[who]["deliveries"]
        r[who]["wages"]=[
            {"contract_id":cid,"service":row["service_deliveries"],
             "paid_at":row["paid_at"]}
            for cid,c in sorted(s.courier_provisions.items())
            if c["courier_id"]==who
            for row in c["payments"]
        ]
    r["bakery_food"]=s.resources["bakery"]["food"]
    r["market_food"]=s.resources["market"]["food"]
    r["well_water"]=s.resources["well"]["water"]
    r["farm_cycles"]=s.farm_plots["farm"]["started"]
    r["rain"]=s.hydrology_sources["well"]["received_total"]
    return r


def run(path,*,funded_huda):
    genesis=actual_genesis(path,funded_huda=funded_huda)
    collected=[]
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            rain=FiniteWaterService(db,clock)
            for hour in CHECKS:
                prev=db.verify(WORLD)
                s=sim.advance(WORLD,seconds=int(hour*HOUR)-prev.time,
                    command_id=f"same-genuine-huda-work:{funded_huda}:{hour}",
                    expected_revision=prev.revision).state
                assert len(s.npcs)==13
                assert s.time==int(hour*HOUR)
                conserve_diverse(s)
                cash=audit_npc_economy(s)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"]==12
                assert db.verify(WORLD).to_dict()==s.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                collected.append(report(s))
                if hour==24:
                    measured=rain.record(
                        WORLD,"well","single-fixed-real-rain-day1",2,
                        command_id="original-same-two-water-day1",
                        expected_revision=s.revision).state
                    conserve_diverse(measured)
                    assert db.verify(WORLD).to_dict()==measured.to_dict()
        finally:
            clock.close_session(WORLD)
    return genesis,collected


def test_huda_true_independent_bakery_and_market_wages_cure_hunger_without_hurting_other_workers(tmp_path):
    a0,baseline=run(tmp_path/"original-bakery-one-owned-loaf.sqlite",
                    funded_huda=False)
    b0,trial=run(tmp_path/"bakery-one-real-signed-grain-wage.sqlite",
                 funded_huda=True)
    assert set(a0.npcs)==set(b0.npcs)
    assert audit_npc_economy(a0)["copper_known_total"]==12
    assert audit_npc_economy(b0)["copper_known_total"]==12
    assert a0.resources["market"]["food"]==b0.resources["market"]["food"]==2
    print("PLAY48_HUDA_TWO_DISTINCT_REAL_EMPLOYER_48H_AB "+
          json.dumps({"control":baseline,"bakery_wage":trial},
                     sort_keys=True),flush=True)
    original=baseline[-1]
    payroll=trial[-1]
    wage_ids = {v["contract_id"] for v in payroll["huda"]["wages"]}
    assert "bakery-huda-real-grain" in wage_ids, (
        "RELEASE_NO_GO: physical grain service at bakery not paid"
    )
    assert "market-huda-later-real-food" in wage_ids, (
        "RELEASE_NO_GO: no separately completed real market food delivery wage"
    )
    assert payroll["huda"]["eaten"]>=2, (
        "RELEASE_NO_GO: two genuine separate wage receipts were not consumed"
    )
    assert payroll["huda"]["eaten"]>original["huda"]["eaten"], (
        "RELEASE_NO_GO: bakery claim never became a real Huda meal"
    )
    assert payroll["huda"]["hunger"]<90, (
        "RELEASE_NO_GO: Huda cannot return to work even after distinct services"
    )
    assert payroll["food_eaten_meals"]>=original["food_eaten_meals"], (
        "RELEASE_NO_GO: apparent Huda benefit only robbed other residents"
    )
    assert payroll["total_food_sales"]>=original["total_food_sales"], (
        "RELEASE_NO_GO: do not choke genuine food market"
    )
    assert payroll["hana"]["deliveries"]>=original["hana"]["deliveries"], (
        "RELEASE_NO_GO: must not derail real market logistics"
    )
    assert payroll["basim"]["eaten"]>=original["basim"]["eaten"], (
        "RELEASE_NO_GO: employer's baker must not starve for courier wage"
    )


def test_bakery_cannot_pay_without_authentic_grain_delivery(tmp_path):
    path=tmp_path/"fake-unearned-grain-receipt.sqlite"
    initial=actual_genesis(path,funded_huda=True)
    with SQLiteEventStore(path) as db:
        before=db.verify(WORLD)
        assert before.to_dict()==initial.to_dict()
        with pytest.raises((InvalidEvent,ValueError)):
            db.append(
                WORLD,"forged-bakery-pay-without-grain",before.revision,
                [DomainEvent("CourierProvisionPaid",None,
                    "no matching physically delivered cargo",0,
                    {"id":"bakery-huda-real-grain","courier_id":"huda",
                     "service_deliveries":1,
                     "proof":"bakery_grain_delivery"})],
                supply_authorized=True)
        assert db.verify(WORLD).to_dict()==before.to_dict()

def test_market_future_pay_cannot_be_forged_or_signed_twice(tmp_path):
    path=tmp_path/"fake-market-secondary-cashout.sqlite"
    seed=actual_genesis(path,funded_huda=True)
    with SQLiteEventStore(path) as db:
        old=db.verify(WORLD)
        assert old.to_dict()==seed.to_dict()
        with pytest.raises((InvalidEvent,ValueError)):
            db.append(WORLD,"pay-unearned-market-bread",old.revision,[
                DomainEvent("CourierProvisionPaid",None,
                    "worker never delivered a market loaf yet",0,
                    {"id":"market-huda-later-real-food",
                     "courier_id":"huda","service_deliveries":1})
            ],supply_authorized=True)
        with pytest.raises((InvalidEvent,ValueError)):
            db.append(WORLD,"double-market-employer",old.revision,[
                DomainEvent("CourierProvisionConfigured",None,
                    "cannot sign two market jobs for same person",0,
                    {"id":"market-huda-duplicate-job","courier_id":"huda",
                     "payer_site":"market","units":0,
                     "authorized_total_units":1})
            ],bootstrap=True)
        assert db.verify(WORLD).to_dict()==old.to_dict()
