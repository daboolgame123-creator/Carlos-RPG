# CI-04b — Head snapshot replay/verification A/B, no-go

**2026-11-10 — EXPERIMENT_VERIFIED / PERFORMANCE_PATCH_NO_GO**

## Scope

- Research branch `engineering/ci04b-replay-ab-20261110`.
- Tested exact commit `624e95bd89ba1b885a47d3615be6618a0fa14c40`.
- [GitHub Actions #42799777064](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42799777064): **SUCCESS** in Python 3.10 and 3.13.
- Test harness: [ci04b_head_snapshot_ab.py](../probes/ci04b_head_snapshot_ab.py). Pinned PLAY-47 13-resident 6-hour source at `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`, revision **807**, three alternating A/B iterations per Python. Real SQLite, no test mocking of game logic.

## Hypothesis and measured result

The existing `SQLiteEventStore.verify()` runs full genesis Replay plus a snapshot-based load and compares canonical states. The proof-only candidate, only when the latest snapshot is at the **world head**, replays from genesis and separately validates the stored snapshot state/hash/identity against the result. Missing/non-head snapshots use the unmodified existing verify. This is a prototype, **not** a runtime patch.

| Measure, lower is better | Python 3.10 | Python 3.13 |
| --- | ---: | ---: |
| Original `verify` median | 0.850664 s | 0.794418 s |
| Experimental candidate median | 0.856769 s | 0.795124 s |
| Candidate/baseline ratio | 1.0072 (slower ~0.72%) | 1.0009 (slower ~0.09%) |

All full-world state dictionaries matched. Four corruption cases were **rejected by both**: forged snapshot hash, semantically inconsistent state with recalculated hash, forged event hash, and altered snapshot revision. The missing-snapshot fallback matched the original.

A single matrix run with three repetitions does **not** establish precise speed deltas. Nevertheless, it offers no positive evidence for a performance improvement. Most cost remains genesis event replay (see [CI-03b profile](CI_03B_REAL_24H_HOTSPOTS_2026-11-10.md)); a head-snapshot fast path cannot evade it.

## Decision

**NO_GO:** do not apply the candidate to `simulation/src/carlos_sim/store.py`. Keep full and snapshot-based verification, all integrity checks, and current CI gates. Investigate repeated `store.load` call sites, event projection work, and safe replay architecture with bounded A/B proof before any change. No changes to Schema 42 / Rules 57, `main`, or production runtime; no claim that CI has become faster.
