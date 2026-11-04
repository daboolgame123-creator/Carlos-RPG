# Phase 01-N — Faster immutable world projection (initial implementation)

## Change and invariants

This phase optimizes **how event-sourced `WorldState` is copied and reconstructed**, not NPC behavior, action schedules, inventories, relationships, event validation policy, or SQLite transaction rules.

- Uses `collections.abc.Mapping` rather than the slower typing alias, and fast type branches for ordinary JSON scalars and native mapping/list/tuple nodes in `_thaw` (with a generic Mapping fallback).
- The existing public `WorldState.from_dict` **still validates its complete input** and performs **one JSON portability normalization**. It then freezes the normalized tree directly, rather than calling the ordinary dataclass constructor and serializing all 17 state collections again.
- Only states normalized through this fully checked `from_dict` path use the fast `WorldState.to_dict` operation, which deeply thaws immutable collections into detached, mutable Python JSON-compatible structures. Directly constructed states retain the original strict JSON serialize/validate path, including scalar checking.
- Events are still projected one by one, with reducer validation, immutable snapshots, authorization checks and optimistic concurrency control. Invalid multi-event commands still roll back atomically; hash-verified snapshots and full replay remain enabled.

**No game-balance or contract change**: `Schema 11`, `Rules 15`, same event formats, no new migrations. Existing experimental databases with 11/15 remain compatible; no change to actual Carlos narrative or the `main` branch.

## Tests and cross-version equivalence

- The **379 original tests** passed on the optimized source.
- **9 first-pass Phase 01-N tests** passed: nested immutability, defensive deep-copy, direct construction, invalid JSON scalars, corrupt snapshots, strict schema/collection checks, invalid-event immutability, batch rollback and tuple/list round-trip.
- **15 additional integrity/equivalence regressions** passed, including old JSON-roundtrip equivalence, nested collection behavior, dual-store replay and full-engine event counts.
- **403/403 tests passed** in four completed groups: `158 + 107 + 41 + 97`. `python -m compileall -q src tests scenarios` passed.
- The `bench_event_parity.py` script was run with the exact same fixture against both original reviewed 01-M and optimized 01-N source. Both the **complete event-ledger digest** and **final-world-state digest** matched for 10 and 25 NPCs, with full replay verification in both cases. The 10-NPC fixture yielded 72 identical events; the 25-NPC fixture yielded 177 identical events.

## Reproducible full-engine performance comparison

The same `scenarios/test_village/bench_living_world.py` was run on the same local host against the reviewed 01-M source and this candidate. Each result is **one sample**, not a statistical confidence interval. Each sample advances 60 in-world seconds with a separate SQLite test world and fixed, work-oriented NPCs; `setup_seconds` is excluded from the `advance_seconds` below.

| NPCs | Events in advance | 01-M baseline | 01-N candidate | Speed-up |
|---:|---:|---:|---:|---:|
| 10 | 31 | 0.1716 s | 0.0901 s | 1.90× |
| 25 | 76 | 0.8089 s | 0.3784 s | 2.14× |
| 50 | 151 | 2.6970 s | 1.0523 s | 2.56× |
| 100 | 301 | 10.4821 s | 3.5655 s | 2.94× |

At 100 NPCs, the fully optimized version reduces measured advance time by roughly **66%** in this sample, but **is not sufficient to support 1,000 fully simulated NPCs**. Full-world copying and validation still scale expensively with world size/event count. Measurements are environment- and scenario-dependent and do not test long multi-day simulations, real player input, thousands of interactive NPCs or concurrency. Do not extrapolate the old isolated survival-reducer benchmark to full simulation.

### Reproduce

From each branch's `simulation/` directory run:

```bash
PYTHONPATH=src python scenarios/test_village/bench_living_world.py --counts 10 25 50 100
python -m pytest -q tests/test_projection_optimization.py
```

For the cross-version digest comparison, execute the **same** `scenarios/test_village/bench_event_parity.py` file with `PYTHONPATH` pointing once to the previous reviewed 01-M source and once to the 01-N source, then compare their JSON output. No performance threshold is embedded in unit tests to avoid hardware-dependent failures.

## Remaining risks and follow-up

- The core still performs complete state validation for **each** event, and a full batch is projected again inside the transactional event store after the living-world planner has already projected it. End-to-end cost still grows strongly with population and number of events.
- Future phases should profile real-world-sized workloads and consider **verified incremental state projection / reusing already validated event batches**, but only with strong capability checks, causal per-event validation, replay parity and atomic failure tests. Avoid cutting NPC decisions, skipping ledger events or relying on periodic wall-clock progress.
- GitHub-hosted CI was **not** run for this local baseline. Independent 01-N review is still pending.

**Status: initial implementation complete, tested locally, not independently reviewed/closed.**

## Final integration update

The initial report's **388** tests and its baseline timing are valid for an
intermediate candidate only. The subsequently integrated fast-path `_thaw`
change adds 15 more regressions and passes **403/403 tests** across five
completed batches. The event and final-world-state digests still match the
reviewed 01-M baseline for 10 and 25 NPC scenarios. A separate same-host
100-NPC run shows **9.5122 s → 3.4529 s** for 301 events, about **2.75× faster**
(with single-sample limitations). The authoritative final integration evidence
is recorded in `phase_01n_validation.md`. Independent review is pending.
