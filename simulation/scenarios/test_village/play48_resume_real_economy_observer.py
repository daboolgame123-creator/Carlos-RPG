"""Diagnostic continuation of a REAL, already persisted PLAY48 village.

Does not rewrite the acceptance gate, alter physical state, invent resources,
or declare the economy approved. Both arms resume from identical-hour saved
SQLite event-ledgers produced by the original-13-NPC 72h experiment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, advance_to


def observe(directory: Path, start: int, end: int) -> dict:
    assert (start, end) in ((72, 96), (96, 168))
    report = directory / "results.json"
    rows = json.loads(report.read_text(encoding="utf-8"))
    assert str(start) in rows and all(
        arm in rows[str(start)] for arm in ("control", "candidate")
    ), "provenance requires both original recorded arms"
    for arm in ("control", "candidate"):
        world = directory / (arm + ".sqlite")
        with SQLiteEventStore(world) as db:
            previous = db.verify(WORLD)
            assert previous.time == start * HOUR, (
                f"not the required real {start}h persisted world: {arm}"
            )
            assert len(previous.npcs) == 13
            assert audit_npc_economy(previous)["copper_known_total"] == 12
            assert rows[str(start)][arm]["copper"] == 12
        measured = advance_to(world, end, candidate=(arm == "candidate"))
        assert measured["copper"] == 12
        rows.setdefault(str(end), {})[arm] = measured
        report.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(
            "PLAY48_OBSERVED "
            + json.dumps({"arm": arm, **measured}, sort_keys=True),
            flush=True,
        )
    old, new = rows[str(end)]["control"], rows[str(end)]["candidate"]
    last = rows[str(start)]["candidate"]
    decision = {
        "hour": end,
        "this_is_not_a_release_gate": True,
        "candidate_still_less_starved_than_control": new["starving"] < old["starving"],
        "nora_real_food_advantage": new["npcs"]["nora"]["meals"] > old["npcs"]["nora"]["meals"]
        and new["npcs"]["nora"]["purchases"] > old["npcs"]["nora"]["purchases"],
        "cash_wage_advantage": new["cash_wages"] > old["cash_wages"],
        "meals_grew_since_previous": new["meals"] > last["meals"],
        "sales_grew_since_previous": new["sales"] > last["sales"],
        "bakery_grew_since_previous": new["bread"] > last["bread"],
        "huda_deliveries_grew": new["deliveries"]["huda"] > last["deliveries"]["huda"],
        "hana_deliveries_grew": new["deliveries"]["hana"] > last["deliveries"]["hana"],
        "copper_kept": new["copper"] == old["copper"] == 12,
    }
    print("PLAY48_DIAGNOSIS " + json.dumps(decision, sort_keys=True), flush=True)
    return decision


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--end", required=True, type=int)
    args = parser.parse_args()
    observe(args.directory, args.start, args.end)
