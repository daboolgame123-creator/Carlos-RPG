# Carlos RPG — 03-A6 funded scheduled NPC recovery: technical closure

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-recovery`
Verified **code and tests SHA**: `2ca67e83747eadda75dc63c56242f749eb01645c`
Schema / Rules: **32 / 40**
Scope status: **CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER**
Whole Phase 03-A: **OPEN** — combat, accidental damage, illness, incapacitation, NPC HP and health behavior still unimplemented; do not describe the entire health phase as complete.
Production: **P0_PRODUCTION_NOT_APPROVED**.

## Exact-SHA test evidence

[GitHub Actions run 42273069815](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42273069815)

- `test (3.10)` job 128082339721: **success**, `1105 passed in 155.91s`, full workflow including frozen historical parity, recovery tests, backups and smoke.
- `test (3.13)` job 128082340398: **success**, `1105 passed in 77.71s`, same workflow.
- No failures and no test skipping reported in the pytest run logs.
- [Draft PR #9](https://github.com/daboolgame123-creator/Carlos-RPG/pull/9) remains open; no merge to main, law or property branch.

## Implemented and verified

1. A **trusted in-process** `NPCRecoveryService.start` starts one supportive-care treatment of a configured injured NPC with a co-located available caregiver. Neither HTTP nor untrusted player commands have access.
2. Starting treatment consumes **exactly 1 unit of caregiver-owned `food`**, immediately and atomically, from a known finite balance. No food, no treatment. The ledger `WorldState.treatments` records identity, subject, caregiver, site, resource and amount, start time, due time, schedule ID and status.
3. A protected `ScheduledEventCreated` appointment `{"__npc_recovery": treatment_id}` matures only after **600 logical seconds**. Its improvement is fixed at **10 severity points**, never caller-adjustable. `ScheduledEventFired` performs the transition deterministically and once; no passive healing before due.
4. If either party is no longer available at the original site at due time, the record becomes `interrupted` with **no healing** and no unexplained food refund. The adversarial test moves the caregiver to another location during the treatment.
5. Fake events, unauthorized schedules, generic cancellation of paid treatment, duplicate pending treatment, fake effects, missing food, and prior-version snapshots fail closed. The transaction preserves the original state on refusal.
6. A dedicated `commands.recovery_authorized` bit preserves capability provenance through replay. Hence **Schema 32 / Rules 40** for the new treatment collection and SQLite command column. Historical versions are rejected without modification.
7. SQLite reopen, full replay, snapshots and existing frozen parity/smoke workflows are verified on both Python versions.

## Limits and outstanding risk

- The source of existing injuries is the verified 03-A4 bootstrap or 03-A5 exhaustion event only. This is not a general combat, disease, fracture or emergency medical system.
- Supportive care consumes food and scheduled time; it is not medical efficacy validated against simulation physiology. A caregiver leaving after treatment start causes interruption at due time, not immediate interruption.
- The recovery feature is a trusted internal engine interface; there is **no player-facing authenticated command**, no automated NPC decision to seek treatment, and no user/AI authority to invent resources or injuries.
- No automatic HP reduction/refill is implied. NPC vital stats need their own explicitly designed model.
- External independent review remains deferred, not passed. Production and legal branches remain separate.

## Route for remainder of 03-A

Before any additional injury cause or status effects, analyze AI/NPC decision integration and knowledge isolation. Do not assume characters know another NPC is hurt without observation. Define consistent symptom and capability effects, bounded incapacitation/death policy, illness/accident/combat source provenance, and gateway visibility; implement and exact-SHA test only the subset prioritized by the roadmap. If original 03-A is narrowly "injury and recovery mechanics", this work supplies a restricted functional subset, not every damage origin.

All continuation follows `AGENTS.md` analyze-plan-implement-test-document and separate branch discipline.
