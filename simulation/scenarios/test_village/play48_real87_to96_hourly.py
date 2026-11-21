"""Real original PLAY48 13-NPC persisted h87→96 endurance, hour by hour.

No reset, teleport, minted money, free bread or invisible market knowledge.
P0 and P1 advance from genuine verified saved87 physical event ledgers.
The only exogenous resource addition is identical pre-existing actual
FINITE 2-unit day-four rain at precisely h96, using the original authorized
water service and original source ID (not synthetic NPC charity).

This is observational and is NOT the 168h release acceptance gate.
Checkpoints permit an interrupted action to preserve real elapsed world time.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from play48_integrated_acceptance import WORLD, HOUR, engine, metrics, conserve_diverse

INPUT = Path("evidence/real87")
OUT = Path("real96")
OUT.mkdir(exist_ok=False)
ARMS = (("owner_relief_only", False), ("owner_relief_plus_roads", True))
histories = {}
for arm, _ in ARMS:
    original = INPUT / (arm + ".sqlite")
    assert original.is_file(), "immutable verified original h87 source missing: " + str(original)
    copy = OUT / (arm + ".sqlite")
    shutil.copyfile(original, copy)
    sha = hashlib.sha256(original.read_bytes()).hexdigest()
    assert hashlib.sha256(copy.read_bytes()).hexdigest() == sha
    with SQLiteEventStore(copy) as db:
        initial = db.load(WORLD)
        assert initial.time == 87 * HOUR and len(initial.npcs) == 13
        assert audit_npc_economy(initial)["copper_known_total"] == 12
    histories[arm] = {"source87_sha256":sha}

for hour in range(88,97):
    for arm, roads in ARMS:
        path = OUT / (arm + ".sqlite")
        with SQLiteEventStore(path) as db:
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                sim = engine(db, clock, reserve_trader_meal=True,
                             deferred_market_courier_wage=True)
                sim.merchant_food_wage_enabled = True
                sim.community_food_enabled = True
                sim.cashless_relief_walk_enabled = roads
                sim.deferred_bakery_grain_wage_enabled = True
                sim.integrated_livelihoods_enabled = True
                sim.remember_unbought_stalls_enabled = True
                start = db.load(WORLD)
                assert start.time == (hour-1)*HOUR and len(start.npcs) == 13
                result = sim.advance(
                    WORLD, seconds=HOUR,
                    command_id=f"real-hourly-advance:{hour*HOUR}",
                    expected_revision=start.revision,
                ).state
                assert result.time == hour * HOUR
                assert len(result.npcs) == 13
                conserve_diverse(result)
                if hour == 96:
                    # The project's original integrated acceptance runner
                    # records this same real, finite and attributed rain day 4.
                    result = FiniteWaterService(db, clock).record(
                        WORLD, "well", "fixed-external-rain-day4", 2,
                        command_id="real-attributed-source-day4",
                        expected_revision=result.revision,
                    ).state
                assert audit_npc_economy(result)["copper_known_total"] == 12
                db.snapshot(WORLD)
                assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                m = metrics(result)
                units = result.market_stalls["market"]["community_food"]["payments"]
                # Historical false market-return decisions have an exact,
                # formerly problematic event cause; legitimate new visited
                # routes must NOT be misclassified as fruitless shuttling.
                false_revisits = db.db.execute(
                    "SELECT COUNT(*) FROM events WHERE "
                    "json_extract(payload,'$.event_type')='NPCTravelStarted' "
                    "AND json_extract(payload,'$.time') > ? "
                    "AND json_extract(payload,'$.actor_id') IN ('miner','burner','smith') "
                    "AND json_extract(payload,'$.cause') LIKE "
                    "'cashless starving resident revisiting%' "
                    "AND json_extract(payload,'$.cause') NOT LIKE "
                    "'%personally witnessed food quote%'",
                    (87*HOUR,),
                ).fetchone()[0]
                assert false_revisits == 0, "old false food-market revisit recurred"
                row = {
                    "hour":hour,
                    "variant":arm,
                    "meals":m["meals"],"hungry100":m["starving"],
                    "sales":m["sales"],"bread":m["bread"],
                    "cash_wages":m["cash_wages"],
                    "market_owned_food":result.resources["market"]["food"],
                    "charity_rations":len(units),
                    "charity_recipients":[a["recipient_id"] for a in units],
                    "false_nonfood_market_revisit_legs_since87":false_revisits,
                    "copper":12,
                    "revision":result.revision,
                    "original_87_sha256":histories[arm]["source87_sha256"],
                    "observational_only":True,"release_gate_unchanged":True,
                }
                histories[arm][str(hour)] = row
                print("PLAY48_REAL87_TO96_HOURLY "+json.dumps(row,sort_keys=True),flush=True)
            finally:
                clock.close_session(WORLD)

    a, b = (histories[x][str(hour)] for x,_ in ARMS)
    print("PLAY48_REAL87_TO96_DELTA "+json.dumps({
        "hour":hour,
        "roads_minus_relief":{
            key:b[key]-a[key] for key in (
                "meals","hungry100","sales","bread","cash_wages","charity_rations")
        },
        "both_12_copper":True,
        "observational_only":True,
        "release_gate_unchanged":True,
    },sort_keys=True),flush=True)
    # Real hour-by-hour ledger copies remain available to the upload step
    # even if the next expensive hour is canceled or hits a time limit.
    (OUT/"hourly_comparison.json").write_text(
        json.dumps(histories,indent=2,sort_keys=True),encoding="utf8")
