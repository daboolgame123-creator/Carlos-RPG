# Carlos RPG — CI and simulation performance audit

**Date:** 2026-11-27

**Status:** `AB_VALIDATED_LOCALLY / PRIOR_FULL_CI_PASS / REALISTIC_SCALE_LOCAL / FINAL_CI_PENDING / CI-00_PARTIAL / CI-03_PARTIAL`

**Work branch:** `chore/carlos-ci-performance-audit-20261127`

**Audit base HEAD:** `80881060da8cffc897f81b979882a9235d890ac4` (source-equivalent to tested code SHA `0f7664fe8e2cc1b3147b9ed223e059c81c9bc4c8`; intervening changes before this audit were documentation only).

**PR #185:** still open and draft; head `416e26b6c037b2fc504c8454d9b607aadeee7eba`; no merge or PR update was made.

**Realistic scale benchmark source:** `8218cdc173d3df67dba4544a0e42d086e97ea689`. The benchmark was run locally on this exact code SHA; final full regression CI for this addition is pending.

The measured A/B change is limited to the three-day test fixture: it writes a derived SQLite snapshot after each quarter-day advance and asserts the snapshot equals the returned world state. It does not change engine behavior, workflow definitions, event history, saves, or story files. The current `main` branch was not used.

## Findings

1. **The full regression suite, rather than setup or smoke checks, dominates CI time.** The latest exact-code CI run executed 1,958 tests plus 1 skipped. Pytest itself took **23:47 on Python 3.10** and **22:06 on Python 3.13**; the complete jobs took 24:42 and 22:53 respectively. The Python matrix runs in parallel.
2. **Two three-day end-to-end tests consume 7:14 of a 19:42 local suite run (36.7%).** Each test advances the same seven-NPC economy through 12 quarter-day commands, validates resources, and verifies replay. These are valuable acceptance tests, not disposable overhead.
3. **The slow test repeatedly replays its growing event history.** In the measured provisioned three-day test, `store.load` was called 50 times and `apply_event` 70,889 times. `apply_event`, checked event decoding, and the recursive `_freeze`/`_thaw` paths dominate the profiled call tree. This is evidence for a test-workload/replay cost, not yet proof that any one engine function should be optimized.
4. **The pure survival reducer scales well by itself, while whole-engine advances grow faster.** The existing 100-NPC engine benchmark completed one 60-second command in a median 2.256 seconds, but its NPCs have no labor or investigation resources and it does not model a functioning economy. It is a technical baseline, not a forecast for a village with wages, production, routes, and social activity.
5. **Workflow changes need a required-check inventory first.** There are 160 workflow files; 159 contain `push`, 10 contain `pull_request`, and 125 contain `workflow_dispatch` (trigger categories overlap). The repository branch-protection endpoint returned HTTP 403, so the required status checks could not be confirmed. No workflow was changed.

## Local test profile

Environment: Linux workspace, Python **3.12.14**, current simulation source, existing `.venv`.

Command:

```bash
PYTHONPATH=src ./.venv/bin/python -m pytest -q --durations=30
```

Result: **1,958 passed, 1 skipped in 1,182.26 seconds (19:42)**.

