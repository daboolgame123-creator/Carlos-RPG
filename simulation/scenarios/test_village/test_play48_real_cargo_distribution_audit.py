"""PLAY48 — compare the deliveries RECEIVED by owners, not only courier name.

The authentic original 13-resident village is advanced twice, with exactly
the same 12 copper, weather, known roads and external rain. Never mistake
redistribution of work between two real couriers for a vanished parcel.

This test does NOT modify the engine or soften the strict PR127 acceptance.
It is a separate provenance-based economic decision gate: if a food, grain,
water or real customer shipment is actually lost, emit full evidence and
fail rather than treating total courier traffic as sufficient.
"""
from __future__ import annotations

import json
from collections import Counter

from carlos_sim import SQLiteEventStore
from test_play38_multi_farm_couriers import WORLD
from test_play48_deferred_bakery_grain_wages_ab import simulate, HOURS

COURIERS = ("hana", "huda")
RESOURCES = ("food", "grain", "water", "coin_copper")


def physical_receipts(path, hour):
    """Only cryptographically checked original SQLite event receipts count."""
    c = Counter()
    times = {who: [] for who in COURIERS}
    with SQLiteEventStore(path) as db:
        last = db.verify(WORLD)
        assert last.rules_version == 68 and len(last.npcs) == 13
        records = db.db.execute(
            "SELECT seq,payload FROM events WHERE world_id=? ORDER BY seq",
            (WORLD,),
        ).fetchall()
        for seq, raw in records:
            event = json.loads(raw)
            if event["time"] > hour * 3600:
                continue
            if event["event_type"] != "SupplyCargoDelivered":
                continue
            who = event["actor_id"]
            if who not in COURIERS:
                continue
            resource = event["data"]["resource"]
            assert resource in RESOURCES
            # An actual delivery is authenticated by the world's replay.
            # Do not treat a picked parcel as a received unit.
            c[(who, resource)] += 1
            times[who].append({
                "sequence": seq, "hour": round(event["time"]/3600,5),
                "commodity": resource,
            })
        wallets = {
            who: {resource: last.resources[who].get(resource)
                  for resource in ("food", "coin_copper")}
            for who in COURIERS
        }
        hunger = {who: last.npcs[who]["needs"]["hunger"]
                  for who in last.npcs}
        meals = Counter(
            item["npc_id"] for item in last.consumptions.values()
        )
        salary = {
            who: [
                row for x in last.courier_provisions.values()
                if x["courier_id"]==who
                for row in x["payments"]
            ]
            for who in COURIERS
        }
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
    return {
        "by_worker_and_kind": {
            who: {resource:c[(who,resource)] for resource in RESOURCES}
            for who in COURIERS
        },
        "by_commodity": {
            resource:sum(c[(who,resource)] for who in COURIERS)
            for resource in RESOURCES
        },
        "combined_total": sum(c.values()),
        "wallets_at_h48": wallets,
        "hunger_at_h48": hunger,
        "meals_by_npc_at_h48": dict(sorted(meals.items())),
        "signed_market_payroll_at_h48": {
            who:len(rows) for who,rows in salary.items()
        },
        "actual_receipts": times,
    }


