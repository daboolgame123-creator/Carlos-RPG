# Phase 01-Z — Technical implementation and P0 candidate review report

**Branch:** `simulation-engine-phase-01z`. **Status: IN_PROGRESS while final CI is pending.**
**Baseline:** 01-Y `a7e0e8e4d1671bc16f5a3c4f9bbd4ee3bb8c4210` — [CI 42040723164](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42040723164), 627/627 tests per Python 3.10/3.13.
**Versions:** **Schema 14 / Rules 21 unchanged**. No new world event type or schema migration.
**P0: OPEN** (backup/recovery candidate implemented, **independent verification pending**).
**External review: DEFERRED**; not APPROVED/CLOSED.

## Work implemented
- `carlos_sim.backup`: creates an independent bundle containing a consistent SQLite snapshot via `sqlite3.Connection.backup()` and a manifest with caller-supplied full 40-character commit reference, captured world/Schema/Rules/revision/logical time, complete DB SHA-256, and per-world state digests and event/command/snapshot counts. Every included world is checked by SQLite `integrity_check` and replay-based `verify()`. No raw copying of a *live* SQLite database, including WAL.
- `verify_backup_bundle`: accepts a complete bundle only; checks hash and version on a detached scratch DB so verification never attempts to rewrite the stored copy. It cannot convert an old world or prove cryptographic authenticity against an attacker who can rewrite both DB and manifest.
- `restore_backup_bundle`: refuses any pre-existing target, copies into a temp DB, checks full replay/integrity again, and creates the destination with atomic create-if-absent hard-linking. Original source and backup are left alone; no overwrite or implicit session switch.
- `ResumableTestSession`: explicitly gated to `disposable_test=True`; new worlds require a trusted fixture callback and a fresh path, resuming requires an existing version-compatible world. It performs a read-only SQLite preflight and full `verify()` before opening a play session. Reopened player is the already registered human-controlled actor. `view()` returns only own scene/status/memory. World logical time remains frozen between sessions; travel resumes on its original schedule and only explicit player `wait()` advances events.
- `scenarios/test_village/play_resumable_demo.py`: optional **disposable experimental** command line; `--new` and `--resume` are mutually exclusive, require `--disposable-test` and a pre-existing backup directory. Checkpoints are independently verified after each accepted mutating command. A command prints its request ID first and allows explicit reuse with `id <request-id> <verb>...` to reject/reconcile duplicate retries. No canonical story import or in-game auto-grant/recovery mechanics.

## Current test evidence
The focused phase-01Z suite adds **16 tests** to the prior 627. The tests cover WAL capture while source continues advancing, frozen snapshot restore, verifying **all** worlds included in a full DB copy, malformed/corrupted backup/manifest, wrong version, missing player, no-overwrite restore, failed destination copy cleanup, inconsistent source, partial fixture failure, snapshot and replay verification, time freeze on restart mid-travel, read-model privacy, invalid request IDs, and no duplicate commands. Tests exercise actual SQLite files, not a mocked event stream.

**Full CI result for implementation and independent CLI smoke:** PENDING until recorded on final SHA. A provisional 643/643 passing run of focused implementation will be cited only when confirmed. Internal review findings and corrections are preserved in Git history, and final validation must refer to final HEAD.

## Known limits and deferred P0 requirements
- **The P0 gate remains OPEN.** An independent review and demonstrated disaster recovery process, including crashes/power loss, filesystem permissions, Windows operational behavior, and attack-model evaluation, are still required before treating player history as durable production data.
- Snapshots inside the DB are not backups; independent bundles are tested but do not yet establish operational retention policies, off-device redundancy or automated restore drills.
- Multiple checkpoints can consume disk. A crash between SQLite committing a command and completion of its next backup can leave a newer live DB and an older last backup. Do not promise zero data loss in that gap.
- The bundle's `code_commit` is *caller-supplied provenance*, not a signed attestation. SHA-256 is not adversary-proof against anyone who can rewrite the DB and manifest together.
- The local session does not provide AuthN/AuthZ across a network. No current user story import, permanent world certification, migration, guaranteed long-lived gameplay, telephone/cloud integration or XP/loot/combat rules.
- A high-privilege local operator can tamper with the DB; do not expose SQLiteEventStore/backup controls to untrusted players.
- No direct modification to `main`, older branch history, or original Carlos story documents.

**Conclusion:** implement and validate this as a bounded, resumable **test-world** loop; keep P0 and independent review explicitly open. Do not launch a canonical long-lived play world until the remaining safety gate is actually approved.
