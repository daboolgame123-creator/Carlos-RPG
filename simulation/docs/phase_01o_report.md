# Phase 01-O — Joined SQLite replay provenance: independent review

## Scope
Optimizes the SQLite event-store **read path** only: instead of looking up the
command's capability flags for every replayed event, one `LEFT JOIN` yields
each ordered event and its provenance in the same cursor. The original code
performed approximately `events + 2` SELECT statements per full replay;
the new code performs two (world-head lookup and replay scan).

The command lookup still rejects missing commands (the LEFT JOIN is essential
here), preserves the stored per-command capability flags, and passes each
event through the **same** domain reducer in the same order. Event hashes,
snapshot hashes, version checks, session rules, revisions, database transactions
and final consistency/reservation checks remain in place. No world schema,
rules or gameplay behavior changes were intended.

## Source and tests
- Runtime change: `simulation/src/carlos_sim/store.py`.
- New regression tests: `simulation/tests/test_replay_join.py` (3 tests).
  They cover bounded SELECT count, mixed clock/bootstrap replay against
  snapshots, and fail-closed behavior on a deliberately orphaned command.
- Reproducible measurement:
  `PYTHONPATH=src python scenarios/test_village/bench_replay_store.py --counts 10 50 100`.
  Same script, separate source imports against reviewed 01-N and 01-O.
- CI: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41825396142
  - Python 3.10: **413 passed**, compilation passed.
  - Python 3.13: **413 passed**, compilation passed.
  - Full event-ledger and final-state digest output matched reviewed 01-N
    byte-for-byte in the 10- and 25-NPC test worlds, on both Python versions.

## CI benchmark: full replay (isolated)

Values are median wall-clock seconds from **three repetitions** of the same
disposable database on one CI runner per Python version. Excludes DB setup.
No performance threshold is used for test correctness.

| Python | Events | 01-N SELECTs | 01-O SELECTs | 01-N seconds | 01-O seconds |
|---|---:|---:|---:|---:|---:|
| 3.13 | 10 | 12 | 2 | 0.002203 | 0.001895 |
| 3.13 | 50 | 52 | 2 | 0.012239 | 0.011523 |
| 3.13 | 100 | 102 | 2 | 0.032674 | 0.029224 |
| 3.10 | 10 | 12 | 2 | 0.002375 | 0.002071 |
| 3.10 | 50 | 52 | 2 | 0.013439 | 0.012478 |
| 3.10 | 100 | 102 | 2 | 0.035102 | 0.032671 |

## Review conclusions and remaining bottlenecks
The **observable query-count reduction is deterministic** for these
fixtures, whereas the timing difference is modest and machine-dependent.
This review verified source changes, additional corruption tests, the
complete 413-test suite and cross-version parity. It does not show
that 1,000 autonomous NPCs can be simulated interactively.

Remaining large-world cost is mostly full-state immutable projection and
validation for **each** event, plus two full batch projections for planning
and committing a living-world command. Any future shortcut must preserve
authorization, causal per-event checking, replay parity, rollback and
revision conflicts. Do not discard event detail or suppress NPC decisions
for artificial benchmark wins.

**Verdict: Phase 01-O closed within local/test-world scope.**
No migration; **Schema 11 / Rules 15**. The main branch and actual
Carlos narrative are unchanged.