def test_same_original_cargo_reallocated_or_lost(tmp_path):
    a_path = tmp_path/"control-physical.sqlite"
    b_path = tmp_path/"bakery-earned-physical.sqlite"
    baseline=simulate(a_path,deferred=False)
    candidate=simulate(b_path,deferred=True)
    a48=physical_receipts(a_path,48)
    b48=physical_receipts(b_path,48)
    actual_failures=[]
    for hour in HOURS:
        old, new = physical_receipts(a_path,hour),physical_receipts(b_path,hour)
        result={
            "h":hour,
            "courier_receipts_control":old["by_worker_and_kind"],
            "courier_receipts_candidate":new["by_worker_and_kind"],
            "actual_received_by_commodity_delta":{
                x:new["by_commodity"][x]-old["by_commodity"][x]
                for x in RESOURCES
            },
            "total_delivered_delta":new["combined_total"]-old["combined_total"],
            "food_sales_delta":
                candidate[hour]["food_sales"]-baseline[hour]["food_sales"],
            "bakery_jobs_delta":
                candidate[hour]["bakery_finished"]-baseline[hour]["bakery_finished"],
            "village_meals_delta":
                candidate[hour]["meals"]-baseline[hour]["meals"],
            "huda_meals_delta":
                candidate[hour]["huda_meals"]-baseline[hour]["huda_meals"],
            "huda_hunger_delta":
                candidate[hour]["huda_hunger"]-baseline[hour]["huda_hunger"],
            "physical_events_strict_replay_verified":True,
        }
        print("PLAY48_ACTUAL_COMMODITY_COURIER_REDISTRIBUTION_AB " +
              json.dumps(result,sort_keys=True),flush=True)
        if new["combined_total"]<old["combined_total"]:
            actual_failures.append((hour,"actually_delivered_total_lost",
                                    old["combined_total"]-new["combined_total"]))
        for resource in RESOURCES:
            if new["by_commodity"][resource]<old["by_commodity"][resource]:
                actual_failures.append((
                    hour,f"genuine_{resource}_delivered_lost",
                    old["by_commodity"][resource]-new["by_commodity"][resource]))
        for measure in ("food_sales","meals","bakery_finished"):
            if candidate[hour][measure]<baseline[hour][measure]:
                actual_failures.append((hour,f"lost_{measure}",
                         baseline[hour][measure]-candidate[hour][measure]))
    for who in COURIERS:
        print("PLAY48_COURIER_OWNER_SAFETY " +
            json.dumps({"courier":who,
                "old_personal_food":a48["wallets_at_h48"][who],
                "new_personal_food":b48["wallets_at_h48"][who],
                "old_hunger":a48["hunger_at_h48"][who],
                "new_hunger":b48["hunger_at_h48"][who],
                "old_meals":a48["meals_by_npc_at_h48"].get(who,0),
                "new_meals":b48["meals_by_npc_at_h48"].get(who,0),
                "old_signed_market_food_wages":a48["signed_market_payroll_at_h48"][who],
                "new_signed_market_food_wages":b48["signed_market_payroll_at_h48"][who],
            },sort_keys=True),flush=True)
    hunger_regression = {
        who:(a48["hunger_at_h48"][who],b48["hunger_at_h48"][who])
        for who in a48["hunger_at_h48"]
        if b48["hunger_at_h48"][who] > a48["hunger_at_h48"][who]
    }
    print("PLAY48_ANY_WORSE_NPC_HUNGER_AT_H48 " +
        json.dumps(hunger_regression,sort_keys=True),flush=True)
    if hunger_regression:
        actual_failures.append((48,"other_npc_hunger_increased",hunger_regression))
    if b48["meals_by_npc_at_h48"].get("hana",0)<a48["meals_by_npc_at_h48"].get("hana",0):
        actual_failures.append((48,"Hana_own_real_meals_declined",1))
    if b48["signed_market_payroll_at_h48"]["hana"]<a48["signed_market_payroll_at_h48"]["hana"]:
        actual_failures.append((48,"Hana_signed_wage_removed",1))
    if candidate[36]["huda_meals"]<=baseline[36]["huda_meals"]:
        actual_failures.append((36,"Huda_salary_not_eaten",1))
    if candidate[36]["huda_hunger"]>=baseline[36]["huda_hunger"]:
        actual_failures.append((36,"Huda_hunger_not_improved",1))
    print("PLAY48_ORIGINAL_FREIGHT_ACCEPTANCE_ALL_REAL_FAILURES "+
          json.dumps(actual_failures,sort_keys=True),flush=True)
    assert not actual_failures, (
        "original village commodity/recipient safeguards failed: "
        + repr(actual_failures))
