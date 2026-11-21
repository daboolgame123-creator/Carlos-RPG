"""Read-only inspection of automatically preserved partial P0/P1 96h run.
The old full continuation timed out. Never mutate, replay or reseed these ledgers.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, metrics

for arm in ("owner_relief_only", "owner_relief_plus_roads"):
    db_path = Path("evidence/partial96") / (arm + ".sqlite")
    if not db_path.is_file():
        print("PLAY48_PARTIAL_MISSING "+arm, flush=True)
        continue
    before = hashlib.sha256(db_path.read_bytes()).hexdigest()
    with SQLiteEventStore(db_path) as store:
        state = store.load(WORLD)
        assert store.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not store.db.execute("PRAGMA foreign_key_check").fetchall()
    assert hashlib.sha256(db_path.read_bytes()).hexdigest() == before
    audit = audit_npc_economy(state)
    assert len(state.npcs) == 13
    assert audit["copper_known_total"] == 12
    moves = sorted(state.travels.values(), key=lambda t: t["start"])
    recent = [t for t in moves if t["start"] >= state.time - 6 * HOUR]
    stats = {}
    for who,npc in sorted(state.npcs.items()):
        personal = [t for t in moves if t["npc_id"] == who]
        last_6h = [t for t in recent if t["npc_id"] == who]
        from_market = [t for t in personal if t["origin"] == "market"]
        to_market = [t for t in personal if t["destination"] == "market"]
        stats[who] = {
            "hunger": npc["needs"]["hunger"],
            "location": state.entities[who]["location_id"],
            "trips_total": len(personal),
            "trips_last6h": len(last_6h),
            "arrivals_at_market": len([t for t in to_market if t["status"]=="arrived"]),
            "departures_from_market": len(from_market),
            "charity": sum(p["recipient_id"] == who for p in
                           state.market_stalls["market"]["community_food"]["payments"]),
            "last5_destinations": [t["destination"] for t in personal[-5:]],
        }
    m = metrics(state)
    print("PLAY48_PARTIAL96_TRAVEL_AUDIT "+json.dumps({
        "arm": arm, "hour": state.time/HOUR, "revision":state.revision,
        "raw_sha256":before, "hunger100":m["starving"],"meals":m["meals"],
        "sales":m["sales"],"bread":m["bread"],
        "community":len(state.market_stalls["market"]["community_food"]["payments"]),
        "trip_total":len(moves),"trips_last6h":len(recent),
        "npcs":stats, "read_only":True, "copper":12,
    },sort_keys=True),flush=True)
