# Phase 01-W — independent review request (deferred by user)

**State:** EXTERNAL_REVIEW_DEFERRED. This file is a future handoff, not an independent approval. Do not merge review-only PRs or claim P0 is complete.
**Branch:** `simulation-engine-phase-01w`; tested code commit `8787cf549973d78b1fc471fc86858b23aa422840`.
**Base:** corrected Phase 01-V `6a0f3d473f0eecb856fb2b320e1d6485b032b3bc`.
**CI:** [42021241326](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42021241326), 607/607 per Python 3.10 and 3.13.

## Review checklist

1. Inspect the exact diff in domain.py, movement.py, social.py, store.py, player_gateway.py, tests and CI. Do not rely on the author's report.
2. Prove bound player ID cannot issue NPC-controller commands or move another entity. A future network client must NOT expose store capabilities or allow construction of arbitrary gateways.
3. Try forged player route IDs, origin, destination, fake actor, negative/malformed times, concurrent journeys, early signal firing and cancellation. Verify no teleport, time skip or duplicate arrival.
4. Probe social presence: a travelling player must not appear as a present NPC neighbor or send local speech. Receiver reaction is NPC-controlled; forged remote social messages rejected.
5. Check inspect returns no remote occupant, resources, beliefs, hidden schedules, NPC profile or full state while present or travelling.
6. Check SQLite event batch rollback, stale revision, duplicate command, session closed, snapshot/reopen/replay, raw TimeEngine arrival and multiple due events.
7. Compare genuine 01-V Rules 18 snapshot rejection without mutation, actual 01-R/01-S compatibility, and exact event plus version-neutral semantic state parity to corrected 01-T/01-U.
8. Confirm only disposable test worlds are used, P0 is OPEN, main and original Carlos story files untouched, no unauthenticated network surface.

Return APPROVED/BLOCKED/INCONCLUSIVE with exact SHA, file/line and reproducer; a green CI alone is not a separate review.
