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
from carlos_sim.market_navigation import choose_known_market_walk

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
        causes = store.db.execute(
        "SELECT json_extract(payload, '$.actor_id'), "
        "json_extract(payload, '$.cause'), count(*) FROM events "
        "WHERE json_extract(payload, '$.event_type') = 'NPCTravelStarted' "
        "AND json_extract(payload, '$.time') >= ? "
        "GROUP BY 1, 2 ORDER BY count(*) DESC LIMIT 20",
            (72 * HOUR,),
        ).fetchall()
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
    # Exercise P1 planner at the real saved84 checkpoint without advancing
    # even a single simulated second. All knowledge comes from each NPC's
    # personal travel/offer history, not the inspector's market inventory.
    candidate_revisits = {}
    for who in ("miner", "burner", "smith", "adel", "repairman"):
        if state.resources.get(who, {}).get("coin_copper") != 0:
            continue
        walk = choose_known_market_walk(
            state, who, repeat_errands=True,
            remember_unbought_stalls=True,
            seek_alternative_if_unaffordable=True,
            seek_relief=True,
        )
        candidate_revisits[who] = (
            {"destination": walk.destination, "route": walk.route_id,
             "reason": walk.reason} if walk else None
        )
    for who in ("miner", "burner", "smith"):
        step = candidate_revisits.get(who)
        assert step is None or "personally witnessed food quote" not in step["reason"] or (
            step["destination"] not in ("smithy", "charcoal_kiln", "iron_mine")
        ), f"false food return intent for {who} at {step}"
    m = metrics(state)
    print("PLAY48_PARTIAL96_TRAVEL_AUDIT "+json.dumps({
        "arm": arm, "hour": state.time/HOUR, "revision":state.revision,
        "raw_sha256":before, "hunger100":m["starving"],"meals":m["meals"],
        "sales":m["sales"],"bread":m["bread"],
        "community":len(state.market_stalls["market"]["community_food"]["payments"]),
        "trip_total":len(moves),"trips_last6h":len(recent),
        "travel_causes_since72": [{"npc":who,"cause":why,"trips":n} for who,why,n in causes],
        "real84_p1_next_market_intents": candidate_revisits,
        "npcs":stats, "read_only":True, "copper":12,
    },sort_keys=True),flush=True)
