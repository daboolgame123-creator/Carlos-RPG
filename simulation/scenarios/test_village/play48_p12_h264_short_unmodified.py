"""P12: advance a COPY of genuine P11 h264 to see if idle Salma resumes aid.

No new behavior, tuning, free goods or intervention. This is an operator-only
replay of the unmodified real village with its precise P11 flag configuration.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.community_food import choose_market_ration
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, conserve_diverse
from play48_p11_real240_renewable_wage import FLAGS

SOURCE = Path("evidence/p12_real264/P11_real_wage.sqlite")
OUT = Path("play48_p12_short_continuation")
HOURS = (264, 265, 266, 270)


def at(s) -> dict:
    market = s.resources["market"]
    relief = s.market_stalls["market"]["community_food"]
    today = s.time // (24 * 3600)
    baker = s.npcs["basim"]
    salma = s.npcs["salma"]
    last_baking = max((
        j["finished_at"] for j in s.production_jobs.values()
        if j["status"] == "completed" and j["recipe_id"] == "grain-to-bread"
    ), default=None)
    running_owner_tasks = [
        {"action": a["action"], "due": a["due"]}
        for a in s.actions.values()
        if a["npc_id"] == "salma" and a["status"] == "running"
    ]
    return {
        "hour": s.time // HOUR, "time": s.time,
        "baker_hunger": baker["needs"]["hunger"],
        "baker_food": s.resources["basim"].get("food", 0),
        "baker_location": s.entities["basim"]["location_id"],
        "keeper_hunger": salma["needs"]["hunger"],
        "keeper_tasks": running_owner_tasks,
        "market_owned_food": market.get("food", 0),
        "bakery_grain": s.resources["bakery"].get("grain", 0),
        "bakery_food": s.resources["bakery"].get("food", 0),
        "last_real_baking_at": last_baking,
        "day_relief_receipts": [
            {"who": p["recipient_id"], "at": p["paid_at"]}
            for p in relief["payments"]
            if p["paid_at"] // (24 * 3600) == today
        ],
        "next_local_signed_ration": choose_market_ration(s),
        "hungry_100": [
            who for who, npc in sorted(s.npcs.items())
            if npc["needs"]["hunger"] == 100
        ],
        "huda_food_wages": sum(
            x["payment"] is not None
            for x in s.supply_circuits["huda"]["food_payroll"]["receipts"]
        ),
    }


def arm(name: str, *, resting_ration: bool) -> dict:
    copy = OUT / (name + ".sqlite")
    shutil.copyfile(SOURCE, copy)
    rows = {}
    with SQLiteEventStore(copy) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = db.load(WORLD)
            assert state.time == HOURS[0] * HOUR and len(state.npcs) == 13
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            for flag in FLAGS:
                setattr(sim, flag, True)
            sim.local_market_freight_wage_enabled = True
            sim.resting_market_ration_enabled = resting_ration
            for hour in HOURS:
                if hour > HOURS[0]:
                    state = sim.advance(
                        WORLD, seconds=hour * HOUR - state.time,
                        command_id=f"p12-{name}-h{hour}",
                        expected_revision=state.revision,
                    ).state
                assert len(state.npcs) == 13
                conserve_diverse(state)
                cash = audit_npc_economy(state)
                assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                db.snapshot(WORLD)
                assert db.load(WORLD).to_dict() == state.to_dict()
                rows[str(hour)] = at(state)
                print("PLAY48_P12_BAKERY_SHORT " + json.dumps({
                    "arm": name, **rows[str(hour)]
                }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT / (name + ".json")).write_text(
        json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")
    return rows


def main() -> None:
    assert SOURCE.is_file()
    original_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    OUT.mkdir(exist_ok=False)
    control = arm("P11_original", resting_ration=False)
    candidate = arm("P12_resting_receipt", resting_ration=True)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == original_hash
    comparison = {}
    for hour in HOURS[1:]:
        a, b = control[str(hour)], candidate[str(hour)]
        delta = {
            "hour": hour,
            "basim_hunger_delta": b["baker_hunger"] - a["baker_hunger"],
            "basim_received_ration": any(
                p["who"] == "basim" for p in b["day_relief_receipts"]),
            "market_food_delta": b["market_owned_food"] - a["market_owned_food"],
            "last_baking_at": b["last_real_baking_at"],
            "hungry100_delta": len(b["hungry_100"]) - len(a["hungry_100"]),
            "day_ration_count": len(b["day_relief_receipts"]),
            "gate": "PLAY48_NO_GO",
        }
        comparison[str(hour)] = delta
        print("PLAY48_P12_BAKERY_COMPARISON " + json.dumps(
            delta, sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(json.dumps({
        "immutable_original_h264_sha256": original_hash,
        "control": control, "candidate": candidate, "diff": comparison,
        "gate": "P12_EXPERIMENT_NO_GO / PLAY48_NO_GO",
    }, indent=2, sort_keys=True), encoding="utf8")
    # No invented bread, no extra ration: a *genuine* signed third daily
    # transfer must remain impossible, whether Basim recovered or not.
    assert all(len(row["day_relief_receipts"]) <= 2
               for row in candidate.values())
    assert candidate["270"]["baker_hunger"] < control["270"]["baker_hunger"], (
        "resting-ration experiment failed to improve the actual bread worker")



if __name__ == "__main__":
    main()
