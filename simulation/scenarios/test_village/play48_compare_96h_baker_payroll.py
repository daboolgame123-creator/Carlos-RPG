"""Compare two genuine 96h persisted worlds, not a synthetic economy.

Both actual 72->96h studies started from the identical saved 72h village.
This read-only diagnostic has no control over world decisions or resources.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import argparse

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy, audit_production_wages
from carlos_sim.food_for_work import _available_site_food
from play48_integrated_acceptance import WORLD, HOUR, metrics


def summarize(path: Path) -> dict:
    before = sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        world = db.load(WORLD)  # Each 96h artifact was fully verified before upload
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
        # No rewriting: inspect actual immutable event types and times as saved.
        activity = Counter()
        for (blob,) in db.db.execute(
            "SELECT payload FROM events WHERE world_id=? ORDER BY seq", (WORLD,)
        ):
            event = json.loads(blob)
            if 72 * HOUR <= event["time"] <= 96 * HOUR:
                activity[event["event_type"]] += 1
    assert sha256(path.read_bytes()).hexdigest() == before
    assert world.time == 96 * HOUR and len(world.npcs) == 13
    assert audit_npc_economy(world)["copper_known_total"] == 12
    row = metrics(world)
    jobs = [(ident, j) for ident, j in sorted(world.production_jobs.items())
            if j["npc_id"] == "basim" and j["status"] == "completed"]
    receipts = [{"job": ident, "hour": round(j["food_wage"]["paid_at"] / HOUR, 3),
                 "source_before": j["food_wage"]["site_before"],
                 "source_after": j["food_wage"]["site_after"]}
                for ident, j in jobs if "food_wage" in j]
    return {
        "ledger_sha256": before,
        "summary": {key: row[key] for key in
                    ("hour", "starving", "bread", "meals", "sales", "cash_wages")},
        "basim": row["npcs"]["basim"],
        "basim_recipe_roles": sorted({world.production_recipes[j["recipe_id"]]["role"]
                                      for _, j in jobs}),
        "basim_finished_batches": len(jobs),
        "basim_food_wage_receipts": receipts,
        "basim_unpaid_signed": sum(
            "food_wage" not in j and "wage_food" in world.production_recipes[j["recipe_id"]]
            for _, j in jobs
        ),
        "bakery_owned_food": world.resources["bakery"]["food"],
        "bakery_unpromised_food": _available_site_food(world, "bakery"),
        "market_owned_food": world.resources["market"]["food"],
        "production_wages": {
            k: v for k, v in audit_production_wages(world).items() if k != "unpaid_jobs"
        },
        "events_from_72h_to_96h": dict(sorted(activity.items())),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--trial", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old = summarize(args.baseline / "candidate.sqlite")
    new = summarize(args.trial / "candidate.sqlite")
    # Every 96h state starts from an original 72h ledger with 13 original NPCs.
    for label, item in (("36h", old), ("12h", new)):
        print("PLAY48_PAYROLL96 " + json.dumps({"variant": label, **item}, sort_keys=True), flush=True)
    diff = {
        "bread": new["summary"]["bread"] - old["summary"]["bread"],
        "meals": new["summary"]["meals"] - old["summary"]["meals"],
        "starving": new["summary"]["starving"] - old["summary"]["starving"],
        "basim_meals": new["basim"]["meals"] - old["basim"]["meals"],
        "basim_paid_food_wages": len(new["basim_food_wage_receipts"]) - len(old["basim_food_wage_receipts"]),
    }
    print("PLAY48_12H_CAUSAL_DELTA " + json.dumps(diff, sort_keys=True), flush=True)
    args.output.write_text(json.dumps({"baseline": old, "trial": new, "delta": diff,
                                      "gate_passed": False}, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
