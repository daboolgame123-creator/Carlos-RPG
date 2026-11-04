# Phase 01-S — Independent adversarial code review request

**State: Pending reviewer sign-off.** Tests are passing but do not replace code review.

**Diff:** `simulation-engine-phase-01r` → `simulation-engine-phase-01s`. Inspect `foraging.py`, `npc.py`, `actions.py`, `domain.py`, `store.py`, `living_world.py`, and `test_foraging.py`.

## Review checklist

1. Prove `NPCDecisionRecorded(action=forage)` cannot be persisted with forged reason/score or without both trusted planner/action capabilities.
2. Show the policy never accesses a different location or NPC's private inventory; absent resource ≠ zero.
3. Verify `forage` cannot deliver free food before its 120-second scheduled completion, during a paused session, or through a forged firing order.
4. Compare standalone `TimeEngine.advance` and `LivingWorldEngine.advance`; confirm already-started attempts complete even after flag toggles.
5. Prove simultaneous attempts cannot spend the same food twice, do not go negative and always log successes *or failures*.
6. Verify action identity/actor/site/time/quantity validators, full replay/snapshot/restart, and atomic rollback on event-budget failure.
7. Inspect `Schema 13 / Rules 17` changes; test a genuine 01-R database is rejected unchanged rather than implicitly migrated.
8. Verify disabled legacy event-digest and semantic state parity, and that old `investigate` / `NPCFoodGathered` paths still behave correctly.
9. Identify any critical privacy, integrity, game-design or action-priority flaw; deterministic lexicographic ordering and local-visibility assumptions are known non-blocking candidates but require judgment.

## Deliverable

For each finding: severity/blocker or follow-up, reproducible scenario, affected function, proposed correction and regression test. Record verdict **approved / blocked**, then rerun complete CI on last commit after any fixes. If approved, change 01-S status to *مكتملة ومراجعة* in ROADMAP.md and update phase_01s_report.md. Do not modify main or Carlos narrative files.
