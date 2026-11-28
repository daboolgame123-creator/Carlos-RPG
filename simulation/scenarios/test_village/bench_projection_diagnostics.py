"""Opt-in component timings for world projection, validation and replay.

This diagnostic reuses the realistic finite-world benchmark, installs temporary
in-process timing wrappers, and restores every wrapped callable on exit. The
instrumented durations include wrapper overhead and are for locating costs,
not capacity claims or comparison with uninstrumented wall-clock results.

Run from ``simulation`` with::

    PYTHONPATH=src python scenarios/test_village/bench_projection_diagnostics.py

No timing threshold is a test or CI gate. The reused benchmark still verifies
repeatable event/state digests, replay, snapshots, SQLite integrity, and resource
conservation for each sample.
"""
from __future__ import annotations

import argparse
import functools
import importlib
import json
import platform
import statistics
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Callable, Iterator

import bench_realistic_world_scale as benchmark
from carlos_sim.domain import WorldState
from carlos_sim.living_world import LivingWorldEngine
from carlos_sim.store import SQLiteEventStore


# These are the validators called directly by WorldState._decode_checked.
# A runtime check below makes this list fail closed if that contract changes.
VALIDATORS = (
    ("npc", "validate_npc_state"),
    ("actions", "validate_actions"),
    ("movement", "validate_movement"),
    ("movement", "validate_player_schedules"),
    ("player_foraging", "validate_player_forage_schedules"),
    ("player_needs", "validate_player_needs"),
    ("player_needs", "validate_player_rest_schedules"),
    ("navigation", "validate_navigation"),
    ("social", "validate_social"),
    ("rumors", "validate_rumors"),
    ("assistance", "validate_obligations"),
    ("consumption", "validate_consumptions"),
    ("survival", "validate_survival_progress"),
    ("gathering", "validate_gatherings"),
    ("foraging", "validate_foraging_attempts"),
    ("environment", "validate_environment_cycles"),
    ("agriculture", "validate_farm_plots"),
    ("supply", "validate_supply_circuits"),
    ("courier_provisions", "validate_courier_provisions"),
    ("hydrology", "validate_sources"),
    ("production", "validate_production_state"),
    ("market", "validate_market"),
    ("property", "validate_takings"),
    ("property_evidence", "validate_property_evidence"),
    ("local_institutions", "validate_institutions"),
    ("complaints", "validate_complaints"),
    ("rights", "validate_origins"),
    ("custody", "validate_lots"),
    ("rights_permissions", "validate_permissions"),
    ("registered_claims", "validate_claims"),
    ("loans", "validate_loans"),
    ("temperament", "validate_temperaments"),
    ("routines", "validate_routines"),
    ("rpg_state", "validate_rpg_profiles"),
    ("player_quests", "validate_player_quests"),
    ("injury_events", "validate_injury_state"),
    ("recovery_events", "validate_treatment_state"),
)


