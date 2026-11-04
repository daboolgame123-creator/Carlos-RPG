# Phase 01-U — Independent adversarial review request

**Status:** EXTERNAL_REVIEW_PENDING. DO NOT MERGE OR DECLARE CLOSED.
**Branch:** simulation-engine-phase-01u, forked from frozen 01-T d2a397bde95d2596592818f348d68b030f78f48a (also EXTERNAL_REVIEW_PENDING).
**Code checkpoint:** 537c72dc3337265d287030cc7f2a9f95885793aa.
**CI:** [41930579158](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41930579158), 564/564 per Python 3.10/3.13 and direct 01-T runtime parity.
**P0:** OPEN; disposable worlds only.

## Independent reviewer checklist

1. Read actual 01-T→01-U diff, not merely the implementation report. Inspect food_navigation.py, living_world.py, tests and CI.
2. Attempt to induce a route choice by modifying only another character's private memory or a distant true resource balance; this must not change the sender/actor's food-route intent.
3. Reject learned-food routes with no complete known path, and verify valid two-hop journeys only after their roads have been physically learned. Review shortest-path time cost, tie resolution, and event provenance.
4. Validate hunger, fatigue, safety, danger warning, unknown owned food, existing explicit navigation targets, local forage priority, and pending decision cooldowns.
5. Deliberately inject false or old rumors. Neither route planning nor travel produces food; an actual local arrival observation should correct a false rumor, or remain unverified when food stock is uninitialized.
6. Challenge scheduled travel, 120s forage, completed-action boundaries, partial event-budget rollback, session pause, stale revision, command replay, SQLite reopen/verify, and split-time results.
7. Re-run the frozen 01-T baseline script with knowledge+foraging+navigation enabled and food_navigation disabled: compare event and state digests, not merely test counts. Keep 01-R/01-S compatibility proofs.
8. No new Schema/Rules from 13/18, no migration, P0 still open. Confirm main and original Carlos story files untouched.

Report APPROVED or BLOCKED with commit SHA, file/line evidence, reproducible failures, CI reference and dependency impact on 01-T. No merge or phase closure simply because CI is green.
