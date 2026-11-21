"""PLAY48 original 13-NPC h96→168 test of work/market loop correction.

Never reset the simulation: start from *the verified unmodified original P1
h96 event ledger* (96h/12 copper/13 residents), change only the opt-in
cashless navigation planner and compare to authenticated original h168 P0/P1
checkpoint artifacts. New engine events follow normal reducer validation,
all finite rain is the pre-existing attributed 2 water at h120 and h144.
All results are EXPERIMENTAL; no production release gate changes.
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

initial=Path("evidence/saved96/owner_relief_plus_roads.sqlite")
history=Path("evidence/original168/checkpoints.json")
out=Path("workloop168")
out.mkdir(exist_ok=False)
assert initial.is_file() and history.is_file()
baseline=json.loads(history.read_text(encoding="utf8"))
original_sha=hashlib.sha256(initial.read_bytes()).hexdigest()
assert original_sha == baseline["owner_relief_plus_roads"]["source96_sha256"]
dest=out/"fixed_workloop.sqlite"
shutil.copyfile(initial,dest)
assert original_sha == hashlib.sha256(dest.read_bytes()).hexdigest()
with SQLiteEventStore(dest) as db:
    s=db.load(WORLD)
    assert s.time==96*HOUR and len(s.npcs)==13
    assert audit_npc_economy(s)["copper_known_total"]==12
history_rows={}
for hour in range(102,169,6):
    with SQLiteEventStore(dest) as db:
        clock=TimeEngine(db)
        clock.open_session(WORLD)
        try:
            s=db.load(WORLD)
            assert s.time==(hour-6)*HOUR
            sim=engine(db,clock,reserve_trader_meal=True,
                       deferred_market_courier_wage=True)
            sim.merchant_food_wage_enabled=True
            sim.community_food_enabled=True
            sim.cashless_relief_walk_enabled=True
            sim.deferred_bakery_grain_wage_enabled=True
            sim.integrated_livelihoods_enabled=True
            sim.remember_unbought_stalls_enabled=True
            new=sim.advance(
                WORLD,seconds=6*HOUR,
                command_id=f"fixed-work-loop-advance:{hour*HOUR}",
                expected_revision=s.revision,
            ).state
            assert new.time==hour*HOUR and len(new.npcs)==13
            conserve_diverse(new)
            if hour in (120,144):
                new=FiniteWaterService(db,clock).record(
                    WORLD,"well",f"fixed-external-rain-day{hour//24}",2,
                    command_id=f"real-attributed-source-day{hour//24}",
                    expected_revision=new.revision,
                ).state
            audit=audit_npc_economy(new)
            assert audit["copper_scope_complete"] and audit["copper_known_total"]==12
            db.snapshot(WORLD)
            assert db.db.execute("PRAGMA integrity_check").fetchone()==("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall()==[]
            m=metrics(new)
            food_revisit_legs=db.db.execute(
                "SELECT json_extract(payload,'$.actor_id'),"
                "json_extract(payload,'$.cause'),count(*) FROM events "
                "WHERE json_extract(payload,'$.time') > ? AND "
                "json_extract(payload,'$.event_type')='NPCTravelStarted' "
                "AND json_extract(payload,'$.actor_id') IN ('farid','nora') "
                "AND (json_extract(payload,'$.cause') LIKE "
                "'cashless starving resident revisiting%' OR "
                "json_extract(payload,'$.cause') LIKE "
                "'returning from physically visited market%') "
                "GROUP BY 1,2",
                (96*HOUR,)
            ).fetchall()
            row={
                "hour":hour,"meals":m["meals"],"hungry100":m["starving"],
                "sales":m["sales"],"bread":m["bread"],
                "cash_wages":m["cash_wages"],
                "rations":len(new.market_stalls["market"]["community_food"]["payments"]),
                "market_food":new.resources["market"]["food"],
                "copper":12,
                "farid_nora_market_work_trips_after96":[
                    {"npc":who,"cause":cause,"count":count}
                    for who,cause,count in food_revisit_legs
                ],
                "from_original_P1_96_sha256":original_sha,
                "revision":new.revision,
                "observational_only":True,"release_gate_unchanged":True,
            }
            history_rows[str(hour)]=row
            old_p1=baseline["owner_relief_plus_roads"][str(hour)]
            old_p0=baseline["owner_relief_only"][str(hour)]
            print("PLAY48_WORKLOOP_FIX_REAL "+json.dumps({
                **row,
                "vs_original_P1":{
                    key:row[key]-old_p1[other] for key,other in (
                        ("meals","meals"),("hungry100","hungry100"),
                        ("sales","sales"),("cash_wages","cash_wages"))
                },
                "original_P1":{
                    key:old_p1[key] for key in ("meals","hungry100","sales","cash_wages")
                },
                "original_P0":{
                    key:old_p0[key] for key in ("meals","hungry100","sales","cash_wages")
                },
            },sort_keys=True),flush=True)
        finally:
            clock.close_session(WORLD)
    (out/"comparisons.json").write_text(json.dumps(
        history_rows,indent=2,sort_keys=True),encoding="utf8")
    # Automatic artifact upload, even on timeout, preserves the exact
    # most recently completed physical checkpoint; no fake result on cancel.
