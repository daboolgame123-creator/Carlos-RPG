# Carlos RPG 03-A — exact-SHA verification handoff

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-validation`
Last tested code: **NOT YET VERIFIED**.
Implementation fixes: `677e81d85d426d977d7831e6684d71a679c69a56` (`injury_source_gate.py`); regression tests: `8ef8de357720b39171c3d3e423874dacc8aba653` (`test_injury_source_gate_03a.py`).
Schema/Rules still 29/37; no durable injury event was enabled.

## Requested verification — only this scope

1. Read `AGENTS.md`, `simulation/docs/WORK_ROUTING_PROTOCOL.md`, `simulation/docs/PHASE_03A_SOURCE_GATE.md`, and this instruction; check the HEAD and worktree before running anything.
2. Checkout `simulation-engine-phase-03a-validation`, do **not** merge it into `simulation-engine-phase-04a-j1` or `main`.
3. From `simulation/` run in Python 3.10 and 3.13:
   `python -m pytest -q tests/test_injury_intake_03a.py tests/test_injury_transitions_03a.py tests/test_recovery_readiness_03a.py tests/test_injury_source_gate_03a.py tests/test_injury_registry_03a.py tests/test_injury_contract_guards_03a.py`
   and `python -m pytest -q`.
4. Inspect GitHub Actions run for the final SHA; if CI cannot run, state that explicitly rather than claiming success. Check frozen parity baselines and compatibility/replay targeted tests.
5. Review: injury proposals must not mutate state, infer actual injuries from theft/observations/vital tests, create a schedule, spend resources, or grant authority; reject negative/bool/future event times; reject invalid event version and empty cause or event type.
6. If a test fails, fix the **smallest local problem on this branch** and rerun required checks. Avoid changes to store/domain schema, authority rules, or unrelated property/justice modules; these have separate review gates.
7. Report exact final HEAD, interpreters, commands, pass/fail/skips, CI run URL if available, and any failing tests. Do not claim permanent injury, treatment, or production readiness.

## Decision gate

Do **not** begin durable `InjuryRecorded`/SQLite persistence or change schema/rules before **both** the new focused tests and the complete regression suite are green at the final code SHA. When they are, plan a separate branch/commit series for trust-source provenance, dedicated command capability, versioned NPC injury collection, and replay/corruption tests. No NPC player-status leakage. The unapproved `J1c2b-LAW` branch remains untouched.

## CI incident and corrective evidence — 2026-11-06

The draft PR [#6](https://github.com/daboolgame123-creator/Carlos-RPG/pull/6) triggered GitHub Actions run [42260046143](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42260046143). The run exposed a **real source syntax error**: source and test patches contained literal `\\n` tokens instead of physical newlines. Both interpreter jobs failed at the `compileall` step, before pytest began. This is a confirmed failure, not a passing test.

Fixed both files on the same isolated verification branch:
- `simulation/src/carlos_sim/injury_source_gate.py`: commit `1e08d63dd3a06a0916d3e080f6aa77304a2d78e4`
- `simulation/tests/test_injury_source_gate_03a.py`: commit `efeb4a0f12f5cdd151a41cfbd72928f6c33e36bc`

New PR-triggered run [42260232264](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42260232264) started on commit `efeb4a0f12f5cdd151a41cfbd72928f6c33e36bc`. On last checked status, both Python 3.10/3.13 jobs were **in progress, in the Install test dependency step**; no overall pass/fail has been established. Do not mark this stage closed unless both complete successfully at final implementation SHA, including all smoke/parity steps. If errors appear, read the specific GitHub Actions job logs and correct the root cause before extending the world schema.

No persistent injury reducer, event authorization, recovery scheduler or SQLite change has been added.
