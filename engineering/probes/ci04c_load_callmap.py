"""CI-04c: instrument real PLAY-47 6h SQLite loads and event replay call sites.

Research-only: monkeypatches class functions IN THIS TEST PROCESS ONLY, checks
canonical full-state plus SQLite event/command receipts against uninstrumented
run. No library, workflow release gate, or gameplay change.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

from carlos_sim import SQLiteEventStore
import carlos_sim.store as store_module
from test_play47_closure_endurance import _seed, _day, WORLD


def receipt_digest(path: Path) -> dict:
    with sqlite3.connect(path) as connection:
        return {
            table: connection.execute(
                "SELECT * FROM " + table + " ORDER BY rowid"
            ).fetchall()
            for table in ("worlds", "commands", "events", "snapshots")
        }


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="ci04c-loads-") as tmp:
        baseline = Path(tmp) / "original.sqlite"
        instrumented = Path(tmp) / "traced.sqlite"
        _seed(baseline)
        start = time.perf_counter()
        original_result = _day(baseline, 6 * 3600)
        baseline_elapsed = time.perf_counter() - start
        original_db_rows = receipt_digest(baseline)

        _seed(instrumented)
        original_load = SQLiteEventStore.load
        original_verify = SQLiteEventStore.verify
        original_apply = store_module.apply_event
        load_origins = Counter()
        load_modes = Counter()
        load_wall = Counter()
        counts = Counter()
        active = [0]

        def trace_load(self, world_id, *args, **kwargs):
            frame = sys._getframe(1)
            origin = frame.f_code.co_filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            caller = origin + ":" + frame.f_code.co_name
            use_snapshot = kwargs.get("use_snapshot", args[0] if args else True)
            began = time.perf_counter()
            counts["loads"] += 1
            load_origins[caller] += 1
            load_modes["snapshot" if use_snapshot else "full_genesis"] += 1
            active[0] += 1
            try:
                return original_load(self, world_id, *args, **kwargs)
            finally:
                active[0] -= 1
                load_wall[caller] += time.perf_counter() - began

        def trace_verify(self, world_id, *args, **kwargs):
            counts["verifications"] += 1
            return original_verify(self, world_id, *args, **kwargs)

        def trace_apply(*args, **kwargs):
            counts["replay_apply" if active[0] else "append_apply"] += 1
            return original_apply(*args, **kwargs)

        try:
            SQLiteEventStore.load = trace_load
            SQLiteEventStore.verify = trace_verify
            store_module.apply_event = trace_apply
            start = time.perf_counter()
            traced_result = _day(instrumented, 6 * 3600)
            traced_elapsed = time.perf_counter() - start
        finally:
            SQLiteEventStore.load = original_load
            SQLiteEventStore.verify = original_verify
            store_module.apply_event = original_apply

        assert original_result.to_dict() == traced_result.to_dict(), "instrumentation altered world"
        traced_db_rows = receipt_digest(instrumented)
        assert original_db_rows == traced_db_rows, "instrumentation altered receipts"
        assert counts["loads"] == sum(load_origins.values())
        assert counts["loads"] == sum(load_modes.values())
        assert counts["replay_apply"] > 0
        with SQLiteEventStore(instrumented) as reopened:
            assert reopened.verify(WORLD).to_dict() == original_result.to_dict()
            rows = reopened.db.execute(
                "SELECT count(*) FROM events WHERE world_id=?", (WORLD,)
            ).fetchone()[0]
        assert rows > 0
        top = [
            {"caller": call, "count": n, "inclusive_seconds": round(load_wall[call], 5)}
            for call, n in load_origins.most_common(15)
        ]
        print("CI04C_CALLMAP " + json.dumps({
            "world": WORLD,
            "simulated_seconds": 6 * 3600,
            "recorded_events": rows,
            "loads_total": counts["loads"],
            "load_modes": dict(load_modes),
            "verifications": counts["verifications"],
            "replay_apply_calls_in_store": counts["replay_apply"],
            "append_apply_calls_in_store": counts["append_apply"],
            "replay_calls_per_stored_event": round(counts["replay_apply"] / rows, 3),
            "top_callers": top,
            "baseline_wall_seconds": round(baseline_elapsed, 5),
            "instrumented_wall_seconds": round(traced_elapsed, 5),
            "event_receipts_identical": True,
            "world_state_identical": True,
            "production_engine_changed": False,
            "optimization_applied": False,
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    run()
