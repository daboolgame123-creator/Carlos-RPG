"""PLAY48 original independent 13-NPC genuine persisted 96→168h endurance.

Both worlds originated from the same genuine time-zero 12 copper and 3 food
with no teleport, unlimited institution budget, fabricated wages or meals.
P0 is owner-funded market help; P1 adds cashless firsthand-known-road help.
Read the immutable signed world ledgers saved at genuine 96h, persist every
six simulated hours, and keep 12 copper conserved with full SQLite integrity.

The original external finite water contribution is made at 120 and 144h,
exactly as original integrated acceptance; not at final 168h boundary.
Treat results as *observation*, never declare release just for completion.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from play48_integrated_acceptance import (
    WORLD, HOUR, engine, metrics, conserve_diverse
)

ROOT = Path("evidence/saved96")
OUT = Path("real168")
OUT.mkdir(exist_ok=False)
ARMS = (("owner_relief_only", False), ("owner_relief_plus_roads", True))
rows = {}
for arm, _ in ARMS:
    original = ROOT / (arm + ".sqlite")
    assert original.is_file(), f"immutable genuine h96 history missing: {original}"
    dest = OUT / (arm + ".sqlite")
    shutil.copyfile(original, dest)
    original_sha = hashlib.sha256(original.read_bytes()).hexdigest()
    assert original_sha == hashlib.sha256(dest.read_bytes()).hexdigest()
    with SQLiteEventStore(dest) as db:
        s = db.load(WORLD)
        assert s.time == 96 * HOUR and len(s.npcs) == 13
        econ = audit_npc_economy(s)
        assert econ["copper_scope_complete"] and econ["copper_known_total"] == 12
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
        initial = metrics(s)
        assert initial["hour"] == 96
    rows[arm] = {
        "source96_sha256": original_sha,
        "initial96": {
            "hour": 96,
            "meals": initial["meals"],
            "hungry100": initial["starving"],
            "sales": initial["sales"],
            "bread": initial["bread"],
            "cash_wages": initial["cash_wages"],
            "copper": 12,
        },
    }
    print("PLAY48_REAL168_ORIGINAL96 " + json.dumps({
        "variant":arm,"sha256":original_sha,
        **rows[arm]["initial96"],
    },sort_keys=True),flush=True)

for hour in range(102, 169, 6):
    for arm, known_roads in ARMS:
        filename = OUT / (arm + ".sqlite")
        with SQLiteEventStore(filename) as db:
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                sim = engine(db, clock, reserve_trader_meal=True,
                             deferred_market_courier_wage=True)
                sim.merchant_food_wage_enabled = True
                sim.community_food_enabled = True
                sim.cashless_relief_walk_enabled = known_roads
                sim.deferred_bakery_grain_wage_enabled = True
                sim.integrated_livelihoods_enabled = True
                sim.remember_unbought_stalls_enabled = True
                previous = db.load(WORLD)
                assert previous.time == (hour-6)*HOUR and len(previous.npcs) == 13
                s = sim.advance(
                    WORLD, seconds=6*HOUR,
                    command_id=f"original-continuation-to:{hour*HOUR}",
                    expected_revision=previous.revision,
                ).state
                assert s.time == hour*HOUR and len(s.npcs) == 13
                conserve_diverse(s)

                if hour in (120,144):
                    day=hour//24
                    s=FiniteWaterService(db, clock).record(
                        WORLD, "well", f"fixed-external-rain-day{day}", 2,
                        command_id=f"real-attributed-source-day{day}",
                        expected_revision=s.revision,
                    ).state

                audit = audit_npc_economy(s)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                db.snapshot(WORLD)
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert not db.db.execute("PRAGMA foreign_key_check").fetchall()
                m = metrics(s)
                charity=s.market_stalls["market"]["community_food"]["payments"]
                false_food_returns=db.db.execute(
                    "SELECT count(*) FROM events WHERE "
                    "json_extract(payload,'$.event_type')='NPCTravelStarted' "
                    "AND json_extract(payload,'$.time') > ? "
                    "AND json_extract(payload,'$.actor_id') IN ('miner','burner','smith') "
                    "AND json_extract(payload,'$.cause') LIKE "
                    "'cashless starving resident revisiting%' "
                    "AND json_extract(payload,'$.cause') NOT LIKE "
                    "'%personally witnessed food quote%'",
                    (96*HOUR,)
                ).fetchone()[0]
                assert false_food_returns == 0, "spurious nonfood market revisit"

                result = {
                    "hour":hour, "variant":arm,
                    "meals":m["meals"],
                    "hungry100":m["starving"],
                    "sales":m["sales"],
                    "bread":m["bread"],
                    "cash_wages":m["cash_wages"],
                    "charity_rations":len(charity),
                    "charity_recipients":[x["recipient_id"] for x in charity],
                    "market_owned_food":s.resources["market"]["food"],
                    "copper":12,
                    "false_nonfood_market_revisits_since96":false_food_returns,
                    "source96_sha256":rows[arm]["source96_sha256"],
                    "revision":s.revision,
                    "observational_only":True,
                    "release_gate_unchanged":True,
                }
                rows[arm][str(hour)] = result
                print("PLAY48_REAL168_SIX_HOURLY "+json.dumps(
                    result,sort_keys=True),flush=True)
            finally:
                clock.close_session(WORLD)

    a,b=(rows[arm][str(hour)] for arm,_ in ARMS)
    delta={key:b[key]-a[key] for key in (
        "meals","hungry100","sales","bread","cash_wages","charity_rations"
    )}
    print("PLAY48_REAL168_DELTA "+json.dumps({
        "hour":hour,"roads_minus_owner_relief":delta,
        "both_copper_12":True,
        "observational_only":True,
        "release_gate_unchanged":True,
    },sort_keys=True),flush=True)
    (OUT/"checkpoints.json").write_text(
        json.dumps(rows,sort_keys=True,indent=2),encoding="utf8")
