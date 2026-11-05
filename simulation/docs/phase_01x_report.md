# Phase 01-X — Technical validation report

**Status: TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED — NOT APPROVED/CLOSED.**
**Branch:** `simulation-engine-phase-01x`.
**Baseline:** 01-W SHA `3fb18d3222ebdc08307d393bab8603a5726dda63`, [green 607-test CI](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42021905506).
**Version:** Schema 13 / Rules 20, no migration, no saved-state shape changes.
**P0: OPEN.** **External independent review: DEFERRED.**

## Implemented and internal review
- `PlayerGateway.observe`: a deliberately invoked local observation, event-authorized and replay-valid, while `inspect` remains side-effect-free. The disposable terminal's `look` records sight; `remember` returns past observations and addressed testimony.
- `PlayerGateway.recall`: player-scoped remembered observations and incoming hearsay sourced solely from integrity-verified event logs, not present omniscient world state. Records logical timestamps and speakers.
- `NPCSocialService.share_food_claim_to_player`: NPC-side trusted delivery of an existing belief only, with co-location, travel, recipient role and same-tick hearsay restrictions; no ability for Carlos to force speech.
- `PlayerObserved` and `PlayerHearsayReceived` need trusted event capabilities and are checked during replay. Hearsay remains `unverified`, even if the original NPC believed it.
- No changes to main, original story files, resources, NPC decision algorithms, or any migration tool.

## Threats and regression tests
New tests cover absent/remote sight, tampered occupants, actor spoofing, stale revisions, traveling, duplicate commands, immutable source NPC belief, remote speech, isolation between two players, session closure, saved snapshots/reopen and full `verify()`. The existing 607 tests also run on both supported Python versions. CI includes a real 01-W 13/19 saved database rejection test with intact metadata/events/snapshots.

**Internal review risk:** This is a trusted Python-local gateway, not network authorization. Full-ledger memory scans are appropriate only for disposable test worlds; long-lived save/recovery and read-model scalability remain deferred. A player-facing NPC speech-selection policy is not implemented, so NPC statements do not spontaneously appear in the temporary CLI.

## Test evidence
**Tested implementation SHA:** `2640eb76ca94c5e34ab509d423f597860fa3d45f`. [CI run 42033754979](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42033754979) finished **SUCCESS**, **615/615 tests on Python 3.10** and **615/615 on Python 3.13**, with the 01-W disposable CLI smoke, original compatibility/parity gates, and a real frozen Phase 01-W Rules 19 SQLite file rejected unchanged under Rules 20. This is 607 inherited plus eight new 01-X tests; no independent approval.
    
Intermediate red CI runs identified an immutable tuple-vs-list comparison bug and stale hard-coded Rules 19 expectations in regression/CI checks; both were corrected without removing semantic parity assertions. **A fresh green CI run on the final documentation commit is additionally required before describing that later SHA as green.**
