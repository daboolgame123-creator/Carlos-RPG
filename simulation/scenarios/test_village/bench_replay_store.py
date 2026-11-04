"""Measure SQLite full-replay query count without hardware timing assertions.

Run this identical script with PYTHONPATH pointed at a reviewed baseline and
at the candidate source to compare like-for-like implementation behavior.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

from carlos_sim import DomainEvent, SQLiteEventStore


def measure(event_count: int) -> dict:
    if type(event_count) is not int or event_count < 1:
        raise ValueError("positive event_count required")
    with TemporaryDirectory() as tmp, SQLiteEventStore(Path(tmp) / "replay.sqlite") as store:
        store.create_world("benchmark")
        batch = [
            DomainEvent("LocationCreated", None, "benchmark setup", 0,
                        {"id": f"site-{i:05d}", "name": f"Site {i}"})
            for i in range(event_count)
        ]
        store.append("benchmark", "bootstrap", 0, batch, bootstrap=True)
        timings: list[float] = []
        select_count = None
        for _ in range(3):
            statements: list[str] = []
            store.db.set_trace_callback(statements.append)
            try:
                start = perf_counter()
                state = store.load("benchmark", use_snapshot=False)
                timings.append(perf_counter() - start)
            finally:
                store.db.set_trace_callback(None)
            assert state.revision == event_count
            selects = sum(s.lstrip().upper().startswith("SELECT ") for s in statements)
            if select_count is None:
                select_count = selects
            else:
                assert select_count == selects
        return {
            "events": event_count,
            "select_statements": select_count,
            "median_full_replay_seconds": round(median(timings), 6),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--counts", nargs="+", type=int, default=[10, 50, 100])
    args = parser.parse_args()
    print(json.dumps([measure(count) for count in args.counts], sort_keys=True))


if __name__ == "__main__":
    main()
