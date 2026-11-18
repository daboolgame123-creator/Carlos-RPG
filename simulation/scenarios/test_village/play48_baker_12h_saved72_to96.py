"""Observe a changed baker wage cadence only on genuine persisted 72h events.

This is NOT a release gate and does not reset resources or force NPC behavior.
"""
from __future__ import annotations
import json
from pathlib import Path
from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, metrics, advance_to


def main() -> None:
    path = Path("evidence/candidate.sqlite")
    assert path.is_file(), "mandatory authentic saved72 candidate is missing"
    with SQLiteEventStore(path) as db:
        before = db.load(WORLD)
    assert before.time == 72 * HOUR and len(before.npcs) == 13
    assert audit_npc_economy(before)["copper_known_total"] == 12
    first = metrics(before)
    result = advance_to(path, 96, candidate=True)
    assert result["hour"] == 96 and result["copper"] == 12
    assert result["bread"] >= first["bread"]
    assert result["meals"] >= first["meals"]
    print("PLAY48_BAKER_12H_REAL_SAVED72_96 " + json.dumps({
        "before": {k: first[k] for k in ("hour", "starving", "bread", "meals", "sales", "cash_wages")},
        "after": {k: result[k] for k in ("hour", "starving", "bread", "meals", "sales", "cash_wages")},
        "basim": result["npcs"]["basim"], "copper_conserved": True,
        "historical_36h_candidate_96h": {"starving": 6, "bread": 43, "meals": 35},
        "observational_only": True, "release_gate_unchanged": True,
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
