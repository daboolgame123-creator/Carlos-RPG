# 04-A / J1c2a — Mandatory stage closure gate

**Adopted:** 2026-11-06. **Authority:** user rule: DO NOT start any following stage/substage until its predecessor is fully completed, reviewed, tested, documented and explicitly CLOSED. See repository-root `AGENTS.md`.
**Scope:** existing registered *historical claim* handshake, NOT legally recognized title. Do not begin J1c2b implementation, including schema migrations or new judicial/title reducers, while J1c2a is OPEN.

## Verified evidence (not equivalent to formal closure)

| Check | Status | Concrete evidence |
| --- | --- | --- |
| Planning before coding | PASS | `phase_04a_j1c2_design.md`; original J1c2a bounded scope and risks |
| J1c2a implementation | PASS | `registered_claims.py`, `domain.py`, `rights.py`, `store.py` |
| Adversarial + full regression | PASS | [CI 42137905742](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42137905742) **897/897 passed each** on Python 3.10 and 3.13. [CI 42137905809](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42137905809) adversarial workflow success on both versions |
| Additional internal code review | PASS **internal only** | `phase_04a_j1c2a_followup_review.md`, including 3 extra probes, known trust limitations |
| Documentation/roadmap | PASS | `phase_04a_j1c2_report.md`, `ROADMAP.md`, `ROADMAP_CHANGELOG.md` |
| Genuine independent external adversarial approval | **OPEN / BLOCKING** | `phase_04a_j1c2_independent_review_request.md` defines test scopes; **no signed separate reviewer report exists** |
| Production recovery / backup P0 evidence required for full acceptance | **OPEN / BLOCKING** | historical snapshot and version rejection tests are not a full independently demonstrated production backup-and-restore drill |
| Authentication for untrusted network/player access | **OPEN / HIGH** | current local in-process trusted services accept actor IDs and trusted capability flags; do not expose them to an untrusted caller; define/test authenticated entry-point before such exposure |
| Recorded legal title, binding jurisdiction and courts | OUT OF CURRENT J1c2a SCOPE | cannot be silently inferred from historical-claim accounting. Explicitly outside J1c2a and reserved for future approved design |

## Pending work WITHOUT opening a new stage

1. **Independent reviewer:** use a different human or genuinely independent review agent/environment than the implementing/reviewing author, verify HEAD source and rerun independent attack tests, produce a dated report listing reviewed SHA, test outputs, findings, severity, remediation and explicit approval or rejection. Do not relabel self-review external.
2. **Backup/recovery P0 proof:** run a reproducible local-world SQLite crash-safe backup-and-restore drill with integrity verification, persisted claim offers, partial/successful assignments, snapshots and restart; test old-world rejection and failure-atomicity. Keep any necessary correction confined to current stage. Note this environment alone is not an independent disaster-recovery signoff.
3. **Security boundary:** when preparing *any* external interface, require independently validated actor identity and authorization rather than a caller-supplied `actor_id` or free `claim_transfer_authorized` flag. Treat as a release blocker. Trusted local J1c2a may remain technically tested, but this caveat must never disappear from reports.
4. Rerun adversarial and full CI after any code fix, record exact SHA, all results. Review documentation and issue explicit `CLOSED / APPROVED` sign-off only once every required gate above is met with independent evidence.

## Hard-stop decision

**J1c2a: OPEN / TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN.** No claim of full completion; do not start J1c2b, J1c3 or judiciary implementation. A user saying “continue” means continue working on these closure tasks, not bypassing the gate.

**No invented reviewer or recovery sign-off.** An unresolved check remains open until its own evidence exists.