class Timings:
    def __init__(self) -> None:
        self.phase = "setup"
        self.stack: list[dict[str, int]] = []
        self.records: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)

    def wrap(self, name: str, function: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(function)
        def measured(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter_ns()
            frame = {"children_ns": 0}
            self.stack.append(frame)
            try:
                return function(*args, **kwargs)
            finally:
                elapsed = time.perf_counter_ns() - started
                self.stack.pop()
                exclusive = max(0, elapsed - frame["children_ns"])
                bucket = self.records[self.phase].setdefault(
                    name, {"calls": 0, "inclusive_ns": 0, "exclusive_ns": 0},
                )
                bucket["calls"] += 1
                bucket["inclusive_ns"] += elapsed
                bucket["exclusive_ns"] += exclusive
                if self.stack:
                    self.stack[-1]["children_ns"] += elapsed
        return measured

    @contextmanager
    def in_phase(self, name: str) -> Iterator[None]:
        previous = self.phase
        self.phase = name
        try:
            yield
        finally:
            self.phase = previous

    def output(self) -> dict[str, dict[str, dict[str, int]]]:
        return {
            phase: {name: dict(values) for name, values in sorted(rows.items())}
            for phase, rows in sorted(self.records.items())
        }


@contextmanager
def instrument(timings: Timings) -> Iterator[None]:
    """Patch only this process temporarily; always restore exact originals."""
    patches: list[tuple[Any, str, Any]] = []

    def patch(owner: Any, attribute: str, replacement: Any) -> None:
        original = getattr(owner, attribute)
        patches.append((owner, attribute, original))
        setattr(owner, attribute, replacement)

    def phase_wrapper(name: str, function: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(function)
        def measured(self: Any, *args: Any, **kwargs: Any) -> Any:
            with timings.in_phase(name):
                return function(self, *args, **kwargs)
        return measured

    expected = {
        name for name in WorldState._decode_checked.__func__.__code__.co_names
        if name.startswith("validate_")
    }
    declared = {function for _, function in VALIDATORS}
    if declared != expected:
        raise RuntimeError(
            "validator timing map is stale: "
            f"missing={sorted(expected - declared)}, extra={sorted(declared - expected)}"
        )

    try:
        patch(WorldState, "to_dict", timings.wrap("WorldState.to_dict", WorldState.to_dict))
        original_decode = WorldState.__dict__["_decode_checked"]
        decode_function = original_decode.__func__
        timed_decode = timings.wrap("WorldState._decode_checked", decode_function)

        @functools.wraps(decode_function)
        def measured_decode(cls: type[WorldState], *args: Any, **kwargs: Any) -> WorldState:
            return timed_decode(cls, *args, **kwargs)

        # Preserve the descriptor so classmethod binding and the contract stay intact.
        patches.append((WorldState, "_decode_checked", original_decode))
        setattr(WorldState, "_decode_checked", classmethod(measured_decode))

        for module_name, function_name in VALIDATORS:
            module = importlib.import_module(f"carlos_sim.{module_name}")
            patch(module, function_name, timings.wrap(
                f"validator.{function_name}", getattr(module, function_name),
            ))

        from carlos_sim import custody
        patch(custody, "reconcile_lots", timings.wrap(
            "custody.reconcile_lots", custody.reconcile_lots,
        ))
        patch(LivingWorldEngine, "advance", phase_wrapper(
            "advance", LivingWorldEngine.advance,
        ))
        patch(SQLiteEventStore, "snapshot", phase_wrapper(
            "snapshot", SQLiteEventStore.snapshot,
        ))
        patch(SQLiteEventStore, "verify", phase_wrapper(
            "full_replay", SQLiteEventStore.verify,
        ))
        yield
    finally:
        for owner, attribute, original in reversed(patches):
            setattr(owner, attribute, original)


def _seconds(nanoseconds: int) -> float:
    return round(nanoseconds / 1_000_000_000, 6)


def summarize(metrics: dict[str, dict[str, dict[str, int]]], repeats: int) -> dict:
    phases: dict[str, dict] = {}
    validator_names = {f"validator.{name}" for _, name in VALIDATORS}
    for phase in ("advance", "snapshot", "full_replay"):
        rows = metrics.get(phase, {})
        validators = {
            name: values for name, values in rows.items()
            if name in validator_names
        }
        validator_exclusive = sum(row["exclusive_ns"] for row in validators.values())
        decode = rows.get("WorldState._decode_checked", {
            "calls": 0, "inclusive_ns": 0, "exclusive_ns": 0,
        })
        phases[phase] = {
            "worldstate_to_dict": rows.get("WorldState.to_dict", {
                "calls": 0, "inclusive_ns": 0, "exclusive_ns": 0,
            }),
            "decode_checked": decode,
            "validator_exclusive_total_ns": validator_exclusive,
            "decode_unattributed_ns": max(0, decode["inclusive_ns"] - validator_exclusive),
            "validators": validators,
            "custody_reconcile": rows.get("custody.reconcile_lots", {
                "calls": 0, "inclusive_ns": 0, "exclusive_ns": 0,
            }),
        }
        phases[phase]["custody_reconcile_status"] = (
            "measured" if phases[phase]["custody_reconcile"]["calls"]
            else "inactive_in_benchmark_no_tracked_lots"
        )

    # Convert per-sample nanosecond counters to medians. Call counts must agree
    # across identical samples; timings intentionally have no pass threshold.
    result: dict[str, dict] = {}
    for phase, stage in phases.items():
        names = set(stage["validators"])
        names.update(("WorldState.to_dict", "WorldState._decode_checked",
                      "custody.reconcile_lots"))
        output_rows = {}
        for name in sorted(names):
            if name == "WorldState.to_dict":
                row = stage["worldstate_to_dict"]
            elif name == "WorldState._decode_checked":
                row = stage["decode_checked"]
            elif name == "custody.reconcile_lots":
                row = stage["custody_reconcile"]
            else:
                row = stage["validators"].get(name, {
                    "calls": 0, "inclusive_ns": 0, "exclusive_ns": 0,
                })
            output_rows[name] = {
                "calls": row["calls"],
                "inclusive_seconds": _seconds(row["inclusive_ns"]),
                "exclusive_seconds": _seconds(row["exclusive_ns"]),
            }
        result[phase] = {
            "components": output_rows,
            "validator_exclusive_total_seconds": _seconds(
                stage["validator_exclusive_total_ns"],
            ),
            "decode_unattributed_seconds": _seconds(stage["decode_unattributed_ns"]),
            "custody_reconcile_status": stage["custody_reconcile_status"],
            "repeats": repeats,
        }
    return result


def run_point(sectors: int, seconds: int, batch_units: int,
              checkpoint_seconds: int, repeats: int) -> dict:
    samples = []
    for _ in range(repeats):
        timings = Timings()
        with instrument(timings):
            result = benchmark.run_sample(
                sectors, seconds, batch_units, checkpoint_seconds,
            )
        samples.append((result, timings.output()))

    first = samples[0][0]
    for result, _ in samples[1:]:
        for key in ("state_digest", "event_ledger_digest", "events", "activity"):
            if result[key] != first[key]:
                raise AssertionError(f"instrumented benchmark diverged for {key}")

    phases = set().union(*(set(metrics) for _, metrics in samples))
    merged: dict[str, dict[str, dict[str, int]]] = {}
    call_counts_stable = True
    for phase in phases:
        names = set().union(*(
            set(metrics.get(phase, {})) for _, metrics in samples
        ))
        merged[phase] = {}
        for name in names:
            rows = [metrics.get(phase, {}).get(name, {
                "calls": 0, "inclusive_ns": 0, "exclusive_ns": 0,
            }) for _, metrics in samples]
            counts = {row["calls"] for row in rows}
            if len(counts) != 1:
                call_counts_stable = False
            merged[phase][name] = {
                "calls": rows[0]["calls"],
                "inclusive_ns": int(statistics.median(
                    (row["inclusive_ns"] for row in rows),
                )),
                "exclusive_ns": int(statistics.median(
                    (row["exclusive_ns"] for row in rows),
                )),
            }

    return {
        "sectors": sectors,
        "npcs": sectors * 4,
        "simulated_seconds": seconds,
        "events": first["events"],
        "activity": first["activity"],
        "repeats": repeats,
        "repeatability_verified": True,
        "metric_call_counts_stable": call_counts_stable,
        "state_digest": first["state_digest"],
        "event_ledger_digest": first["event_ledger_digest"],
        "diagnostics": summarize(merged, repeats),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sectors", nargs="+", type=int, default=[1, 2, 4, 8, 16])
    parser.add_argument("--seconds", type=int, default=900)
    parser.add_argument("--batch-units", type=int, default=3)
    parser.add_argument("--checkpoint-seconds", type=int, default=21_600)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if (not args.sectors or any(value < 1 for value in args.sectors)
            or args.seconds < 1 or not 1 <= args.batch_units <= 20
            or args.checkpoint_seconds < 1 or args.repeats < 2):
        parser.error("sectors/seconds/checkpoint must be positive, batch-units 1..20, repeats at least 2")

    report = {
        "benchmark": "projection-validation-diagnostics-v1",
        "source_sha": benchmark.source_sha(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "instrumented": True,
        "timing_note": (
            "Timers include Python wrapper overhead; compare component proportions and "
            "call counts only. Do not compare instrumented wall time to the normal benchmark."
        ),
        "scope": {
            "duration_seconds": args.seconds,
            "npcs_per_sector": 4,
            "finite_timber_and_funded_job_cycles_per_sector": args.batch_units,
            "phases": ["advance", "snapshot", "full_replay"],
            "diagnostics": ["WorldState.to_dict", "WorldState._decode_checked",
                            "all direct decode validators", "custody.reconcile_lots"],
            "custody_note": (
                "The base scenario has no property_custody_lots; zero reconciliation "
                "calls means this optional path was inactive, not that its active cost is zero."
            ),
            "limits": ["independent repeated sectors", "no shared-market contention",
                       "instrumentation is diagnostic, not a capacity claim"],
        },
        "results": [
            run_point(sectors, args.seconds, args.batch_units,
                      args.checkpoint_seconds, args.repeats)
            for sectors in args.sectors
        ],
    }
    if any(not item["metric_call_counts_stable"] for item in report["results"]):
        raise AssertionError("identical samples produced different diagnostic call counts")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