| Rank | Test | Duration |
| --- | --- | ---: |
| 1 | `test_play_three_day_survival_batch_28.py::test_real_three_day_endurance_and_conservation[finite-provisions]` | 239.72 s |
| 2 | `test_play_three_day_survival_batch_28.py::test_real_three_day_endurance_and_conservation[shortage]` | 195.00 s |
| 3 | `test_injury_observer_memory_03a7c.py::test_pending_evidence_cannot_bypass_finite_memory_capacity` | 27.13 s |
| 4 | `test_play_ecology_endurance_batch_22.py::test_milestones_monotone_and_resource_accounting_even_after_depletion` | 24.67 s |
| 5 | `test_injury_visible_supportive_care_03a7c.py::test_care_memory_full_does_not_prevent_basim_observing` | 23.89 s |
| 6 | `test_play_adversity_batch_20.py::test_one_world_is_deterministic_across_independent_sqlite_files` | 20.18 s |
| 7 | `test_injury_observer_memory_03a7c.py::test_capacity_exhaustion_does_not_block_valid_local_look` | 17.67 s |
| 8 | `test_play_physical_supply_batch_27.py::test_seven_characters_three_days_and_reality_counterfactuals[opts0-2-2-2]` | 17.56 s |
| 9 | `test_play_physical_supply_batch_27.py::test_hungry_courier_cannot_eat_consigned_customer_food` | 17.40 s |
| 10 | `test_play_physical_supply_batch_27.py::test_seven_characters_three_days_and_reality_counterfactuals[opts6-1-0-0]` | 15.21 s |

The two three-day tests alone account for 434.72 seconds of the 1,182.26-second run. Profiling one provisioned case with cProfile took **625.19 seconds**, around 2.6 times its unprofiled 239.72-second result; that profiled wall time must not be compared with CI or treated as a normal run.

The profile recorded 70,889 calls to `domain.apply_event` and 50 calls to `store.load`. `apply_event` accumulated 602.1 profiled seconds; `store.load` accumulated 563.1 seconds. These totals overlap and must not be added. Recursive `_freeze` and `_thaw` recorded about 281 million and 289 million calls respectively. Before the A/B change, no intermediate snapshots bounded the reads during the three-day advance. The final `db.verify()` still performs a full genesis replay after the change.

## A/B test-only checkpoint result

Both runs used Python 3.12.14 on the same workspace and executed the same parameterized three-day test. The before run used the original fixture; the after run added a checkpoint after each quarter. No event or economy assertion was removed.

| Personal food | Before | After | Reduction | Before → after events | Event digest identical | Snapshots before → after |
| ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 18 (finite provisions) | 216.26 s | 53.02 s | 75.5% | 2,589 → 2,589 | Yes | 1 → 12 |
| 0 (shortage) | 177.98 s | 44.95 s | 74.7% | 2,458 → 2,458 | Yes | 1 → 12 |
| **Both tests** | **394.34 s** | **98.07 s** | **75.1%** | — | — | — |

The aggregate event-hash digests were unchanged: food 18 `c129ea4de9411de2fd820c1e3f46ea90cec85db79c6c6a58052cbf234d11fe08`; food 0 `b7a00152308be6f8d322deda864618c081350c5122de0011524d541a90f9ac1d`. Both databases reported `PRAGMA integrity_check = ok`. The printed three-day outcomes also matched exactly, including daily action counts, meals/consumption, hunger/fatigue, crop growth, and deliveries. The test's final `db.verify()` passed from genesis with all 12 quarter checkpoints present.

The combined targeted regression command passed **6 tests** (`test_play_three_day_survival_batch_28.py` and `test_replay_join.py`) on Python 3.12.14 in **99.65 seconds**. Its two endurance cases measured 54.60 and 44.30 seconds on that repeat; snapshot/replay and concurrent-read checks each took at most 0.03 seconds. It also passed **6/6 on Python 3.13.5 in 81.67 seconds** (45.10 and 35.59 seconds for the endurance cases), and **6/6 on Python 3.10.22 in 136.50 seconds** (76.21 and 60.03 seconds for the endurance cases). These are targeted runs, not the full version matrix.

## Engine-scale microbenchmarks

These measurements used the existing benchmark scripts, with three fresh SQLite samples for each whole-engine population. Timing has no asserted threshold and should only be compared on the same machine and Python version.

### Existing 60-second whole-engine command

From `scenarios/test_village/bench_living_world.py`; median per three fresh worlds:

| NPCs | Setup median | Advance median | Advance events | Simulated time |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 0.0142 s | 0.0655 s | 31 | 60 s |
| 25 | 0.0363 s | 0.2093 s | 76 | 60 s |
| 50 | 0.1005 s | 0.6440 s | 151 | 60 s |
| 100 | 0.3390 s | 2.2564 s | 301 | 60 s |

