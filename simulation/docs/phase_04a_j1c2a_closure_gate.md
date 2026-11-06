# 04-A / J1c2a — Mandatory stage closure gate

**Adopted:** 2026-11-06. **Authority:** user rule: DO NOT start any following stage/substage until its predecessor is fully completed, reviewed, tested, documented and explicitly CLOSED. See repository-root `AGENTS.md`.
**Scope:** existing registered *historical claim* handshake, NOT legally recognized title. Do not begin J1c2b implementation, including schema migrations or new judicial/title reducers, while J1c2a is OPEN.

## Verified evidence (not equivalent to formal closure)

| Check | Status | Concrete evidence |
| --- | --- | --- |
| Planning before coding | PASS | `phase_04a_j1c2_design.md`; original J1c2a bounded scope and risks |
| J1c2a implementation | PASS | `registered_claims.py`, `domain.py`, `rights.py`, `store.py` |
| Adversarial + full regression | PASS | [CI 42139139403](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42139139403) **899/899 passed each** Python 3.10/3.13, specialized probes **5/5** each; earlier [CI 42137905742](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42137905742) passed 897/897 each |
| Additional internal code review | PASS **internal only** | `phase_04a_j1c2a_followup_review.md`, including 3 extra probes, known trust limitations |
| Documentation/roadmap | PASS | `phase_04a_j1c2_report.md`, `ROADMAP.md`, `ROADMAP_CHANGELOG.md` |
| Genuine independent external adversarial approval | **OPEN / BLOCKING** | `phase_04a_j1c2_independent_review_request.md` defines test scopes; **no signed separate reviewer report exists** |
| Current-stage claim-backup technical tests | **PASS (technical only)** | `test_j1c2a_recovery_gate.py`: backup while accepted and open offers coexist, SQLite WAL, verification, restore and resume with unchanged rights and custody; corrupted backup is refused without creating output. Included in [CI 42139139403](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42139139403), 899/899 each. |
| Independently demonstrated production recovery / P0 acceptance | **OPEN / BLOCKING** | Test fixture is a disposable CI world. No independent disaster recovery sign-off or production-world restoration approval; existing prior-version reject is not migration. |
| Authentication for untrusted network/player access | **OPEN / HIGH** | current local in-process trusted services accept actor IDs and trusted capability flags; do not expose them to an untrusted caller; define/test authenticated entry-point before such exposure |
| Recorded legal title, binding jurisdiction and courts | OUT OF CURRENT J1c2a SCOPE | cannot be silently inferred from historical-claim accounting. Explicitly outside J1c2a and reserved for future approved design |

**Tracked blocking external review:** [GitHub Issue #5 — J1c2a independent review and P0 recovery](https://github.com/daboolgame123-creator/Carlos-RPG/issues/5). Issue creation is a request, NOT external sign-off or completion of P0; its checklist remains open until separately documented evidence and approval. Latest checked docs-only HEAD `f22ddd5686145532279c4426c8ab96240f1ba16b` [CI 42139494294](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42139494294) SUCCESS.

## Follow-up same-tick adversarial test evidence (2026-11-06)

- [CI 42140310497](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42140310497) **901/901 passed per Python 3.10 and 3.13**, with the dedicated five adversarial probes passing on each interpreter.
- Two extra tests at code commit `318a7388bbee2d621baa0b6cbaff6863d499c207` verify that two concurrently reserved offers accepted in reverse order cannot overallocate registered claim units, and cancellation during the same logical tick permanently blocks acceptance even if the balance is later reserved for someone else.
- These are extra **internal automated regression probes**, not external independent sign-off. Issue [#5](https://github.com/daboolgame123-creator/Carlos-RPG/issues/5) remains OPEN; production P0 and external reviewer approval remain blockers.

## Pending work WITHOUT opening a new stage

1. **Independent reviewer:** use a different human or genuinely independent review agent/environment than the implementing/reviewing author, verify HEAD source and rerun independent attack tests, produce a dated report listing reviewed SHA, test outputs, findings, severity, remediation and explicit approval or rejection. Do not relabel self-review external.
2. **Backup/recovery P0 proof:** run a reproducible local-world SQLite crash-safe backup-and-restore drill with integrity verification, persisted claim offers, partial/successful assignments, snapshots and restart; test old-world rejection and failure-atomicity. Keep any necessary correction confined to current stage. Note this environment alone is not an independent disaster-recovery signoff.
3. **Security boundary:** when preparing *any* external interface, require independently validated actor identity and authorization rather than a caller-supplied `actor_id` or free `claim_transfer_authorized` flag. Treat as a release blocker. Trusted local J1c2a may remain technically tested, but this caveat must never disappear from reports.
4. Rerun adversarial and full CI after any code fix, record exact SHA, all results. Review documentation and issue explicit `CLOSED / APPROVED` sign-off only once every required gate above is met with independent evidence.

## Hard-stop decision

**J1c2a: OPEN / TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN.** No claim of full completion; do not start J1c2b, J1c3 or judiciary implementation. A user saying “continue” means continue working on these closure tasks, not bypassing the gate.

**No invented reviewer or recovery sign-off.** An unresolved check remains open until its own evidence exists.
