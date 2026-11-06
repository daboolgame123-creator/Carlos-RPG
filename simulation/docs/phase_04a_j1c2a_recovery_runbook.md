# J1c2a — Offline recovery drill / independent acceptance runbook

**Status: PROCEDURE PREPARED — NOT EXECUTED OR APPROVED.**
Date: 2026-11-06. Target branch: `simulation-engine-phase-04a-j1`.
This document is an operational procedure, not an independent-review sign-off and not evidence of a successful disaster recovery.

## Safety and scope

- Run only on an **authorized, disposable, non-production local world**, in a clean checkout of an explicitly recorded commit.
- **Never** copy real player saves, staff data, backup archives, hashes of private material, or secrets into public GitHub issues.
- Keep source database and its WAL/SHM companions untouched. Never restore into the original file or an existing destination.
- No public network endpoint. Internal `actor_id` / `claim_transfer_authorized` remain trusted in-process inputs, not authentication.
- If the reviewer cannot establish a separate identity/environment from the implementation author, record this as an **internal rehearsal** only. Do not call it independent sign-off.

## Prerequisites and identity

1. Independently clone the repository and checkout the **exact final J1c2a HEAD**, not an older report's reference. Record `git rev-parse HEAD`, `git status --porcelain`, OS, architecture, `python --version`, and `sqlite3.sqlite_version`.
2. Install dependencies using the repository's current documented test installation mechanism, e.g. from `simulation/`: `python -m pip install -e ".[test]"` **only if** supported by that checkout. Otherwise use the CI workflow's exact install command and document it.
3. Keep all run outputs in a disposable local directory outside the repository. Do not commit database bundles.

## Phase A — automated preflight (same reviewed HEAD)

From `simulation/`, with the package and pytest available:

```sh
python -m pytest -q tests/test_j1c2a_recovery_gate.py tests/test_j1c2a_recovery_protection.py
python -m pytest -q
```

Record all test totals, failures/skips, start/end timestamps and Python versions 3.10 and 3.13. Check the **actual resulting CI runs on the exact final SHA**. A missing run is **unverified**, not green. A symlink test skipped by the platform is not evidence the symlink protection was exercised.

## Phase B — separate offline backup and restore rehearsal

1. Create a disposable Schema 28 / Rules 36 world with at least **two actors** and original registered claim units. Use the current engine's supported scenario bootstrap, not an arbitrary fabricated SQL state.
2. With a live SQLite WAL transaction environment, create (a) one accepted historical-claim assignment, (b) one still-open registered claim offer, (c) a snapshot, and (d) a sequence of committed events. Record the exact before-state using `SQLiteEventStore.verify(world_id).to_dict()`, including `registered_claim_balances`, `registered_claim_offers`, custody lots, resources, revision, time, and event/snapshot counts.
3. Call `create_backup_bundle(store, world_id, NEW_BUNDLE_DIRECTORY, code_commit=FULL_REVIEWED_SHA)` while the source world remains open. Verify with `verify_backup_bundle(bundle)`.
4. Record the returned `database_sha256`, `database_bytes`, `schema`, `rules`, `worlds[*].state_sha256` and an independent local `sha256sum world.sqlite` (or PowerShell `Get-FileHash -Algorithm SHA256`). Do not publish private file content.
5. Modify the **source world after backup** (e.g. cancel its pending offer). Verify that source now differs from the frozen backup. Restore to a brand-new filename using `restore_backup_bundle(bundle, NEW_TARGET_PATH)`.
6. Reopen the recovered database and run `SQLiteEventStore.verify(world_id)`. Compare its complete canonical state against the frozen before-state. Independently check `PRAGMA integrity_check` equals `ok`, stored event and snapshot counts match the manifest, and the previously pending offer can be accepted after opening an authorized local session. Check registered claim quantities are conserved and physical goods/custody do not teleport.
7. Reopen the original source: verify that it still contains the **post-backup change**, proving no restore overwrote it.

## Phase C — failure-atomicity and compatibility

Run **separate fresh disposable targets** for each negative case; record exception type and destination existence:

- Corrupt one byte of a **copy** of the backup SQLite file; refuse restore; do not create output.
- Forge a **copy** of manifest's revision or state hash; refuse restore; do not create output.
- Attempt restore to an existing normal file containing a sentinel; refuse without modifying its bytes.
- Attempt restore to a preexisting symlink (where supported); refuse without modifying its target.
- Refuse a genuine older Schema27 / Rules35 world on current engine without modifying the older SQLite bytes. **Never** call rejection a successful migration.
- If a run fails after staging but before publication, verify no final target was published and examine whether any temporary staging file remains. Report this rather than asserting crash resilience from ordinary exception testing.

## Evidence packet / sign-off template

- Reviewer name/identity and organization or genuinely separate agent/environment; independence explanation:
- Reviewed full commit SHA, branch, dirty checkout yes/no:
- OS/filesystem, Python/SQLite versions:
- Command transcripts, test totals and skips per interpreter:
- Disposable world seed/setup and exact reversible backup/restore commands:
- Original source checksum before/after, bundle checksum, manifest checksum, recovered checksum:
- SQLite integrity and full replay verification results, claim balances, pending offer statuses, event/snapshot counts:
- Corrupt backup, forged manifest, existing-file/symlink, old-schema refusal outcomes:
- Findings (ID, severity, reproduction, fix SHA, retest outcome):
- Operational restoration/recovery procedure approved by project owner (yes/no, date):
- Independent reviewer **APPROVED / REQUEST_CHANGES** with explicit date and reviewer identity:

## Hard gate

The J1c2a stage is **OPEN** until independent signed results on the final HEAD, both interpreter CI checks, and separately accepted P0 recovery are documented. The existence of this runbook, its automated tests, or an internal rehearsal does **not** close J1c2a or authorize J1c2b.
