"""PLAY48 original 13-resident candidate-only actual economy 96-hour endurance.

Diagnostic ONLY; one real candidate world to cheaply expose the known
h72 collapse before spending long twice-worlds 168h acceptance effort.
Original 12 copper coins conserved, rain truly recorded as exogenous water,
no generated food, contract/pay from actual completed bread, all real roads.
"""
from __future__ import annotations
import json
from collections import Counter

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play48_deferred_bakery_grain_wages_ab import seed, report
from test_play48_real_watch_income_24h import engine as original_engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play38_multi_farm_couriers import WORLD

HOURS=(24,36,48,60,72,84,96)

def test_authentic_13npc_still_produces_and_eats_on_days_three_and_four(tmp_path):
    path=tmp_path/"genuine-original-96h-candidate.sqlite"
    seed(path,deferred=True)
    seen={}
    with SQLiteEventStore(path) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim=original_engine(db,clock,reserve_trader_meal=True,
                                deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.deferred_bakery_grain_wage_enabled=True
            world=db.verify(WORLD)
            for hour in HOURS:
                world=sim.advance(
                    WORLD,seconds=hour*HOUR-world.time,
                    command_id=f"original-real-13NPC-96h:{hour}",
                    expected_revision=world.revision).state
                conserve_diverse(world)
                assert db.verify(WORLD).to_dict()==world.to_dict()
                audit=audit_npc_economy(world)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"]==12
                assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                stats=report(world)
                stats["starving_ids"]=sorted(
                    who for who,n in world.npcs.items()
                    if n["needs"]["hunger"]==100)
                stats["hunger_by_npc"]={
                    who:n["needs"]["hunger"]
                    for who,n in sorted(world.npcs.items())}
                stats["personal_meal_counts"]=dict(sorted(Counter(
                    item["npc_id"] for item in world.consumptions.values()
                ).items()))
                stats["actual_signed_huda_paid_loaves"]=sum(
                    row["paid_at"] is not None
                    for c in world.courier_provisions.values()
                    if c["courier_id"]=="huda"
                    for row in c.get("deferred_grain_services",()))
                stats["baker_actual_earned_labor"]=sum(
                    j["status"]=="completed" and j["site_id"]=="bakery"
                    for j in world.production_jobs.values())
                stats["water_ledger"]=audit["stock_known_by_resource"].get("water")
                seen[hour]=stats
                print("PLAY48_GENUINE_96H_ENDURANCE "+
                      json.dumps(stats,sort_keys=True),flush=True)
                if hour in (24,48,72):
                    world=FiniteWaterService(db,clock).record(
                        WORLD,"well",
                        f"fixed-external-rain-day{hour//24}",2,
                        command_id=f"real-attributed-source-day{hour//24}",
                        expected_revision=world.revision).state
                    conserve_diverse(world)
            assert db.snapshot(WORLD).to_dict()==world.to_dict()
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict()==world.to_dict()
    # These are actual economic survival gates; merely having a payable
    # claim or replayable static village does not mean recovery.
    assert seen[36]["huda_meals"]>=1, (
        "Huda never got a real job-funded meal")
    assert seen[48]["hunger100"]==0, (
        "the verified h48 population-level anti-starvation candidate regressed")
    assert seen[72]["meals"]>seen[48]["meals"], (
        "zero actual meals between days 2 and 3")
    assert seen[72]["bakery_finished"]>seen[48]["bakery_finished"], (
        "bakery production stopped before day 3")
    assert seen[96]["meals"]>seen[72]["meals"], (
        "no further completed meals over day 4")
    assert seen[96]["bakery_finished"]>seen[72]["bakery_finished"], (
        "real bread output did not repeat into day 4")
    assert seen[96]["hunger100"]<13, (
        "all original villagers reached hunger 100 by day 4")
