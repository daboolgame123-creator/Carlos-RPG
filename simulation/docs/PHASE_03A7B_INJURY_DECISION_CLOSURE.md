# Carlos RPG — 03-A7b self-injury decision integration closure

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-injury-decision`
**Verified code/tests SHA:** `73da9660c7e7c275490f3065990d6a72af65f836`
Schema / Rules: **32 / 41**.
Status: **CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER**.
Parent 03-A: OPEN (not a complete RPG combat/illness system). Production: P0_PRODUCTION_NOT_APPROVED.

## Exact-SHA automated evidence
[GitHub Actions run 42284128589](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42284128589)
- Python 3.10 job 128120434985: **success**, **1121 passed in 159.72s**; full workflow including historical parity/snapshot/replay checks green.
- Python 3.13 job 128120434626: **success**, **1121 passed in 116.10s**; full workflow green.
- Draft PR [#11](https://github.com/daboolgame123-creator/Carlos-RPG/pull/11) remains unmerged; nothing changed in main or institutional law branch.

## Exact scope
1. A configured NPC with **its own** active injury severity >=20 prioritizes deterministic `rest`, instead of normal utility choices. Scoring and reason use that same NPC's self-injury record only. Untouched minor cases keep legacy choices.
2. `NPCDecisionRecorded` reducer verifies this override so the event log cannot claim unwarranted `work` or `forage` through forged payloads. Decisions survive SQLite restart/replay and snapshot.
3. `LivingWorldEngine` suppresses autonomous forage and navigation for a severely injured NPC rather than bypassing the forced rest policy. `NPCActionStarted` prevents stale pre-injury decisions from starting nonrest activity.
4. `rest` can reduce fatigue through existing action mechanics, but does **not** heal injury severity or create free supplies. Healing remains solely under the 03-A6 funded scheduled treatment rule.
5. No peer injuries are read to decide a character's action; 03-A7a isolated advisory remains read-only. No change to NPC cross-knowledge, observation, social perception, player gateway or health diagnoses.
6. Bumped **Rules 41**, not Schema: no persisted column or collection added. Current pin tests and CI updated; frozen historical baseline data and hash values unchanged.

## Remaining stage boundaries
03-A7c, others' visible injuries/knowledge propagation, requires an explicit observation contract. Visibility alone must not reveal diagnosis, severity, hidden cause, or other NPC's private memory. Mark **DECISION_REQUIRED** pending scoped rule approval. Do not infer medical knowledge automatically from shared room.

Accidental harm, combat damage, disease, death, NPC HP, treatment efficacy, client knowledge and production testing remain outside this closure. Independent external review is deferred, not passed.
