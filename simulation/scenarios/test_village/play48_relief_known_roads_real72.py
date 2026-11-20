"""Only play the treatment branch: real owner-relief + destitute known-road search.

Official original 13-person starting ledger, 12 genuine copper, 3 starting food.
The change is only an autonomous desperate walk using personally known roads.
No teleport, omniscient access to food, new resources or source-ledger edits.
Control observations are already verified in PR160; this avoids rerunning control.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, seed, advance_to

STEPS = (24, 48, 60, 72)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--max-hour", type=int, choices=STEPS, default=72)
    args = p.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    path = args.evidence / "cashless_known_roads.sqlite"
    genesis = seed(path, candidate=True, community_food=True)
    assert len(genesis.npcs) == 13 and genesis.time == 0
    assert audit_npc_economy(genesis)["copper_known_total"] == 12
    assert sum(items.get("food", 0) for items in genesis.resources.values()) == 3
    rows = []
    for hour in STEPS:
        if hour > args.max_hour:
            break
        result = advance_to(path, hour, candidate=True, community_food=True)
        with SQLiteEventStore(path) as db:
            state = db.load(WORLD)
        assert audit_npc_economy(state)["copper_known_total"] == 12
        rations = state.market_stalls["market"]["community_food"]["payments"]
        row = {
            "hour": hour, "meals": result["meals"], "hungry100": result["starving"],
            "sales": result["sales"], "bread": result["bread"],
            "cash_wages": result["cash_wages"], "copper_total": 12,
            "market_owned_food": state.resources["market"]["food"],
            "market_open_quoted_food": sum(
                offer["remaining"] for offer in state.market_offers.values()
                if offer["status"] == "open"
                and offer["stock_owner_id"] == "market"
                and offer["resource"] == "food"),
            "charity_rations": len(rations),
            "charity_recipients": [r["recipient_id"] for r in rations],
            "hungry_npcs": [
                {"id": who, "hunger": r["hunger"], "site": r["site"],
                 "cash": r["cash"], "food": r["food"]}
                for who, r in sorted(result["npcs"].items())
                if r["hunger"] >= 95
            ],
            "observational_only": True,
            "release_gate_unchanged": True,
        }
        rows.append(row)
        (args.evidence / "real72.csv.json").write_text(json.dumps(rows, indent=2),
                                                       encoding="utf8")
        print("PLAY48_CASHLESS_ROADS_REAL " + json.dumps(row, sort_keys=True),
              flush=True)


if __name__ == "__main__":
    main()
