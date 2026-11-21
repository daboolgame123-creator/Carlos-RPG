"""Operator-only inspection of authentic h180 P3/P4 saved worlds.

Never modifies event history or changes a production policy. Deterministic
facts are printed to identify precisely why local work and trade stopped.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from carlos_sim.economic_autonomy import choose_local_production, choose_local_food_purchase
from play48_integrated_acceptance import WORLD, HOUR, metrics

SOURCE = Path("evidence/genuine180")
OUT = Path("audit180")
ARMS = ("P3_original", "P4_signed_quote_relief")


def describe(arm: str) -> dict:
    matches = sorted(SOURCE.rglob(arm + ".sqlite"))
    assert len(matches) == 1, (arm, matches)
    path = matches[0]
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
        s = db.load(WORLD)
        assert s.time == 180 * HOUR and len(s.npcs) == 13
        audit = audit_npc_economy(s)
        assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
        stock = {
            site: {k: v for k, v in sorted(inventory.items())
                   if isinstance(v, int) and v > 0}
            for site, inventory in sorted(s.resources.items())
            if any(isinstance(v, int) and v > 0 for v in inventory.values())
        }
        locals_ = []
        for who, npc in sorted(s.npcs.items()):
            position = s.entities[who]["location_id"]
            inventory = s.resources.get(who, {})
            intent = choose_local_production(
                s, who, agriculture_enabled=True,
                finite_aquifer_enabled=False, desperate_paid_harvest_enabled=True)
            purchase = choose_local_food_purchase(s, who, adaptive=False)
            locals_.append({
                "id": who, "role": npc["role"],
                "site": position,
                "workplace": s.npc_routines.get(who, {}).get("workplace_id"),
                "hunger": npc["needs"]["hunger"],
                "fatigue": npc["needs"]["fatigue"],
                "food": inventory.get("food", 0),
                "copper": inventory.get("coin_copper", 0),
                "production_intent": (
                    {"recipe": intent.recipe_id, "reason": intent.reason}
                    if intent is not None else None),
                "food_purchase_intent": (
                    {"price": purchase.price, "site": purchase.site_id}
                    if purchase is not None else None),
                "running_work": sum(j["npc_id"] == who and j["status"] == "running"
                                    for j in s.production_jobs.values()),
                "running_travel": sum(t["npc_id"] == who and t["status"] == "traveling"
                                      for t in s.travels.values()),
            })
        output = {
            "arm": arm, "hour": 180, "metrics": metrics(s),
            "financial": {
                "coins_by_owner": audit["copper_known_by_owner"],
                "wages": audit_production_wages(s),
                "completed_by_recipe": dict(sorted(Counter(
                    job["recipe_id"] for job in s.production_jobs.values()
                    if job["status"] == "completed").items())),
                "running_by_recipe": dict(sorted(Counter(
                    job["recipe_id"] for job in s.production_jobs.values()
                    if job["status"] == "running").items())),
            },
            "stock_owned_by_site_or_person": stock,
            "farm_plots": s.farm_plots,
            "recipes": s.production_recipes,
            "npcs": locals_,
            "routines": s.npc_routines,
            "supply_circuit_summary": {
                who: {
                    "keys": sorted(c.keys()),
                    "status": c.get("status"),
                    "deliveries": c.get("deliveries"),
                    "location": s.entities.get(who, {}).get("location_id"),
                } for who, c in sorted(s.supply_circuits.items())
            },
            "read_only": True, "release_gate": "PLAY48_NO_GO",
            "original_sha256": before,
        }
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    return output


def main():
    OUT.mkdir(exist_ok=False)
    all_rows = {}
    for arm in ARMS:
        row = describe(arm)
        all_rows[arm] = row
        (OUT / (arm + ".json")).write_text(
            json.dumps(row, indent=2, sort_keys=True), encoding="utf8")
        summary = {
            "arm": arm,
            "hunger100": row["metrics"]["starving"],
            "potential_work": [n for n in row["npcs"]
                               if n["production_intent"] is not None],
            "potential_food_buyers": [n["id"] for n in row["npcs"]
                                      if n["food_purchase_intent"] is not None],
            "npc_rows": row["npcs"],
            "coins": {k: v for k, v in row["financial"]["coins_by_owner"].items() if v},
            "stock": row["stock_owned_by_site_or_person"],
            "farm_plots": row["farm_plots"],
            "completed_recipes": row["financial"]["completed_by_recipe"],
            "running_recipes": row["financial"]["running_by_recipe"],
            "wages": row["financial"]["wages"],
        }
        print("PLAY48_DAY7_180_WORK_STALL " +
              json.dumps(summary, sort_keys=True), flush=True)
    (OUT / "comparison.json").write_text(
        json.dumps(all_rows, indent=2, sort_keys=True), encoding="utf8")


if __name__ == "__main__":
    main()
