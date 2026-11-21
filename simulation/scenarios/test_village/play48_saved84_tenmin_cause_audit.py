"""Read original completed 10min P0/P1 event records, NO simulation.

Inspect the newly created miner/burner/smith NPCTravelStarted event causes
and actual origin->destination, not estimates from the caller's assumptions.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path

data = Path("evidence/short84")
records = json.loads((data/"comparison.json").read_text(encoding="utf8"))
for arm in ("owner_relief_only","owner_relief_plus_roads"):
    result = records[arm]
    src = data/(arm+".sqlite")
    assert src.exists()
    db = sqlite3.connect(f"file:{src.as_posix()}?mode=ro",uri=True)
    try:
        assert db.execute("PRAGMA integrity_check").fetchone()==("ok",)
        details = db.execute(
            "SELECT json_extract(payload,'$.actor_id'), "
            "json_extract(payload,'$.cause'), "
            "json_extract(payload,'$.data.origin'), "
            "json_extract(payload,'$.data.destination'), "
            "COUNT(*) FROM events WHERE seq > ? "
            "AND json_extract(payload,'$.event_type')='NPCTravelStarted' "
            "AND json_extract(payload,'$.actor_id') IN ('miner','burner','smith') "
            "GROUP BY 1,2,3,4 ORDER BY 1,2,3,4",
            (result["source84_revision"],)
        ).fetchall()
        samples=db.execute(
            "SELECT seq,json_extract(payload,'$.time'),"
            "json_extract(payload,'$.actor_id'),json_extract(payload,'$.cause'),"
            "json_extract(payload,'$.data.origin'),json_extract(payload,'$.data.destination') "
            "FROM events WHERE seq > ? "
            "AND json_extract(payload,'$.event_type')='NPCTravelStarted' "
            "AND json_extract(payload,'$.actor_id') IN ('miner','burner','smith') "
            "ORDER BY seq LIMIT 25",
            (result["source84_revision"],)
        ).fetchall()
    finally:
        db.close()
    total=sum(row[-1] for row in details)
    assert total==result["nonfood_shop_NPC_trips"], (arm,total,result["nonfood_shop_NPC_trips"])
    print("PLAY48_REAL10MIN_TRIP_CAUSES " + json.dumps({
        "arm":arm,"time_from":84,"minutes":10,"travel_events":total,
        "grouped": [{"npc":w,"cause":c,"origin":a,"destination":b,"count":n}
                    for w,c,a,b,n in details],
        "sample": [{"seq":seq,"time":t,"npc":who,"cause":cause,
                    "origin":a,"destination":b} for seq,t,who,cause,a,b in samples],
        "read_only": True,
    },sort_keys=True),flush=True)
