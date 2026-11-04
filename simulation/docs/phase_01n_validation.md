# Phase 01-N — Final integration verification (supersedes preliminary totals)

This document records the **combined Phase 01-N candidate** after both immutable-state normalization and the additional fast-path for built-in JSON types, plus 22 further integrity tests. Any earlier 388-test or 2.14× figures in the initial report describe an **intermediate** version; these final checks apply to the integrated code.

## Verified code behavior

- `WorldState.from_dict`: complete existing snapshot validation, one canonical JSON normalization, then deep-freeze of normalized data; no weakening of external validation.
- `WorldState.to_dict`: deep detached copy for trusted normalized projections; direct constructor keeps strict JSON validation including scalars.
- `_thaw`: fast path for JSON scalars/dict/mappingproxy/list/tuple; fallback still supports custom `Mapping` inputs.
- Same decisions, events, event ordering, resource conservation, frozen game clock when paused, event-store integrity, role/capability boundary and atomic rollback.
- **No event schema or rule changes:** Schema **11**, Rules **15**; no database migration.

## Final local tests

**410/410 passed** in five complete batches:

| Test group | Passed |
|---|---:|
| Core, clock, NPC, actions and living world | 134 |
| Movement, navigation and social | 107 |
| Assistance, promises and autonomy | 72 |
| Consumption and survival | 66 |
| Projection performance/integrity (9 + 15 + 7 new tests) | 31 |

`python -m compileall -q src tests scenarios` passed. An all-in-one multi-group shell command hit its execution timeout after three complete passing groups; the remaining two groups were independently rerun and passed. No GitHub-hosted CI ran for these results.

## Cross-version event/state equality

The **same** `bench_event_parity.py` code ran in separate Python processes using reviewed Phase 01-M and the integrated Phase 01-N code. JSON output matched byte-for-byte at **10 NPCs (72 logged events)** and **25 NPCs (177 logged events)**. This includes the complete event-ledger digest, final-state digest, logical clock, revision and replay verification. This is strong evidence for the measured scenarios, not a mathematical proof of equivalence for every possible world.

## Full-engine benchmark, same local environment

One 60-second autonomous world advance per measurement, independent SQLite test world, setup excluded; same work-oriented fixture and **identical event counts** in both versions:

| NPCs | Events | Reviewed 01-M | Integrated 01-N | Speed-up |
|---:|---:|---:|---:|---:|
| 10 | 31 | 0.1222 s | 0.0535 s | 2.28× |
| 25 | 76 | 0.6859 s | 0.2405 s | 2.85× |
| 50 | 151 | 2.3237 s | 0.9001 s | 2.58× |
| 100 | 301 | 9.5122 s | 3.4529 s | 2.75× |

At 100 NPCs, this measured roughly **64% lower wall-clock execution time**. Samples are not statistical confidence intervals or production latency guarantees. Reproducing the numbers on different hardware or under different loads may yield different timings. The improvement does **not** mean the engine already supports 1000 fully active NPCs efficiently. A future controlled optimization should examine per-event full-world projection and double simulation at plan/commit time, while preserving complete audit parity.

## Status

**Phase 01-N independently reviewed and closed for test-world scope.** GitHub Actions passed 410/410 tests on both Python 3.10 and 3.13, and cross-branch event/state parity at 10/25 NPCs. See `phase_01n_independent_review.md`. `main` and Carlos narrative remain unchanged.
