# Phase 01-V — Independent adversarial review request

**Status:** EXTERNAL_REVIEW_PENDING — DO NOT MERGE / FORMALLY CLOSE.
**Target branch:** `simulation-engine-phase-01v`, compare against `simulation-engine-phase-01u` commit `47dd04ef6928af6c6b76fecdd1b29dc46a653755`.
**Code checkpoint:** `0e70d4d3163b7336ad784848096e65f7edee2576`.
**CI:** [41989436509](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41989436509), 587/587 per Python 3.10 and 3.13, frozen 01-U parity step passed.
**Dependencies:** 01-T and 01-U still EXTERNAL_REVIEW_PENDING; their independent review findings must be reflected in this branch.
**P0:** OPEN. No durable-world safety or production migration certification.

## Read-only independent adversarial checklist

1. Audit the *actual* 01-U→01-V diff, not this assistant's description. Examine scarcity.py, food_navigation.py, assistance_autonomy.py, living_world.py, tests and the CI freeze.
2. Check the failed-forage filter reads only the named actor's real `foraging_attempts` and never reads peer private histories or the remotely true stock to select a destination. Test wrong actor, stale/newer observation, 3599/3600 boundary, and multiple alternatives.
3. Check new hearsay cannot immediately erase personal evidence of an exhausted site, while a later verified direct observation can; preserve existing 01-T `should_adopt` rules and deterministic event replay.
4. Challenge the assistance-request provider filter at 899/900 and 3599/3600 seconds, for `declined`, provider `promise_withdrawn`, requester `request_withdrawn`, promises still open, other requesters and unavailable peers.
5. Verify an actual accepted alternative assistance request can transfer only available goods with correct actor, co-location, audit trail, time, trust, and no double transfer. Reproduce a full depletion/failed forage with several real NPCs.
6. Test independent command atomicity, idempotency, closed session, stale revision, no data change after an event-limit failure, SQLite snapshot/reopen and `verify()` replay.
7. Compare a shared knowledge+navigation+foraging+assistance **enabled** scenario in frozen actual 01-U and new 01-V with the scarcity flag **disabled**. Require event log/state digests and all prior compatibility probes to match.
8. Confirm Schema 13/Rules 18 unchanged, no hidden migration, no P0 closure and no changes to main or original Carlos story files.

Return APPROVED, BLOCKED or INCONCLUSIVE with exact checked SHA, test evidence and file/line references. The implementing assistant's tests and green CI are not an independent sign-off. Do not merge review-only PRs or start unrelated phases.
