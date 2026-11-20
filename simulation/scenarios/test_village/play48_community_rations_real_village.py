"""Real original 13-person PLAY48 village, genuine t0 A/B welfare experiment.

Both A/B arms use the SAME previous paid livelihood rules, genesis resources,
copper, rain, couriers, actors and roads. The only treatment difference is a
pre-authorized market-owned community ration contract and its optional runtime.
No historical saved-world edit, no gifting or inflation, no release gate waiver.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, seed, advance_to

CHECKPOINTS = (24, 48, 60, 72)


def snapshot(db_path: Path, measured: dict) -> dict:
    with SQLiteEventStore(db_path) as db:
        state = db.load(WORLD)
        assert state.time == measured["hour"] * HOUR
        ledger = audit_npc_economy(state)
        assert ledger["copper_scope_complete"] and ledger["copper_known_total"] == 12
        assert len(state.npcs) == 13
        c = state.market_stalls["market"].get("community_food", {})
        receipts = c.get("payments", [])
        return {
            "hour": measured["hour"],
            "copper": 12,
            "hungry100": measured["starving"],
            "bread": measured["bread"],
            "meals": measured["meals"],
            "cash_wages": measured["cash_wages"],
            "sales": measured["sales"],
            "market_owned_food": state.resources["market"]["food"],
            "market_open_offered_food": sum(
                o["remaining"] for o in state.market_offers.values()
                if o["status"] == "open" and o["stock_owner_id"] == "market"
                and o["resource"] == "food"
            ),
            "community_rations": len(receipts),
            "community_recipients": [r["recipient_id"] for r in receipts],
            "npc_meals": {who: row["meals"] for who, row in measured["npcs"].items()},
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--hours", type=int, choices=CHECKPOINTS, default=72)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    paths = {arm: args.directory / (arm + ".sqlite")
             for arm in ("baseline", "community")}
    for arm, path in paths.items():
        initial = seed(path, candidate=True, community_food=(arm == "community"))
        assert len(initial.npcs) == 13 and initial.time == 0
        assert sum(r.get("food", 0) for r in initial.resources.values()) == 3
        assert audit_npc_economy(initial)["copper_known_total"] == 12
    rows = {}
    for hour in CHECKPOINTS:
        if hour > args.hours:
            break
        rows[str(hour)] = {}
        for arm in ("baseline", "community"):
            state = advance_to(paths[arm], hour, candidate=True,
                               community_food=(arm == "community"))
            row = snapshot(paths[arm], state)
            rows[str(hour)][arm] = row
            (args.directory / "community_results.json").write_text(
                json.dumps(rows, indent=2, sort_keys=True), encoding="utf8")
            print("PLAY48_COMMUNITY_REAL " + json.dumps(
                {"arm": arm, **row}, sort_keys=True), flush=True)
        baseline, charity = rows[str(hour)]["baseline"], rows[str(hour)]["community"]
        delta = {key: charity[key] - baseline[key]
                 for key in ("hungry100", "bread", "meals", "cash_wages", "sales")}
        print("PLAY48_COMMUNITY_DELTA " + json.dumps(
            {"hour": hour, **delta, "community_rations": charity["community_rations"],
             "observational_only": True, "gate_passed": False}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
