"""Continue authentic preserved h84 economic worlds for three hours.

No re-seed, no fabricated owner food/copper, no erased failed journeys:
P0 owner relief only; P1 the same relief with a stricter firsthand-food
road planner. The archived h84 SQLite histories are unchanged and hashed.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, advance_to, metrics

SOURCE = Path("evidence/partial96")
OUT = Path("fixed-route-87")
OUT.mkdir(exist_ok=False)
results = {}
for arm, seek in (("owner_relief_only", False), ("owner_relief_plus_roads", True)):
    original = SOURCE / (arm + ".sqlite")
    assert original.is_file(), f"missing genuine saved84 {arm}"
    target = OUT / (arm + ".sqlite")
    shutil.copyfile(original, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == hashlib.sha256(original.read_bytes()).hexdigest()
    with SQLiteEventStore(target) as db:
        start = db.load(WORLD)
    assert start.time == 84 * HOUR and len(start.npcs) == 13
    assert audit_npc_economy(start)["copper_known_total"] == 12
    trips_before = {who: sum(t["npc_id"] == who for t in start.travels.values())
                    for who in start.npcs}

    result = advance_to(target, 87, candidate=True, community_food=True,
                        cashless_relief_walk=seek)
    with SQLiteEventStore(target) as db:
        end = db.load(WORLD)
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert end.time == 87 * HOUR and len(end.npcs) == 13
    audit = audit_npc_economy(end)
    assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
    trip_delta = {who: sum(t["npc_id"] == who for t in end.travels.values()) - trips_before[who]
                  for who in end.npcs}
    row = {
        "arm": arm, "start": 84, "end": 87,
        "meals": result["meals"], "hungry100": result["starving"],
        "sales": result["sales"], "bread": result["bread"],
        "charity": len(end.market_stalls["market"]["community_food"]["payments"]),
        "cash_wages": result["cash_wages"],
        "copper": audit["copper_known_total"],
        "new_3h_trips": trip_delta,
        "new_useless_nonfood_market_trips": sum(trip_delta[w] for w in ("miner", "burner", "smith")),
        "original_84_file_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "observational_only": True, "release_gate_unchanged": True,
    }
    results[arm] = row
    (OUT/"result.json").write_text(json.dumps(results,indent=2,sort_keys=True),encoding="utf8")
    print("PLAY48_FIXED_ROUTE_REAL87 " + json.dumps(row, sort_keys=True), flush=True)

p0, p1 = results["owner_relief_only"], results["owner_relief_plus_roads"]
print("PLAY48_FIXED_ROUTE_87_DELTA " + json.dumps({
    key: p1[key] - p0[key] for key in ("meals","hungry100","sales","bread","charity")
},sort_keys=True),flush=True)
# The actual old P1 h78-to84 history recorded 1783 such path legs.
# Bounded, novel exploration of real roads is permitted; thousands of
# nonfood-shop revisits are never defensible food-seeking behavior.
assert p1["new_useless_nonfood_market_trips"] < 30, (
    "historical coal/ore/smithy food-market loop still active"
)
