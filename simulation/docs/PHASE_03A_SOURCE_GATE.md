# Phase 03-A — injury-source evidence gate

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-validation`
Status: IMPLEMENTED_AS_FAIL_CLOSED_PROTOTYPE / TEST_EXECUTION_PENDING
Code: `simulation/src/carlos_sim/injury_source_gate.py` at `c13e5f03`
Tests: `simulation/tests/test_injury_source_gate_03a.py` at `ac39da87`

## Verified source audit
An arbitrary `DomainEvent` object is caller-constructible; it is **not proof** of durable SQLite admission, trusted capability, or causality. The engine's existing `PropertyTaken`, `MarketTradeExecuted`, `PlayerVitalChanged` (test-only), `NPCObserved`, `PlayerObserved`, and `PropertyClaimFiled` are **not** authorized injury-causing events. A physical theft event does not establish bodily harm. Therefore `evaluate_injury_source` fails closed for ALL current event types, returning `authority_to_record_injury=False`, `causally_proves_injury=False`, `current_injury_created=False`. It does not add a persistent record or new credentials.

## Required explicit trust boundary before persistent InjuryRecorded
1. Define an actual `InjuryCauseRecorded` or equivalent source generated only by a trusted rule, not arbitrary text.
2. Record capability provenance in `commands` and reproduce it in `load()` event replay, including snapshot and corruption tests. Do **not** reuse `rpg_authorized` as general injury authority.
3. Define immutable bounded NPC injury collection and event transition, with Schema/Rules version bump and genuine previous-SQLite rejection without mutation.
4. Require existing source event ID/sequence, matching injured subject, exact logical time, deduplication, trusted simulation mode, and atomic rollback for fake or stale events.
5. Test complete pytest on Python 3.10/3.13, adversarial and feature-off parity on exact code SHA. All subsequent recovery must follow a real scheduled action with cost and explicit event.
6. Keep `PlayerGateway` knowledge constrained, and do not leak private NPC injury details through generic responses.

## Test status and why it remains open
`simulation-engine-phase-03a-validation` matches the configured push workflow branch glob. A code-and-test push occurred. The available GitHub connector is limited to PR-triggered runs when querying a commit and returned no run; direct Git clone in this container failed DNS resolution. **No exact-SHA full CI success has been observed in this session.** Run `python -m pytest -q tests/test_injury_source_gate_03a.py tests/test_injury_contract_guards_03a.py tests/test_injury_intake_03a.py tests/test_injury_transitions_03a.py tests/test_recovery_readiness_03a.py` and `python -m pytest -q` before proceeding to Schema 30/Rules 38. Do not close 03-A or claim any character has actually been injured or healed.

No main branch, 04-A branch, SQLite schema, or event reducer changed in this prototype.

## 03-A candidate registry prototype (2026-11-06)

Added `simulation/src/carlos_sim/injury_registry.py` (commit `f6d442bd`) and `simulation/tests/test_injury_registry_03a.py` (commit `a9511c02`). The pure functions validate a **candidate**, not world state, and construct detached injury entries without mutating the provided registry. They reject duplicate injury IDs, invalid key-to-record correspondence, non-existent subject IDs, inconsistent injury status/severity and future-dated entries.

**Local isolated pytest:** 11/11 passed on a local copy of this pure code. Package imports were adapted for the temporary isolated directory; this is not evidence that the exact GitHub SHA passed the full engine test suite, snapshot/replay or GitHub Actions.

**Still blocked:** persistent injury ledger and Schema/Rules bump must wait for exact-SHA integration tests. No `WorldState`, SQLite, event reducer, HP, permissions or recovery clock behavior changed by this addition.
