# Phase 01-D — NPC action execution

## Implementation

- Added `actions.py`, event-sourced `WorldState.actions` and `NPCActionStarted`.
- Started actions have deterministic, persisted completion signals; on firing, the same projection transaction applies bounded real needs/counter effects and records an outcome.
- Work, rest, investigation and wait are all represented as time-consuming actions. Investigation records an **attempt**, not fictional discoveries; work records **labor units**, not goods or money.
- Multiple NPCs can act in parallel; fixed per-action durations and stable scheduled ordering are used.
- Active-session enforcement now also guards direct clock writes at `SQLiteEventStore.append`.
- Protected action schedule payloads and completion counters against ordinary event mutation and prevented canceling a running action signal.
- No actual Carlos story data imported or modified.

## Verification

Local command: `cd simulation && python -m pytest -q` — **112 passed after review** (84 prior tests + 28 Phase 01-D tests). `python -m compileall -q src tests scenarios` passed. The five-character offline demo was run successfully and completed all five scheduled NPC actions, with differentiated outcomes. No GitHub CI run.

Regression coverage includes cross-NPC concurrency; exact completion timing and results; interruption and resumption; session close/reopen; snapshot and genesis replay; unknown counters; forged schedule/action events; duplicate IDs; stale revisions; tampering and resource minting; over-early firing; action repeat; original Carlos/story unaffected.

## Changed files

- New: `src/carlos_sim/actions.py`, `tests/test_actions.py`, `scenarios/test_village/demo_actions.py`, `docs/phase_01d_report.md`.
- Updated: `src/carlos_sim/domain.py`, `src/carlos_sim/store.py`, `src/carlos_sim/__init__.py`, baseline clock tests `tests/test_engine.py`, `tests/test_time_engine.py`, `README.md`, `docs/architecture.md`, `docs/decisions.md`.

## Limitations and remaining work

- Fixed numeric action rules are **test-only**. They do not represent a real farming/economy system or generate physical items.
- `NPCActionService.start` is trusted-local only and does not itself authenticate users. A future API must authenticate the session/caller.
- Completion is automatic **only for actions already started**. Selecting the next intention and starting the next action still requires an explicit authorized caller. Continuous event-driven NPC autonomy is future work.
- No cancel-in-progress policy, NPC travel, relationships, sensory world knowledge, randomized success, inventory or HP/XP effects.
- Action records are append-only and currently retained indefinitely; archival/compaction strategy deferred.
- World schema 5 / rules 6, incompatible with older experimental data without migration. All local databases used in tests are isolated and disposable.
- The GitHub branch is a staging implementation; do not merge to main until reviewed.

## Post-implementation review and corrective action

An additional edge-case test identified a durable orphan reservation bug: a caller holding the internal `action_authorized` capability could commit `ScheduledEventCreated` with reserved `__npc_action_id` without a matching `NPCActionStarted` in the same transaction. This left the clock unable to process the resulting due signal because its action was missing.

**Fix:** `validate_action_reservations` now runs at the **atomic command boundary** before SQLite commit and at the **fully replayed world boundary** during load. It rejects reserved signals that do not map to matching running actions. The check is deliberately after full command application, because a valid action-start command creates its schedule first and its action record second.

**Evidence:** The failure was reproduced in an isolated SQLite test world, fixed, and covered by two regression tests: a lone forged reserved schedule is refused and rolls back completely; an authentic two-event action start still commits and replays correctly. `python -m pytest -q`: **112 passed**. `python -m compileall -q src tests scenarios`: passed. Current GitHub source files `actions.py`, `store.py`, and `test_actions.py` were verified by matching exact Git blob SHAs to the locally tested files.

**Limits:** trusted internal capabilities are not user authentication, and no automated hosted CI test has run. This is still a prototype and does not autonomously select the next action.
