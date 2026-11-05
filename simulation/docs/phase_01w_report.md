# Phase 01-W — Local player gateway: technical validation report

**State: TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED — NOT APPROVED/CLOSED.**
**Branch:** `simulation-engine-phase-01w`, forked from tested corrected 01-V at `6a0f3d473f0eecb856fb2b320e1d6485b032b3bc`.
**Tested code commit:** `8787cf549973d78b1fc471fc86858b23aa422840`.
**Evidence:** [CI 42021241326](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42021241326) — **607/607** tests on Python 3.10 and 3.13, with actual disposable CLI smoke, frozen 01-T and 01-U semantic/event parity, and real 01-V old-world rejection.
**Version:** Schema 13 / **Rules 19** (new player scheduled-travel semantics). **P0 OPEN**; no automated migration, no long-lived games, no original Carlos story import.

## Delivered

- `PlayerGateway` binds one trusted, local `controller='player'` entity in one world. It never adds the player to NPC profiles or automatically chooses a player decision.
- `inspect()` returns only local present entities, incident roads, and public place name. During travel it returns only route ID and remaining seconds; no global `WorldState`, distant positions, hidden resources, beliefs or secrets.
- `move(route_id)` schedules a durable, authorized `__player_travel` signal with exact known route duration; the player remains at origin until a genuine `ScheduledEventFired` reaches its due time, where arrival is projected exactly once. A player cannot move, talk or appear co-located while travelling.
- `wait(seconds)` advances logical time and ordinary existing NPC autonomy using the injected/shared living-world engine; there are no new automatic commands for Carlos. Time advancement, due arrival, decisions and NPC actions follow existing atomic event-batch semantics.
- `interact(npc_id, kind, text)` sends only a user-selected local social speech act to an NPC, and the existing NPC social reducer decides the response. No generated or forced NPC cooperation, inventory transfer or secret disclosure.
- `movement.validate_player_schedules` verifies player controller, one journey per player, adjacent existing route, exact start/due duration, location, and non-interrupting signal. Store rejects trusted player-travel scheduling outside an active session; cancelled active travel is rejected.
- `scenarios/test_village/play_local.py` offers a tiny terminal game (look/move/wait/talk/quit) in a TemporaryDirectory SQLite world **destroyed on exit**. Command results are sanitized and no original story files are read.

## Adversarial and compatibility evidence

- **14 new test cases** on top of corrected Phase 01-V's 593 tests (607 total): local-only inspect, real event-backed travel with 89/90-second boundary, two explicit route hops, temporary absence from NPC observation, real NPC reaction, reject remote dialogue, spoofed actor/route/duration, stale revision and malformed ID, stopped session, atomic event-budget failure, snapshots and SQLite reopen/verify, duplicate social/clock command rejection, and direct TimeEngine arrival.
- GitHub Actions actually runs the disposable CLI command loop and confirms a completed road journey and cleanup.
- CI checks out genuine 01-V at `6a0f3d4`, creates and snapshots an actual **13/18** SQLite test world, and demonstrates Rules 19 rejects opening it with `UnsupportedVersion` **without mutating metadata, event hashes or snapshots**. No migration is attempted.
- All prior 01-R/01-S saved-world rejections remain enforced.
- Compared knowledge and navigation decisions against frozen corrected 01-T and 01-U runtime scripts: **exact event digests, time, revision and event counts**, plus state-semantic digest excluding only the deliberate `rules_version` field. Full state digest is kept separately and necessarily differs across the 18→19 version bump; no resource, belief, NPC or event fields are stripped.
- Replay `SQLiteEventStore.verify()` and after-close/reopen player trip completion pass; no direct state edits or unlogged player movement.

## Explicitly not done

- No network, API, public client, login or authenticated remote player controls: this is a **trusted local Python application facade**, not AuthN/AuthZ.
- No 01-X full player visibility/knowledge rules, RPG health/XP, combat, manual NPC takeover or interaction with invisible/remote actors.
- No true player long-term save, migration tool, independent review, external deployment or imported Carlos story; P0 backup/restore remains OPEN.
- Original branches/PRs for 01-T/01-U/01-V and `main` have not been merged or changed by this phase.

**Outcome:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED. Future 01-X may consume this trusted facade subject to bounded visibility design; formal approval needs a separate reviewer and P0 remains a prerequisite for preserved worlds.
