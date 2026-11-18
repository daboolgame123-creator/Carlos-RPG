"""PLAY48: actual original 13-NPC genesis through a full week, with NO gate waiver.

Runs physical control and candidate with the same start, roads, water, coins and
world engine. Reports all official checkpoints, including setbacks, even when
the legacy strict release gate would stop at h72. No scripts for free aid.
The economic engine remains active from hour zero in both scenarios.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import CHECKPOINTS, WORLD, seed, advance_to


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--hours", default=168, type=int, choices=CHECKPOINTS)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    for arm in ("control", "candidate"):
        path = args.directory / f"{arm}.sqlite"
        initial = seed(path, candidate=(arm == "candidate"))
        assert initial.time == 0 and len(initial.npcs) == 13
        assert audit_npc_economy(initial)["copper_known_total"] == 12
        assert sum(r.get("food", 0) for r in initial.resources.values()) == 3
        with SQLiteEventStore(path) as db:
            assert db.verify(WORLD).to_dict() == initial.to_dict()
    rows: dict[str, dict] = {}
    for hour in CHECKPOINTS:
        if hour > args.hours:
            break
        rows[str(hour)] = {}
        for arm in ("control", "candidate"):
            row = advance_to(
                args.directory / f"{arm}.sqlite",
                hour,
                candidate=(arm == "candidate"),
            )
            assert row["hour"] == hour and row["copper"] == 12
            rows[str(hour)][arm] = row
            (args.directory / "results.json").write_text(
                json.dumps(rows, indent=2, sort_keys=True), encoding="utf8"
            )
            print(
                "PLAY48_FULLGENESIS " + json.dumps({"arm": arm, **row}, sort_keys=True),
                flush=True,
            )
        baseline, candidate = rows[str(hour)]["control"], rows[str(hour)]["candidate"]
        relative = {
            "hour": hour,
            "original_control_hunger100": baseline["starving"],
            "candidate_hunger100": candidate["starving"],
            "candidate_better_starvation_than_control": (
                candidate["starving"] < baseline["starving"]
            ),
            "candidate_food_sales": candidate["sales"],
            "candidate_real_meals": candidate["meals"],
            "candidate_bakery_batches": candidate["bread"],
            "candidate_cash_wages": candidate["cash_wages"],
            "nora_real_meals": candidate["npcs"]["nora"]["meals"],
            "nora_real_purchases": candidate["npcs"]["nora"]["purchases"],
            "basim_real_meals": candidate["npcs"]["basim"]["meals"],
            "courier_deliveries": candidate["deliveries"],
            "physical_copper_conserved": baseline["copper"] == candidate["copper"] == 12,
            "observational_only": True,
            "strict_original_release_gates_not_waived": True,
        }
        print("PLAY48_FULLGENESIS_DIAGNOSIS " + json.dumps(relative, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
