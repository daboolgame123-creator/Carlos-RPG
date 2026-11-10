# CI-04c — Real-world 6h load and replay caller map

**Date:** 2026-11-10 UTC  
**Status:** `CALLER_COUNT_PROVEN / NO_RUNTIME_PATCH / NOT_CI_OPTIMIZED`.

## Test evidence

- Branch `engineering/ci04c-load-callmap-20261110`; initial tested source `d640f7ff1192411b336b7e4ba819238cac52ce6c`.
- [GitHub Actions 42806706041](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42806706041) **SUCCESS** on Python 3.10 and 3.13.
- Bounded original PLAY-47 13-resident 6-hour scenario at pinned runtime `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`; one run uninstrumented, another with **in-process-only wrappers** on `SQLiteEventStore.load`, `verify` and `store.apply_event`. Wrappers are reverted before the process ends and no production source is edited.
- Full final `WorldState.to_dict()` and complete SQLite `worlds/commands/events/snapshots` receipts of both runs compared and **equal**; independent reopen/`verify` succeeded.

## Measured call counts (identical across Python versions)

| Metric | Count |
| --- | ---: |
| Real stored events at 6 hours | 807 |
| Calls to `SQLiteEventStore.load` | 10 |
| Snapshot-mode loads | 9 |
| Full genesis loads | 1 |
| Calls to `SQLiteEventStore.verify` | 1 |
| Event projection invocations *within store.load* | 2,286 |
| Event projections in *append*, not load | 639 |
| Recorded history replay multiplier (2,286/807) | 2.833 |

## Exact immediate load callers

| Caller | Calls | Notes |
| --- | ---: | --- |
| `test_play47_closure_endurance.py:_day` | 3 | scenario entry/expected-state checks |
| `store.py:snapshot` | 2 | snapshot operations call `load` |
| `store.py:verify` | 2 | full-genesis + snapshot based verification |
| `time_engine.py:open_session` | 1 | session readiness |
| `living_world.py:advance` | 1 | simulation advance |
| `store.py:append` | 1 | transactional update path |

**Elapsed wall times** (not performance A/B evidence because instrumented) were Python 3.10 7.42s baseline / 7.37s instrumented; Python 3.13 4.06s / 4.15s. No speedup is claimed; runner variation and instrumentation overhead apply.

## Decision

The principal repeated work is reconstructing 807-event SQLite histories multiple times due to `snapshot`/`verify`, not 10,000 newly recorded events. Keep full genesis, legacy refusal, event hash/capability checks and independent 42/57 snapshot verification. Future scoped optimization work: consider reusing an already fully verified, immutable projection **only with** clear invalidation of any external SQLite writes, transactional race checks, history receipt verification, and isolated A/B + adversarial regressions. No opportunistic memoization of mutable world or weakening of release checks.

This report neither modifies `simulation/` nor certifies faster CI. Required Status Checks remain unverified due to GitHub protection API 403. `main` and Schema 42/Rules 57 remain unchanged.
