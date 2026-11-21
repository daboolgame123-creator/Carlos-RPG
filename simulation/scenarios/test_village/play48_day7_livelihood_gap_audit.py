"""Read-only audit of genuinely saved PLAY48 day7 13-NPC P3 ledger.

Does not simulate, rewrite events, inject resources or infer remote food knowledge.
Classifies physically owned food, cash, jobs and unconsumed market inventory
before proposing another speculative economic rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = sorted(args.input.rglob("genuine_harvest.sqlite"))
    assert len(paths) == 1, f"authenticated P3 h168 saved ledger not unique: {paths}"
    path = paths[0]
    initial_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        s = db.load(WORLD)
        assert s.time == 168 * HOUR and len(s.npcs) == 13
        audit = audit_npc_economy(s)
        assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
        m = metrics(s)

        world_goods = {site: {
            key: stock.get(key, 0) for key in
            ("food", "grain", "crop_ready", "coin_copper")
            if stock.get(key, 0) > 0
        } for site, stock in sorted(s.resources.items())
            if (stock.get("food", 0) or stock.get("grain", 0)
                or stock.get("crop_ready", 0) or stock.get("coin_copper", 0))}
        npc_rows = []
        for who, npc in sorted(s.npcs.items()):
            routine = s.npc_routines.get(who) or {}
            own = s.resources.get(who, {})
            completed_jobs = [
                j for j in s.production_jobs.values()
                if j["npc_id"] == who and j["status"] == "completed"
            ]
            wages = [
                j.get("work_wage") for j in completed_jobs
                if j.get("work_wage") is not None
            ]
            trades = [
                t for t in s.market_trades.values()
                if t["buyer_id"] == who and t["resource"] == "food"
            ]
            meals = [
                receipt for receipt in s.consumptions.values()
                if receipt["npc_id"] == who
            ]
            row = {
                "id": who, "role": npc["role"],
                "hunger": npc["needs"]["hunger"],
                "fatigue": npc["needs"]["fatigue"],
                "safety": npc["needs"]["safety"],
                "site": s.entities[who]["location_id"],
                "workplace": routine.get("workplace_id"),
                "food_owned": own.get("food", 0),
                "copper_owned": own.get("coin_copper", 0),
                "completed_jobs": len(completed_jobs),
                "paid_jobs": len(wages),
                "food_purchases": len(trades),
                "meals": len(meals),
                "stalled_at_hunger100": npc["needs"]["hunger"] == 100,
            }
            npc_rows.append(row)
            print("PLAY48_DAY7_NPC_LIVELIHOOD " + json.dumps(
                row, sort_keys=True), flush=True)

        offer_rows = [{
            "id": oid, "site": o["site_id"], "owner": o["stock_owner_id"],
            "seller": o["seller_id"], "resource": o["resource"],
            "unit_price": o["unit_price"], "remaining": o["remaining"],
            "status": o["status"],
        } for oid, o in sorted(s.market_offers.items())
            if o["resource"] == "food" and o["status"] == "open"]
        rations = s.market_stalls["market"]["community_food"]["payments"]
        result = {
            "source": str(path), "source_sha256": initial_sha256,
            "hour": 168, "npc_count": 13, "total_copper": 12,
            "starving": m["starving"], "meals": m["meals"],
            "sales": m["sales"], "cash_wages": m["cash_wages"],
            "bread": m["bread"], "rations": len(rations),
            "goods_by_owner": world_goods, "food_offers": offer_rows,
            "npcs": npc_rows,
            "read_only": True, "release_gate": "PLAY48_NO_GO",
        }
        assert hashlib.sha256(path.read_bytes()).hexdigest() == initial_sha256
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True),
                               encoding="utf8")
        print("PLAY48_DAY7_LIVELIHOOD_TOTALS " + json.dumps({
            key: result[key] for key in
            ("hour", "npc_count", "total_copper", "starving",
             "meals", "sales", "cash_wages", "bread", "rations")
        }, sort_keys=True), flush=True)
        print("PLAY48_DAY7_LIVELIHOOD_GOODS " + json.dumps({
            "goods_by_owner": world_goods, "food_offers": offer_rows,
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
