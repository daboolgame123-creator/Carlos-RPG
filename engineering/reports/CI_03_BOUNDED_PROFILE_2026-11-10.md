# CI-03 — نتيجة عينة Profiling على Python 3.10/3.13

**Date:** 2026-11-10 UTC  
**State:** `BOUNDED_SAMPLE_VERIFIED / SEVEN_DAY_HOTSPOT_NOT_YET_PROVEN`.  
**Exact tested SHA:** `d1b379b4c6c5ef4d8fe86a794501f2718939c4f2`.  
**Actual CI:** [42786344145 — SUCCESS](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42786344145), with both `sample-profile (3.10)` and `sample-profile (3.13)` **SUCCESS**. The temporary workflow was `.github/workflows/ci03-performance-probe.yml`, [preserved at tested SHA](https://github.com/daboolgame123-creator/Carlos-RPG/blob/d1b379b4c6c5ef4d8fe86a794501f2718939c4f2/.github/workflows/ci03-performance-probe.yml), branch-scoped to `engineering/ci-mig-baseline-20261110` and limited to 15 minutes per job. It was deliberately retired from the final branch after verification to avoid increasing the permanent workflow count. This probe is **not** a release-gate replacement.

## Evidence from actual job logs

| Measurement | Python 3.10 | Python 3.13 |
| --- | ---: | ---: |
| Selected unit / custody / compound tests | 41 passed + 1 intentionally deselected in **4.13s** | 41 passed + 1 deselected in **7.18s** |
| One-hour simulated economy pilot | 1 passed in **1.23s** | 1 passed in **2.36s** |
| cProfile elapsed (includes pytest overhead) | 1.368s | 2.580s |
| All calls / primitive calls | 5,493,900 / 4,181,659 | 5,098,896 / 4,051,792 |
| `domain.apply_event` calls / cumulative time | 1,498 / 0.943s | 1,498 / 1.837s |
| `store.load` calls / cumulative time | 18 / 0.893s | 18 / 1.759s |
| `domain._decode_checked` calls / cumulative time | 1,517 / 0.688s | 1,517 / 1.351s |
| `domain._freeze` recursive calls / cumulative time | 455,588 / 0.251s | 455,588 / 0.458s |
| `domain._thaw` recursive calls / cumulative time | 610,216 / 0.225s | 610,216 / 0.420s |
| `store.verify` calls / cumulative time | 3 / 0.437s | 3 / 0.858s |
| `domain.canonical_hash` calls / cumulative time | 1,458 / 0.022s | 1,458 / 0.047s |

**Important:** cumulative times from nested function calls **overlap** and must not be added. cProfile affects execution times. This microfixture is not the seven-day world, and the 3.13 Python builds, runner load and cProfile overhead differ; do not claim a universal 2x slowdown or extrapolate these seconds to the 75-minute gate.

## Interpretation and next experiment

- The short fixture shows **event projection and repeated SQLite load/replay are major cost centers** in its own execution. `_freeze` and `_thaw` are frequent and measurable, but deleting immutability, hashing or replay checks is not justified.
- The 1-hour fixture confirms test logic can be fast when the world/event graph is small. The 7-day scenarios include daily SQLite close/reopen and full-genesis verification, likely a substantially different cost profile. **We have not measured its hot functions yet.**
- A subsequent `CI-03b` should sample a **bounded 6h/24h checkpoint** with production-equivalent event counts, instrumenting counts and per-stage time for `load`, `apply_event`, `verify`, `_freeze`, `_thaw`, and SQL queries (including WAL) before authorizing a structural-sharing or checkpoint optimization.
- Prepare a no-mutation A/B harness: exact inputs and events, identical digest/semantic state/revision/time, and compare on the same Python/runner. Preserve 7d independent replay checks in final release gates even if shorter feedback tiers become available.

## Coverage notes

The one deselected test is **the genuine 41/56 old-save refusal**, because this short probe does not fetch its historical predecessor; that rejection remains green on the previously verified [full PLAY-47 acceptance run](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42731103345). Do **not** use this tiny sample as proof of full suite or old-save compatibility.

No runtime/source state, Schema/Rules, test assertions or trust boundary was modified. `CI-03` is not fully closed until larger-scale hotspot evidence is taken and acceptance criteria quantified.
