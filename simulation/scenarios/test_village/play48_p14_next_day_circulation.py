"""PLAY48 P14: operator-only genuine-world economic continuation across day 12.

No behavior changes, no free bread/copper, no artificial NPC action. Replay a
COPY of the exact proven P11 h264 SQLite with P12 flags ON through the next
daily ration reset; audit real spending, food ownership, work and delivery.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from play48_integrated_acceptance import WORLD, HOUR, conserve_diverse, engine
from play48_p11_real240_renewable_wage import FLAGS
from play48_p13_h270_hunger_barriers import checkpoint

SOURCE = Path("evidence/p14_real264/P11_real_wage.sqlite")
OUT = Path("play48_p14_next_day")
HOURS = (264, 265, 270, 276, 282, 288, 289, 294)
EXPECTED_H270 = ("burner", "hana", "miner", "nora", "repairman", "smith")
DAY_SECONDS = 24 * HOUR


def snapshot(state) -> dict:
    detail = checkpoint(state)
    economy = audit_npc_economy(state)
    wages = audit_production_wages(state)
    relief = state.market_stalls["market"]["community_food"]["payments"]
    events = sorted(relief, key=lambda p: p["paid_at"])
    people = {}
    for who, npc in sorted(state.npcs.items()):
        shops = [
            t for t in state.market_trades.values()
            if t["resource"] == "food" and t["buyer_id"] == who
        ]
        people[who] = {
            "role": npc["role"],
            "hunger": npc["needs"]["hunger"],
            "location": state.entities[who]["location_id"],
            "food_owned": state.resources[who].get("food"),
            "copper_slot": state.resources[who].get("coin_copper"),
            "meals": sum(m["npc_id"] == who for m in state.consumptions.values()),
            "purchases": len(shops),
            "food_wages": sum(
                j.get("food_wage") is not None
                for j in state.production_jobs.values() if j["npc_id"] == who
            ),
            "copper_wages": sum(
                j.get("work_wage") is not None
                for j in state.production_jobs.values() if j["npc_id"] == who
            ),
        }
    couriers = {}
    for who, circuit in sorted(state.supply_circuits.items()):
        payroll = circuit.get("food_payroll", {})
        couriers[who] = {
            "deliveries": circuit["deliveries"],
            "signed_payroll_receipts": len(payroll.get("receipts", [])),
            "paid_payroll_receipts": sum(
                rec["payment"] is not None for rec in payroll.get("receipts", [])
            ),
        }
    detail.update({
        "day": state.time // DAY_SECONDS,
        "population": people,
        "couriers": couriers,
        "trades": len(state.market_trades),
        "food_trades": sum(
            trade["resource"] == "food" for trade in state.market_trades.values()
        ),
        "completed_jobs": economy["completed_jobs"],
        "production_wages": {
            "coin_paid": wages["coin_paid"],
            "coin_unpaid": wages["coin_unpaid"],
            "food_paid": wages["food_paid"],
            "food_unpaid": wages["food_unpaid"],
        },
        "consumptions": len(state.consumptions),
        "signed_relief_receipts_all_days": [
            {"person": p["recipient_id"], "at": p["paid_at"],
             "day": p["paid_at"] // DAY_SECONDS}
            for p in events
        ],
        "copper_by_owner": economy["copper_known_by_owner"],
    })
    return detail


def summarize(row: dict) -> dict:
    return {
        "hour": row["hour"],
        "day": row["day"],
        "hungry100": [p["id"] for p in row["hungry100"]],
        "market_owned_food": row["market_owner_food"],
        "market_unquoted_food": row["market_unquoted_food"],
        "bakery_food": row["bakery_owner_food"],
        "bakery_grain": row["bakery_grain"],
        "relief_used_today": row["relief_used_today"],
        "relief_receipts_total": len(row["signed_relief_receipts_all_days"]),
        "trades": row["trades"],
        "food_trades": row["food_trades"],
        "completed_jobs": row["completed_jobs"],
        "consumptions": row["consumptions"],
        "production_wages": row["production_wages"],
        "courier_deliveries": {
            who: entry["deliveries"] for who, entry in row["couriers"].items()
        },
    }


def main() -> None:
    assert SOURCE.is_file(), "genuine immutable P11 h264 source missing"
    original_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    copy = OUT / "p12_unchanged_continuation.sqlite"
    shutil.copyfile(SOURCE, copy)
    rows = {}
    with SQLiteEventStore(copy) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = db.load(WORLD)
            assert state.time == HOURS[0] * HOUR
            assert len(state.npcs) == 13
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            for flag in FLAGS:
                setattr(sim, flag, True)
            sim.local_market_freight_wage_enabled = True
            sim.resting_market_ration_enabled = True
            for hour in HOURS:
                if hour > HOURS[0]:
                    state = sim.advance(
                        WORLD, seconds=hour * HOUR - state.time,
                        command_id=f"p14-original-p12-h{hour}",
                        expected_revision=state.revision,
                    ).state
                conserve_diverse(state)
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                db.snapshot(WORLD)
                assert db.load(WORLD).to_dict() == state.to_dict()
                row = snapshot(state)
                assert row["copper_known_total"] == 12
                rows[str(hour)] = row
                print("PLAY48_P14_NEXT_DAY " + json.dumps(
                    summarize(row), sort_keys=True
                ), flush=True)
                # Save inspected intermediate evidence even if a later gate fails.
                (OUT / "continuation.json").write_text(
                    json.dumps({
                        "source_sha": original_sha, "checks": rows,
                        "gate": "P14_DIAGNOSTIC_ONLY / PLAY48_NO_GO",
                    }, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
        finally:
            clock.close_session(WORLD)

    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == original_sha
    at_270 = tuple(x["id"] for x in rows["270"]["hungry100"])
    assert at_270 == EXPECTED_H270, (at_270, EXPECTED_H270)
    assert rows["270"]["market_owner_food"] == 7
    assert rows["270"]["market_unquoted_food"] == 0
    assert rows["270"]["relief_used_today"] == ["adel", "basim"]
    assert rows["270"]["copper_known_total"] == rows["294"]["copper_known_total"] == 12
    for hour in (288, 289, 294):
        report = rows[str(hour)]
        for who in EXPECTED_H270:
            print("PLAY48_P14_ACTOR " + json.dumps({
                "hour": hour, "id": who, **report["population"][who],
            }, sort_keys=True), flush=True)
    print("PLAY48_P14_DIAGNOSIS_PASS " + json.dumps({
        "day11_h270": summarize(rows["270"]),
        "day12_h294": summarize(rows["294"]),
        "immutable_source_sha": original_sha,
        "status": "P14_DIAGNOSTIC_PASS / PLAY48_NO_GO",
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