The benchmark configures each person as a worker but initializes `labor_units` and `investigation_attempts` to zero. It does not exercise wages, production, market transactions, routes, or speech. The event count grows linearly with population in this fixture; wall time grows faster than that, so larger realistic workloads still need direct measurement.

### Full Replay store

From `bench_replay_store.py`; three replay samples, two `SELECT` statements for every size:

| Events | Median full replay |
| ---: | ---: |
| 10 | 0.002015 s |
| 50 | 0.008349 s |
| 100 | 0.019137 s |
| 500 | 0.192111 s |
| 1,000 | 0.650534 s |

The query count remains constant here; reduction/state validation work grows with the replay history. The profile above shows why repeatedly replaying a growing history inside a multi-step test is much more expensive than replaying it once.

### Pure survival reducer

From `bench_survival.py`; five samples per population:

| NPCs | Median reducer time |
| ---: | ---: |
| 10 | 0.00041 s |
| 25 | 0.00088 s |
| 50 | 0.00117 s |
| 100 | 0.00215 s |
| 1,000 | 0.02719 s |

This only applies one `TimeAdvanced` event to an in-memory state. It is not whole-engine or sustained simulation throughput.

## GitHub Actions baseline

The latest exact-code [Simulation regression suite run #46049673812](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/46049673812) succeeded on SHA `0f7664fe8e2cc1b3147b9ed223e059c81c9bc4c8`. Pytest output was 1,958 passed and 1 skipped in 23:47 (Python 3.10) and 22:06 (Python 3.13). Its job durations include checkout, dependency installation, compile, and smoke steps.

The last ten simulation-suite runs with both matrix jobs available had per-job wall times below. The jobs run concurrently, so elapsed wall time per run is roughly the slower Python job, not the sum of the two columns.
Across all 20 jobs, mean duration was **18.22 minutes**, median **17.51 minutes**, and range **14.33–25.98 minutes**.

| Run | Python 3.10 job | Python 3.13 job |
| ---: | ---: | ---: |
| 46049673812 | 24.70 min | 22.88 min |
| 46017871726 | 18.25 min | 18.28 min |
| 46008013870 | 16.20 min | 14.33 min |
| 45998760804 | 25.98 min | 14.68 min |
| 45987206045 | 18.18 min | 17.13 min |
| 45977485506 | 23.53 min | 14.55 min |
| 45922155158 | 15.67 min | 14.48 min |
| 45914899491 | 18.60 min | 17.80 min |
| 45912907781 | 18.20 min | 16.68 min |
| 45847398391 | 17.22 min | 17.12 min |

Workflow inventory is presence-based and overlapping: **160** `.github/workflows/*.yml` files; `push` in 159; `pull_request` in 10; `workflow_dispatch` in 125. The main simulation suite runs `pytest -q` in a Python 3.10/3.13 matrix. Its PR path filter includes all of `simulation/**`, so a documentation-only change under `simulation/docs/` can trigger the full suite. The project also has 97 scenario-level test files outside the default `testpaths = ["tests"]`; some are explicitly called by workflows, while others require explicit selection.

`gh pr checks 185` showed passing checks for the current draft PR. Reading branch-protection required-check settings returned HTTP 403 (`Resource not accessible by integration`), so this audit cannot determine which checks are required for the base branch. Required-check status must be confirmed before introducing conditional jobs or changing check names.

## Recommendations and next step

1. **A/B test-only optimization — locally validated.** Checkpoint derived snapshots after each quarter-day advance. Both scenarios retained all conservation/activity assertions; event counts, aggregate digests, final outcomes, and the final full genesis replay matched. The two cases ran 75.1% faster in the same-machine sample.
2. **The checkpoint optimization passed full exact-SHA CI.** Run #46071708587 passed on SHA `ee791a6ed761b7ad92e8253fdd72955d01a3c121`: both Python 3.10 and 3.13 reported **1,958 passed, 1 skipped**, and all smoke/compatibility steps passed. This run predates the scale harness below; the latest harness SHA still needs its own full matrix.
3. **Initial realistic scale benchmark — locally verified.** [The opt-in harness](../simulation/scenarios/test_village/bench_realistic_world_scale.py) scales 4–32 NPCs across 1–8 finite sectors for 900 simulated seconds, exercising autonomous decisions, funded production wages, wood/charcoal material trades, road travel, owned-food consumption, recorded speech, SQLite snapshots, and genesis replay. Two independent databases per size produced identical event/state digests. Measurements are in the next section.
4. **Next measurement before optimizing NPC scheduling.** Extend the harness to a longer fixed horizon and a controlled shared-market case; retain event-ledger determinism and do not turn local timings into CI thresholds or capacity claims.
5. **Do not optimize the pure survival reducer first.** It reaches 1,000 NPCs in about 27 ms in isolation; current evidence points more strongly to repeated replay and whole-engine state validation.
6. **Design fast feedback separately from release evidence.** Use targeted probes for changes; run the full exact-SHA Python 3.10/3.13 matrix for code closure. A docs-only path needs an explicit always-running success/failure aggregate so required checks cannot silently become skipped.

### Realistic multi-sector scale baseline

Environment: Python **3.12.14**, Linux `6.18.57-x86_64-with-glibc2.41`, harness SHA `8218cdc173d3df67dba4544a0e42d086e97ea689`. Each point simulates **900 seconds**, has **3** finite timber units and exactly funded job cycles per sector, and reports the median of **2 fresh SQLite databases**. Timings are descriptive; there is no hardware-dependent pass threshold.

| Sectors | NPCs | Events | Advance median | Full genesis replay | Snapshot load | Snapshot write | SQLite rows changed by advance |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 130 | 0.141 s | 0.068 s | 0.0019 s | 0.075 s | 90 |
| 2 | 8 | 249 | 0.374 s | 0.187 s | 0.0029 s | 0.177 s | 168 |
| 4 | 16 | 487 | 1.195 s | 0.585 s | 0.0054 s | 0.574 s | 324 |
| 8 | 32 | 963 | 4.141 s | 1.966 s | 0.0088 s | 1.967 s | 636 |

Across the 32-NPC run, the log contains **96** recorded NPC decisions, **24** completed jobs and paid wages, **8** material trades, **16** completed trips, **32** meals, and **16** recorded social messages. Opening and closing copper totals match, and starting personal food equals remaining food plus consumed meals. The harness verifies SQLite integrity, compares the snapshot-loaded state with the returned state, and compares full genesis replay with both; each repeated pair has identical event-ledger and state digests.

The one-sector case also ran twice each on Python **3.10.22** and **3.13.5**. Both versions produced the same 130-event count, event-ledger digest, state digest, and activity counts as Python 3.12.14. Their wall times are recorded by the harness but are not compared across Python versions.

This is a representative, deliberately bounded workload: sectors repeat independently and do not compete in one shared market. It covers several existing engine systems together, but it is not a 96-hour/seven-day sustainability test or a performance forecast. Work grew faster than the event count in these samples; that is a profiling lead, not proof of a specific bottleneck.

### Remaining audit gaps

- CI-00 is partial: required checks could not be read, and the 160-workflow inventory has not yet mapped every branch filter, duplicate behavior, and historical dependency.
- CI-03 now has a local full-suite duration profile, one representative cProfile, simple population/replay/reducer baselines, the realistic 4–32-NPC multi-sector baseline above, and a test-only checkpoint A/B with full exact-SHA CI. The longer-horizon/shared-market measurement is still open.
- Full exact-SHA Python 3.10/3.13 CI for the new benchmark commit is pending. No engine or workflow optimization has been implemented.
