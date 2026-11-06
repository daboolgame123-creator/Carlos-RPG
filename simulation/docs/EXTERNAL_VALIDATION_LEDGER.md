# Carlos RPG — External checks and deferred validation ledger

**Established:** 2026-11-06 by project owner. This ledger separates completed internal testing from testing that genuinely requires a different environment or reviewer. Every new stage updates it when applicable.

| ID | Item | Why external | Current evidence | Status | Revisit trigger |
|---|---|---|---|---|---|
| EXT-001 | Independent adversarial J1c2a source review | Requires a genuinely separate reviewer/agent and judgment not authored by implementer | Internal adversarial steps and 905/905 tests on both Python versions in Actions 42199572310; separate review not performed | **DEFERRED_BY_OWNER / NOT APPROVED** | Before production release, or when owner requests |
| EXT-002 | Production-device/production-server P0 disaster recovery drill | Real filesystem, actual power-loss/OS crash conditions, server/media permissions and rollback cannot be reproduced by a disposable CI runner | Seven-character offline recovery in Actions 42201414528 succeeded on Python 3.10/3.13, verified 37 events, snapshot, replay and continuation | **EXTERNAL_ENVIRONMENT_REQUIRED / NOT VERIFIED** | Before using any valuable persistent world in production |
| EXT-003 | Real Windows backup and restore behavior | GitHub Actions recovery runner was Ubuntu; OS-specific rename and filesystem protection need demonstration on actual target OS | Linux restore and no-replace race regression passes in CI; Windows behavior not run on owner's device | **EXTERNAL_ENVIRONMENT_REQUIRED / NOT VERIFIED** | Before relying on Windows deployment |
| EXT-004 | Untrusted network/player-facing authentication gate | Trusted in-process actor IDs/flags cannot authenticate internet or LAN clients | Current in-process engine only; no public API or trusted gateway certification | **NOT IMPLEMENTED / BLOCK NETWORK EXPOSURE** | Before any untrusted player interface or LAN/API release |

**Policy:** These entries may coexist with `CLOSED_TECHNICALLY` for an isolated simulation feature. Do not describe a deferred item as passed or approved. A known blocking defect in the current stage still prevents technical closure until fixed or explicitly excluded by a pre-approved scoped contract; no silent scope change.

## Source-level evidence

- [J1c2a technical CI](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42199572310) and [full CI](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42199572367), exact code `fcde52a2a40940930f23cd5ee541f79d155332bc`.
- [Independent-of-pytest disposable recovery runner](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42201414528), exact code `f4c1adc552bf9c8a0dae985e5af67477d22baf61`.
- `simulation/docs/phase_04a_j1c2a_executed_recovery_drill.md` gives checksums and limits.
