# Carlos RPG — 03-A5 runtime exhaustion injury technical closure

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-runtime`
Exact **code and test SHA**: `201d79a859ed1fbec0e64583008642e73559537c`
Schema / Rules: **31 / 39**
Status: **CLOSED_TECHNICALLY** for the explicitly scoped, trusted-session exhaustion injury feature.
Whole Phase 03-A: **OPEN**. External independent review: **EXTERNAL_REVIEW_DEFERRED_BY_OWNER**. Production: **P0_PRODUCTION_NOT_APPROVED**.

## Verified evidence on exact SHA

[GitHub Actions run 42269994616](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42269994616)

- `test (3.10)` job `128071767088`: **success**, **1094 passed in 84.04s**, full workflow including smoke, backup and frozen historical parity.
- `test (3.13)` job `128071767609`: **success**, **1094 passed in 116.39s**, full workflow including smoke, backup and frozen historical parity.
- Review PR [#8](https://github.com/daboolgame123-creator/Carlos-RPG/pull/8) is **draft only**. Nothing was merged into main or the institutions/property branch.

## Scope implemented

1. Runtime injury `InjuryRecorded` is admissible only through `injury_authorized=True` in an active trusted local play session. Unlike time-zero bootstrap, it cannot bypass the dedicated runtime guard.
2. Rule `exhaustion` evaluates only a configured present/available NPC with observed, state-held fatigue >= 90. Severity is **exactly fatigue minus 70** (20..30) rather than caller-chosen, and the claimed fatigue value must match current state. No stacking of active injuries.
3. `NPCExhaustionInjuryService.record(...)` is a **trusted in-process** service and NOT an untrusted player/HTTP endpoint. Direct caller access to trusted store methods is outside the security boundary. A future player gateway must not expose this capability.
4. The new command authorization provenance is persisted as `commands.injury_authorized`, including its request hash, and restored on replay. Forgery of the event or removal of recorded command authority fails closed; snapshots/full replay match.
5. State format remains strict with `injuries`, now **Schema 31 / Rules 39** due to the new SQLite command column. Prior 30/38 and historical versions remain rejected without mutation, and all frozen parity/snapshot/backup gates passed on the pinned SHA.
6. The tests verify no automatic resource/HP adjustment, duplicate active injury rejection, impossible fatigue and invalid actor/subject/source, lost session refusal, restore and replay.

## Deliberate limitations and next work (DO NOT CONFLATE)

- This does **not** automatically generate injury when NPC fatigue crosses 90. A trusted application component must explicitly call the service. It also does not model combat, falls, pain impairment, medical evidence, player HP or death.
- Recovery and healing do **not** exist in runtime yet. The pure recovery-transition and readiness prototypes provide no event or gameplay authority.
- The trust capability is an in-process defense, not cryptographic authentication; no remote API or untrusted player should invoke `append(injury_authorized=True)`.
- External review and real-world deployment tests are still deferred; nothing in this technical closure is production approval.

## Next substage 03-A6

Begin with analysis of the real `ScheduledEventCreated/Fired` system and resource-consumption/trade semantics. Introduce a **separate** trusted recovery capability with recorded command provenance. Require actual caregiver/local presence, bounded recovery delay, and funded resources consumed exactly once at a deterministic event boundary; handle cancellation/interruption/travel and forged signal payloads. Preserve old-world rejection; bump schema/rules correctly. Test full restore, snapshot, adversarial event forging, replay, and Python 3.10+3.13 full CI on exact final SHA. Close only after verified.
