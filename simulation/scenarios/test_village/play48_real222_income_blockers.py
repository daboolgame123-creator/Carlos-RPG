"""Read-only diagnosis of authentic 13 NPCs at h222 P4 and P5.
No replay, alternate seed, artificial transfers, NPC intervention or edits.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from carlos_sim.economic_autonomy import choose_local_production, choose_local_food_purchase
from play48_integrated_acceptance import WORLD, HOUR, metrics

SOURCE = Path("evidence/authentic222")
OUT = Path("real222_audit")


def one(arm: str) -> dict:
    files = sorted(SOURCE.rglob(arm + ".sqlite"))
    assert len(files) == 1, (arm, files)
    source = files[0]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with SQLiteEventStore(source) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
        state = db.load(WORLD)
        assert state.time == 222 * HOUR and len(state.npcs) == 13
        e = audit_npc_economy(state)
        assert e["copper_scope_complete"] and e["copper_known_total"] == 12
        rows = []
        for ident, n in sorted(state.npcs.items()):
            needs = n["needs"]
            food = state.resources[ident].get("food")
            money = state.resources[ident].get("coin_copper")
            planting = choose_local_production(
                state, ident, agriculture_enabled=True,
                desperate_paid_harvest_enabled=True,
                desperate_funded_planting_enabled=(arm == "P5_funded_seed"))
            buying = choose_local_food_purchase(state, ident)
            rows.append({
                "npc": ident, "role": n["role"],
                "hunger": needs["hunger"], "fatigue": needs["fatigue"],
                "site": state.entities[ident]["location_id"],
                "workplace": state.npc_routines.get(ident, {}).get("workplace_id"),
                "cash": money, "food": food,
                "proposed_job": planting.recipe_id if planting else None,
                "proposed_sale": buying.offer_id if buying else None,
                "next_decision_at": n["next_decision_at"],
                "last_decision": n["last_decision"],
            })
        goods = {
            k: {resource: value for resource, value in sorted(v.items())
                if type(value) is int and value > 0}
            for k, v in sorted(state.resources.items())
            if any(type(vv) is int and vv > 0 for vv in v.values())
        }
        stalls = [{
            "site": o["site_id"], "remaining": o["remaining"],
            "unit_price": o["unit_price"], "seller": o["seller_id"],
            "stock_owner": o["stock_owner_id"], "resource": o["resource"],
        } for o in state.market_offers.values() if o["status"] == "open"]
        report = {
            "arm": arm, "hour": 222, "npcs": rows,
            "resource_stocks": goods, "copper_by_owner": e["copper_known_by_owner"],
            "market_offers": stalls, "metrics": metrics(state),
            "actual_jobs_unpaid": audit_production_wages(state)["unpaid_jobs"],
            "wage_summary": {
                k: v for k, v in audit_production_wages(state).items()
                if k != "unpaid_jobs"
            },
            "farm_plots": state.to_dict()["farm_plots"],
            "source_sha256": digest,
        }
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    return report


def main():
    OUT.mkdir(exist_ok=False)
    for arm in ("P4_control", "P5_funded_seed"):
        report = one(arm)
        (OUT / (arm + ".json")).write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf8")
        summary = {
            "arm": arm,
            "starving": report["metrics"]["starving"],
            "meals": report["metrics"]["meals"],
            "sales": report["metrics"]["sales"],
            "wages": report["metrics"]["cash_wages"],
            "people": report["npcs"],
            "cash": {k: v for k, v in report["copper_by_owner"].items() if v},
            "stock": report["resource_stocks"],
            "market_offers": report["market_offers"],
            "wage_summary": report["wage_summary"],
        }
        print("PLAY48_AUTHENTIC_H222_BLOCKERS " +
              json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
