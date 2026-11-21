"""Fast, controlled h84-to-h84+10-minute real-world diagnostic, no re-seeding.

Use preserved authentic h84 P0 and P1 event ledgers from historical test.
Do not re-run expensive full-genesis verification here; this is a short
observational probe, NOT a release gate. Verify the stored SQLite structure,
the physically persisted timeline and real 12 copper in both cases.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics

INPUT = Path("evidence/real84")
OUT = Path("short84")
OUT.mkdir(exist_ok=False)
MINUTES = 10
results = {}
for arm, use_roads in (("owner_relief_only", False), ("owner_relief_plus_roads", True)):
    original = INPUT / f"{arm}.sqlite"
    assert original.is_file(), f"genuine saved84 source missing for {arm}"
    dest = OUT / f"{arm}.sqlite"
    shutil.copyfile(original, dest)
    original_sha = hashlib.sha256(original.read_bytes()).hexdigest()
    assert original_sha == hashlib.sha256(dest.read_bytes()).hexdigest()

    with SQLiteEventStore(dest) as db:
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        before = db.load(WORLD)
        assert before.time == 84 * HOUR and len(before.npcs) == 13
        assert audit_npc_economy(before)["copper_known_total"] == 12
        before_count = {who: sum(t["npc_id"] == who for t in before.travels.values())
                        for who in before.npcs}
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            sim = engine(db, clock, reserve_trader_meal=True,
                         deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled = True
            sim.community_food_enabled = True
            sim.cashless_relief_walk_enabled = use_roads
            sim.deferred_bakery_grain_wage_enabled = True
            sim.integrated_livelihoods_enabled = True
            sim.remember_unbought_stalls_enabled = True

            after = sim.advance(
                WORLD, seconds=MINUTES * 60,
                command_id=f"real84-safely-bounded-{MINUTES}min",
                expected_revision=before.revision,
            ).state
            assert after.time == 84 * HOUR + MINUTES * 60
            assert len(after.npcs) == 13
            audit = audit_npc_economy(after)
            assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            trip_delta = {
                who: sum(t["npc_id"] == who for t in after.travels.values()) - before_count[who]
                for who in before.npcs
            }
            # The number of physical legs is NOT the number of pointless
            # visits. Distinguish first-time searches from false referrals
            # to a nonfood-only stall, using authoritative event causes.
            studied = {"miner", "burner", "smith"}
            causes = db.db.execute(
                "SELECT json_extract(payload,'$.actor_id'), "
                "json_extract(payload,'$.cause') FROM events "
                "WHERE seq > ? AND json_extract(payload,'$.event_type') = "
                "'NPCTravelStarted' AND "
                "json_extract(payload,'$.actor_id') IN ('miner','burner','smith')",
                (before.revision,),
            ).fetchall()
            assert len(causes) == sum(trip_delta[who] for who in studied)
            false_revisits = [
                (who, cause) for who, cause in causes
                if cause.startswith("cashless starving resident revisiting")
                and "personally witnessed food quote" not in cause
            ]
            explore_legs = sum(
                "cashless starving resident searching known roads" in cause
                for who, cause in causes
            )
            measure = metrics(after)
            ration = after.market_stalls["market"]["community_food"]["payments"]
            results[arm] = {
                "start": 84, "minutes": MINUTES, "time": after.time / HOUR,
                "meals": measure["meals"], "hungry100": measure["starving"],
                "sales": measure["sales"], "bread": measure["bread"],
                "actual_rations": len(ration),
                "copper": audit["copper_known_total"],
                "trips_new": trip_delta,
                "nonfood_shop_NPC_trips": sum(trip_delta[w] for w in ("miner","burner","smith")),
                "firsthand_known_road_exploration_legs": explore_legs,
                "unwitnessed_nonfood_market_return_legs": len(false_revisits),
                "source84_sha256": original_sha,
                "source84_revision": before.revision, "after_revision": after.revision,
                "observational_only": True, "release_gate_unchanged": True,
            }
            print("PLAY48_SHORT84_REAL " + json.dumps({
                "arm": arm, **results[arm]
            }, sort_keys=True), flush=True)
        finally:
            clock.close_session(WORLD)
    (OUT / "comparison.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf8")

a,b = results["owner_relief_only"], results["owner_relief_plus_roads"]
print("PLAY48_SHORT84_DELTA " + json.dumps({
    key: b[key] - a[key] for key in ("meals", "hungry100", "sales", "nonfood_shop_NPC_trips")
}, sort_keys=True),flush=True)
# Historically there were 3,573 repeated, unproductive food-market
# "revisits". Do NOT mistake one-off real exploration of new known-road
# endpoints for those old loops. Every actual transfer remains conserved.
assert b["unwitnessed_nonfood_market_return_legs"] == 0, (
    "old nonfood market revisit behavior unexpectedly persisted"
)
assert b["firsthand_known_road_exploration_legs"] <= b["nonfood_shop_NPC_trips"]
assert a["copper"] == b["copper"] == 12
