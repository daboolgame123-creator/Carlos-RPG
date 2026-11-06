# Carlos RPG — 03-A8a paid recovery reservation integrity closure

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-treatment-integrity`
**Exact verified code and test SHA:** `75dc81412ba65be4a53b0f3e8f7c257a1d5b68c4`
Schema 32 / Rules 42
Status: **CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER**
Parent 03-A remains **OPEN**. Production remains **P0_PRODUCTION_NOT_APPROVED**.

## What was fixed
Previously, a trusted event command could submit `RecoveryStarted` without the paired `ScheduledEventCreated` in the same transaction. The reducer would deduct caregiver-owned food and leave a pending treatment with no scheduled completion, even though the ordinary recovery service always submitted the pair. This was an integrity gap in the generic trusted append path.

`validate_treatment_reservations` now runs at the **complete command boundary** and at the **completed SQLite replay boundary**. It checks that each pending paid treatment has exactly one scheduled signal with the matching treatment ID, schedule ID and due time, and that no completed/interrupted treatment retains an appointment. It rejects orphaned, forged and duplicated recovery schedules. Crucially, it does not run between the two legitimate events of one atomic start command.

The transaction rolls back if the schedule is missing: no loss of food, no partial treatment, no persisted command. Regular funded recovery, interruption after caregiver travel, snapshots and full replay continue to work. There are no new SQLite columns or WorldState fields; the acceptance policy change bumps **Rules 41 → 42**, while Schema stays **32**.

## Exact-SHA test evidence
[GitHub Actions run 42290286511](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42290286511)

- Python 3.13 job 128141623462: **success**, **1125 passed in 99.08s**; complete workflow, frozen parity and smoke tests green.
- Python 3.10 job 128141623705: **success**, **1125 passed in 126.95s**; complete workflow green.
- Test `test_treatment_reservations_03a.py`: rejects orphaned paid treatments without a schedule, validates no resource debit after failed transaction, verifies legitimate treatment and replay, rejects mismatched/duplicated appointments.

## Limits and routing
- Draft PR [#12](https://github.com/daboolgame123-creator/Carlos-RPG/pull/12), unmerged; main and institution/law branch unchanged.
- This validates a trusted **in-process** store, not the authorization of an external API.
- Task **03-A7c cross-NPC observation** stays `DECISION_REQUIRED / WAITING_DECISION`. No new automatic symptom disclosure, diagnosis or omniscient injury knowledge was authorized.
- No external independent audit took place; its deferral is not an endorsement. No deployment/Windows production backup test was claimed.
