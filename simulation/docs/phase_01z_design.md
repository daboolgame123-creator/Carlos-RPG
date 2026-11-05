# Phase 01-Z — resumable *disposable-test* play and preflight P0 backup evidence

**Baseline:** 01-Y `a7e0e8e4d1671bc16f5a3c4f9bbd4ee3bb8c4210` — [CI 42040723164](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42040723164), 627/627 on Python 3.10 and 3.13.
**Branch:** `simulation-engine-phase-01z`. **Status:** IN_PROGRESS; external independent review deferred; P0 OPEN until independent assessment of restore/recovery.
**Types:** persistence/integration/security (no new game events/behavior rules).

## Dependency and honest scope
ROADMAP.md §15 requires backup/restore verification before 01-Z or any continued world. Previous engine has event replay and snapshots *inside one SQLite file*, but no independent consistent copy. Implement a restricted P0 **candidate** first; it does not mean P0 is formally CLOSED without independent review. Then test a restart across two actual `SQLiteEventStore` objects in a **non-canon, explicitly disposable** scenario; don't advertise production-grade long-lived saves.

## Candidate backup contract
- `create_backup_bundle(store, world_id, new_bundle_path, code_commit)` uses `sqlite3.Connection.backup`, **not raw copying of an open database**. Build a self-contained temporary folder with `world.sqlite` and a separate `manifest.json` (format version, code commit, UTC time, SQLite file SHA-256, original target world, engine Schema/Rules, ordered per-world revision/time/full-state digest/event count/command count/snapshot count). Only publish a complete bundle; never overwrite or mutate a previous bundle. Verify **all worlds** in copied DB with `PRAGMA integrity_check` and `verify()` before publication. A checksum detects accidental corruption, not malicious rewriting by a privileged operator.
- `verify_backup_bundle(bundle)` checks a known folder format, secure file shape, hash and metadata and verifies a **scratch copied DB** with the current code. Exact Schema/Rules required; wrong version fails closed with no conversion. No internet, external API or personal data.
- `restore_backup_bundle(bundle, new_db_path)` requires a **new target** and valid parent directory; it never modifies an existing DB. Copy into a fresh temp file; verify again before atomically creating destination; cleanup on failure. Never move or rewrite the original bundle or the live database. Caller must verify recovered play and (if needed) deliberately switch to the new path.
- Failures remain explicit; no silent world recreation, automatic migration or destination overwrite. No public network or untrusted HTTP entry points.
- Source git commit is caller-provided 40-hex metadata; cannot claim this is signed provenance or that manifest is a backup if backup/restore was never tested.

## Scoped resumable play
Provide a trusted, local `ResumableTestSession`:
- create only with an explicit disposable-world setup callback and a fresh database path; reopen only an existing, verified, schema-compatible, unambiguous `world_id` plus player identity; no auto-reset or overwrite;
- `TimeEngine.open_session` is process-local: closing/reopening does **not** advance logical time or fire due events; scheduled travel resumes with its original deadline, and only a player's subsequent `wait` advances it;
- identical client request IDs cannot repeat a committed event. Use existing command IDs and compare revisions/events after restart; no attempt to guarantee exactly-once responses over HTTP;
- checkpoint method produces independent tested backup bundle. No automatic rewrite of story files, `main`, source DB or old saves.

The experimental demo remains **explicitly disposable**; an opt-in example may persist between two process starts in a test directory, but cannot be labeled a durable game until P0 independently reviewed.

## Acceptance gates
1. Open live SQLite backup, including WAL; continue to write after backup and confirm frozen archive point; deliberately corrupt db/manifest, wrong version, target exists, missing world, malformed commit, concurrent/replayed command and verify that no target is partially published or overwritten.
2. Exercise restore into isolated path, `PRAGMA integrity_check`, replay from genesis vs snapshot, exact latest event/command/state comparison, reopening and a new command without duplicate output; check failed restore leaves original and bundle intact.
3. Reopen a player **mid-travel**: verify same time, location remains origin/in transit, reissue old command ID rejected, only explicit wait completes travel, memory/status is own view, and NPC decisions are not overwritten.
4. Full regressions and original parity checks on Python 3.10/3.13 at final SHA. Explicitly document P0 **OPEN / independently unreviewed** and external review deferred.

**No new Schema/Rules expected:** remain **14/21**. If tests require new saved event interpretation or table shape, reassess explicitly. No permanent story import, phone/server access, automatic XP/loot/combat or untrusted plugin invocation.
