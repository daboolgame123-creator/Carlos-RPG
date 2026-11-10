# MIG-05a — Bounded versioned acceptance, two-world restore and continuation

**Date:** 2026-11-10 UTC  
**Scope/status:** `CLOSED_TECHNICALLY_IN_DISPOSABLE_FIXTURE_SCOPE / MIG05_FULL_MATRIX_OPEN / P0_PRODUCTION_NOT_APPROVED`.

## Reproducible evidence

- Branch: `engineering/mig05a-restore-matrix-20261110` based on verified MIG-04c head `89b0812494ca60b0c81886f905a4fde1344fc687`.
- Initial tested code/workflow commit: `e20a27fccf118cbeacb16afedb8c926ac40dae3b`.
- [GitHub Actions #42806571828](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42806571828) **SUCCESS** on Python 3.10 and 3.13.
- Historical source authored by pinned `a6c20e3edfbe85cc68819cd4fadd909472b21fd5` runtime (Schema 41, Rules 56), two worlds, **53 genuine events**, **7 authentic commands**; target pinned to `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2` (42/57).
- Executable research probe: [mig05a_restore_matrix.py](../probes/mig05a_restore_matrix.py).

## Checks that actually ran and passed

1. `SQLiteEventStore.load()` on a separately copied original 41/56 world fails with `UnsupportedVersion` and does not alter the copied file.
2. Preflight recognizes legitimate original command/event hashes. A **forged, unknown event with both its own hash AND originating command request hash recomputed consistently** passes cryptographic receipt preflight, but is rejected by **target reducer semantics**; no invalid destination is published. This demonstrates hash validity alone is insufficient.
3. Modified source Rules/version **58** is rejected before an output target can be published.
4. The existing test-only reconstruction preserves both worlds' full state, receipts, event history, and explicit target version. Target `verify` and `load` agree.
5. Actual 42/57 `create_backup_bundle` → `verify_backup_bundle` → `restore_backup_bundle` preserves both worlds; repeated restore to occupied target is rejected. Tampered manifest checksum fails closed, publishing no restored target.
6. After restore a trusted explicit `TimeEngine.advance` issues **one new event** for the secondary world. Reopening the saved world proves the new event survived. Duplicate command ID is rejected; resources, entities, locations and copper are unchanged; primary world remains identical.
7. Original predecessor source bytes retain their SHA-256 digest before/after all proof steps.

The exact source/target files are disposable CI fixtures only. Test suites do not enable a runtime migration entry point or change startup/load version enforcement.

## Still missing for full MIG-05 / P0

- Additional historical event classes: loans, property/claim transfer, injuries, player decisions and physical cash-custody transitions.
- Arbitrary long-lived worlds, unknown historical schemas beyond pinned 41/56, Windows, genuine power loss, independent approval and deployable migration CLI.
- Tested source uses **53 events** and is not representative of all **73** event kinds. Even the separate 97-event courier test (MIG-05b) cannot claim exhaustive compatibility.

**Release policy:** `engineering/contracts/migration_41_56_to_42_57.json` remains `mode=inventory_only`, `migration_approved=false`. No production migrations, no `main` changes, no automated switch to a new save format. Full MIG-05 remains OPEN.
