# MIG-04c — SQLite Online Backup API under concurrent WAL writer

**2026-11-10 — CLOSED_TECHNICALLY_IN_DISPOSABLE_SCOPE / P0_PRODUCTION_NOT_APPROVED**

## Pinned proof

- Branch: `engineering/mig04c-wal-backup-20261110`
- Tested commit: `1c6117b6fedd33a45ce9a742b90273e0145c8d47`
- [GitHub Actions run 42799745554](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42799745554): **SUCCESS**, Python **3.10** and **3.13** (both jobs).
- Historical original 41/56 source: `a6c20e3edfbe85cc68819cd4fadd909472b21fd5`; target 42/57 runtime: `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`. The authentic two-world predecessor fixture was generated in each CI job, preserving historical events and commands. No production data.
- Probe: [mig04c_live_backup_probe.py](../probes/mig04c_live_backup_probe.py). CI workflow is scoped to the research branch and has read-only token permissions.

## Results

| Evidence | Python 3.10 | Python 3.13 |
| --- | ---: | ---: |
| Actual concurrent WAL writer commits | 30 | 30 |
| Atomic snapshot-prefix commits | 30 | 30 |
| SQLite Backup API progress calls | 2,771 | 3,471 |
| `integrity_check` / `foreign_key_check` | PASS | PASS |
| No torn multi-table transaction (`n`, `total`, contiguous ledger) | PASS | PASS |
| Historical game-domain receipts unchanged in live source and independent backup | PASS | PASS |
| Strict old-version provenance preflight then full 42/57 reconstruction | PASS | PASS |
| Target game-state replay verification for both worlds | PASS | PASS |
| Existing target protected against replacement | PASS | PASS |
| Original old fixture byte-for-byte unchanged | PASS | PASS |

A test-only writer committed two related SQL updates transactionally in each of 30 transactions while the SQLite Online Backup API copied a WAL-mode source. The copied database was normalized to DELETE journal mode **after successful, closed Backup API capture**, without touching the active WAL source. This permits the existing strict `preflight` to operate on an immutable isolated copy. The test guarantees a coherent observed prefix, not a promise to capture commits that occur later than the backup snapshot.

## Failed attempts and corrections

- [42799036459](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42799036459): **FAIL** — prototype left backup-reading SQLite connections open, and the strict legacy WAL/SHM preflight correctly rejected the sidecars.
- [42799405210](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42799405210): **FAIL** — the completed backup preserved the source WAL journal mode; preflight/reopening could regenerate WAL sidecars. Normalizing only the isolated completed backup to `journal_mode=DELETE` fixed this.
- [42799745554](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42799745554): **SUCCESS** on both Python versions after both fixes.

## What was **not** proven

- The concurrent writer updated **test-only probe tables** on a copy, not live event commands from the running game.
- Actual mains-power failure, fsync/durability on Windows, multi-process game writers or long-lived save compatibility, arbitrary schemas, and the full domain/event semantic matrix remain **unproven**.
- This is not a released migration command; no change to `SQLiteEventStore`, application startup or existing version refusal was made.
- `engineering/contracts/migration_41_56_to_42_57.json` remains `mode=inventory_only` and `migration_approved=false`. Do not switch P0 status based on this research.

**Decision:** MIG-04c disposable concurrent WAL-backup proof closed technically. Proceed to MIG-05 semantic matrix, Windows and independent P0 review on separate gates. No production migration or merge to `main`.
