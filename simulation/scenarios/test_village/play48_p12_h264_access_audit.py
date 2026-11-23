"""PLAY48 P12: read-only diagnosis of the genuine P11 saved h264 economy.

Never runs inside an NPC decision, never changes money, needs, food, quotes,
contract terms or the source SQLite saves. Operator-only barrier audit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

from carlos_sim.domain import WorldState
from carlos_sim.community_food import (
    _eligible, choose_market_ration, signed_local_relief_quote_capacity,
)
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.food_for_work import _available_site_food

DAY = 86400
H264 = 264 * 3600
ROOT = Path("evidence/p12_real264")
OUTPUT = Path("play48_p12_h264_access_audit.json")


def audit_one(name: str) -> dict:
    candidates = list(ROOT.rglob(name + ".sqlite"))
    if len(candidates) != 1:
        raise ValueError(f"exactly one authentic {name} ledger required: {candidates}")
    file = candidates[0]
    initial_sha = hashlib.sha256(file.read_bytes()).hexdigest()
    with sqlite3.connect(f"file:{file.resolve().as_posix()}?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        world = db.execute(
            "SELECT id,revision,sim_time,schema_version,rules_version FROM worlds"
        ).fetchone()
        assert world is not None and world[2] == H264
        row = db.execute(
            "SELECT state FROM snapshots ORDER BY revision DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        raw = json.loads(row[0])
    assert hashlib.sha256(file.read_bytes()).hexdigest() == initial_sha, (
        "the genuine saved-world ledger was mutated during the audit"
    )
    state = WorldState.from_dict(raw)
    assert state.time == H264 and len(state.npcs) == 13
    assert state.revision == world[1]
    food_access = audit_food_access_barriers(state)
    today = state.time // DAY
    stall = state.market_stalls["market"]
    relief = stall["community_food"]
    payments_today = [
        p for p in relief["payments"] if p["paid_at"] // DAY == today
    ]
    bakery = state.resources["bakery"]
    market = state.resources["market"]
    food_quotes = [
        {"offer_id": ident, "remaining": o["remaining"],
         "unit_price": o["unit_price"], "posted_at": o["posted_at"]}
        for ident, o in sorted(state.market_offers.items())
        if (o["status"] == "open" and o["site_id"] == "market"
            and o["stock_owner_id"] == "market" and o["resource"] == "food")
    ]
    last_bread_job = max(
        (j["finished_at"] for j in state.production_jobs.values()
         if j["status"] == "completed"
         and j["recipe_id"] == "grain-to-bread"),
        default=None,
    )
    people = []
    for row in food_access["actors"]:
        who = row["npc_id"]
        person = state.npcs[who]
        goods = state.resources.get(who, {})
        loc = state.entities[who]["location_id"]
        people.append({
            "id": who, "role": person["role"], "location": loc,
            "hunger": person["needs"]["hunger"],
            "personal_food": goods.get("food", 0),
            "personal_copper": goods.get("coin_copper", 0),
            "locally_affordable_now": row["locally_affordable_now"],
            "at_market": row["at_market"],
            "physically_idle": row["physically_idle"],
            "eligible_for_signed_relief_at_this_tick": _eligible(raw, who),
            "known_road_to_market": row["known_road_path_to_market"],
        })
    hungry = [x["id"] for x in people if x["hunger"] == 100]
    report = {
        "arm": name, "source_sha256": initial_sha, "time": state.time,
        "world_id": state.world_id, "revision": state.revision,
        "npc_count": len(people), "hungry100": hungry,
        "market_owned_bread": market.get("food", 0),
        "unquoted_unreserved_market_bread": _available_site_food(state, "market"),
        "food_quotes": food_quotes,
        "relief_daily_cap": relief["daily_limit"],
        "relief_used_today": len(payments_today),
        "relief_recipients_today": [p["recipient_id"] for p in payments_today],
        "next_signed_local_ration_candidate": choose_market_ration(state),
        "owner_relievable_quote_capacity": signed_local_relief_quote_capacity(state),
        "bakery_grain": bakery.get("grain", 0),
        "bakery_oven": bakery.get("oven", 0),
        "bakery_owned_food": bakery.get("food", 0),
        "last_real_bread_finished_at": last_bread_job,
        "hours_since_last_bread": (
            round((state.time - last_bread_job) / 3600, 3)
            if last_bread_job is not None else None
        ),
        "population": people,
        "cash_known_total": sum(
            x.get("coin_copper", 0) for x in state.resources.values()),
    }
    assert report["cash_known_total"] == 12
    assert report["market_owned_bread"] >= report[
        "unquoted_unreserved_market_bread"] >= 0
    assert report["relief_used_today"] <= report["relief_daily_cap"]
    print("PLAY48_P12_AUTHENTIC_H264 " + json.dumps({
        k: v for k, v in report.items() if k != "population"
    }, sort_keys=True), flush=True)
    for person in people:
        if person["hunger"] >= 90:
            print("PLAY48_P12_HUNGRY_ACTOR " + json.dumps(
                {"arm": name, **person}, sort_keys=True), flush=True)
    return report


def main() -> None:
    baseline = audit_one("P10_rescue_only")
    candidate = audit_one("P11_real_wage")
    assert baseline["npc_count"] == candidate["npc_count"] == 13
    assert baseline["cash_known_total"] == candidate["cash_known_total"] == 12
    assert len(candidate["hungry100"]) < len(baseline["hungry100"])
    assert candidate["market_owned_bread"] > 0
    assert candidate["bakery_grain"] > 0
    assert candidate["last_real_bread_finished_at"] is not None
    result = {"control": baseline, "candidate": candidate,
              "gate": "P12_DIAGNOSTIC_ONLY / PLAY48_NO_GO"}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2,
                                 sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
