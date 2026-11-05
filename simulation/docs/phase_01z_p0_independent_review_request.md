# Independent review request — 01-Z and pre-production P0 gate

**Review status: REQUEST DOCUMENTED, NOT PERFORMED.**
**Branch:** `simulation-engine-phase-01z`, descendant of verified 01-Y `a7e0e8e4d1671bc16f5a3c4f9bbd4ee3bb8c4210`.
**Scope:** `simulation/src/carlos_sim/backup.py`, `resumable_play.py`, CLI and tests, policy and CI changes.

An independent reviewer must not treat the author's tests as approval. Review the actual diff, try to break recovery safety on Linux and Windows, and record an independent signed finding before either P0 or 01-Z may be marked APPROVED/CLOSED.

## High-priority reviewer probes

- Verify the backup remains consistent under active WAL writers and simultaneous multi-world changes. Try a writer concurrently committing when `sqlite3.backup` operates. Verify no incorrect manifest revision/time, partial snapshots or silently lost events.
- Simulate a power cut or forced termination before, during and after backup and restore publication; verify SQLite source, old bundles and pre-existing destinations remain intact. Check whether file/parent-directory `fsync` or durability barriers are required for *power-loss* guarantees.
- Race two processes trying to publish the **same backup folder name**. Examine `os.rename` behavior on Linux/Windows when another process creates an empty destination directory between checks; no-overwrite must be guaranteed, or recorded as a blocker until fixed.
- Check Windows NTFS `os.link` support, antivirus/file-lock behavior, long/non-ASCII paths and FAT/exFAT limitations. Choose documented safe fallback if hard-link creation is unsupported **without** risking overwrite.
- Check directory/symlink protection, permissions, user-owned paths, path alias/relative traversal and malicious local files. This module is not a network security boundary.
- Verify a malicious or corrupt `manifest.json` cannot smuggle an old SQLite version, different world ID, forged revision/state digest, extra files, or a database missing command provenance.
- Check rollback when the disk fills, JSON writing fails, copying is interrupted or the target appears during restoration. Ensure source and backup are untouched and temporary files are removed.
- Test restore with an old 13/20 world; **must fail without modifying it**, no editing version numbers to reclassify. A migration requires its own protocol.
- Verify the saved world does not advance while the process is closed, including active player travel and due scheduled NPC actions. Reusing old command IDs must not duplicate a journey, speech, sighting, wait or resource transfer.
- Inspect the player view, world identity and permission boundary. Only local trusted Python may access store/capabilities; no server/network auth was implemented.
- Check the backup commit SHA provenance claim: it is caller supplied and not authenticated; SHA-256 files/manifest are not tamper-proof against a privileged attacker.
- Evaluate checkpoint retention, off-device backup, corruption handling, operator errors and practical disaster-recovery runbook. Test operational restore drills and report RPO/RTO from actual measurements, not guesses.

## Approval bar
Document reproducible independent results, code SHA, Python 3.10/3.13 matrix, Windows test environment, sample backups with manifest checks, integrity and replay validation, and severity-labelled blockers/regressions. Do **not** mark P0 CLOSED merely because CI passed or because this review request exists.

Until then: **P0 OPEN; 01-Z TECHNICALLY_VALIDATED only if latest CI is green, EXTERNAL_REVIEW_DEFERRED; no canonical Carlos history or long-lived-world guarantee.**
