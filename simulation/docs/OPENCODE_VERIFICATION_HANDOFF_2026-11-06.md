# Carlos RPG — OpenCode verification handoff (2026-11-06)

**Scope: verification and bug fixing, NOT next feature stage.** Repository `daboolgame123-creator/Carlos-RPG`; branch `simulation-engine-phase-04a-j1`. Initial documentation HEAD verified as `8eccccb9d26a876180a1f7b8acef6d408e301383` on 2026-11-06; **fetch and verify current HEAD before doing anything**. Read `AGENTS.md`, `simulation/docs/WORK_ROUTING_PROTOCOL.md`, `WORK_QUEUE.md`, `ROADMAP.md`, `EXTERNAL_VALIDATION_LEDGER.md` and J1c2b design.

## Evidence (not assumptions)
- Version: **Schema 29 / Rules 37** (new trusted bootstrap `LocalInstitutionRegistered`, existence-only mandate, no court powers).
- Exact code SHA `617b931da5cc3b433525ae6410f5e878dfc87012`: full CI workflow [42229493643](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42229493643) **FAILED** on Python 3.10 and 3.13. Each Python pytest suite reported **976 passed**, but the subsequent 01-T feature-off parity check failed for `legacy_semantic_digest`: old `7d2be0d6c63594aaf7d6aa60f03be97a9c01747a7606931c66b2cc91c710bdf9` vs new `e665f86fb0e164dfa64095130ed75c8995c86f1d0922d8127d83a71264633157`.
- Dedicated adversarial CI [42229493587](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42229493587) **SUCCESS** 3.10/3.13.
- Separate offline recovery CI [42229493540](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42229493540) **SUCCESS** 3.10/3.13. Seven actors, 38 events, 1 snapshot; backup/replay/resume, corruption rejection and existing-target protection. This is not real Windows/production proof.
- Earlier pre-Schema29 code confirmed **962/962** on both Python versions ([42227263627](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42227263627)).
- Independent adversarial *source review* and real Windows/production recovery remain unverified even if CI exercises pass. No production P0 approval.

## Ordered task 1: fix current CI blocker — DO THIS FIRST

1. **Analyze before editing.** Inspect exact CI logs and the `01t-flag-off` vs frozen `reviewed-01s` parity step. Investigate `scenarios/test_village/bench_event_parity.py` and `legacy_semantic_digest` derivation; compare semantic fields and event traces, not just hashes. Suspect a schema-only representation change but **prove** the precise cause and test whether any behavioral semantic change occurred.
2. Preserve meaningful backwards-compatibility assertions. **Do not silence/skip digest checks, replace expected hashes, weaken event-integrity checks, or forge the baseline.** If only newly added empty collections affect a supposedly legacy digest, correct the version-aware semantic projection with evidence and tests. Otherwise fix the real behavioral regression.
3. On the current feature branch, run focused tests, full `python -m pytest -q` from `simulation` on Windows, relevant local CLI parity and recovery drill where possible; commit a minimal fix and verify GitHub Actions on its **exact final SHA** for Python 3.10/3.13.
4. Check old Schema28/Rules36 world files are refused without mutation; tests with synthetic old schema rows are not substitutes for an actual historical fixture. Report results and file hashes. If a real historical fixture is unavailable, mark this separate check `UNVERIFIED`, never invent one.
5. Record failures/fixes/evidence in `WORK_QUEUE.md`, design log and appropriate test report. **Do not start J1c2b-LAW or a different dependent stage while CI remains red.**

## Ordered task 2: independent adversarial code review

After task 1 is green, use a genuinely separate reviewer (OpenCode reviewer agent) with no assumption of implementer approval. Review event authorization and replay, absence of judicial power in `LocalInstitutionRegistered`, physical proximity and spoofing, claim/title separation, forged snapshots, duplicate sites/representatives, audit visibility leaks, and transactional rollback. Return findings with severity, path/line, reproduction tests, and verdict. Implement fixes only after evaluating findings; rerun full CI.

If the reviewer is just the same agent self-reviewing, label `INTERNAL_REVIEW`, not `INDEPENDENT_APPROVED`. The owner previously deferred independent review; offering it now does not mean it occurred.

## Ordered task 3: Windows external validation

Use a **disposable** isolated SQLite file and temporary folders, never a personal/production world. Verify: reopening after process restart, snapshot vs full replay, file-lock/rename behavior on Windows, backup restore to new target, refusal to overwrite existing target, rejected corrupted backup, replay and resume, and no mutation of source. Capture OS, Python, commands, outputs, SHA, and file hashes. Mark Windows checks confirmed ONLY after actual execution. Do not run intentional power-loss or destructive fault-injection on the owner's only computer.

## Deferred tasks (not now)

- `EXT-002`: real server/production recovery including power loss and permissions — **requires authorized safe production-like hardware**; do not attempt on valuable data.
- `EXT-004`: untrusted network/player authentication — **NOT IMPLEMENTED**, not a candidate for acceptance testing; do not expose API or LAN externally.
- Normative title law, court authority, enforceable transfer, hearings and punishments — **DECISION_REQUIRED/BLOCKED_BY_DEPENDENCY**, not part of this verification handoff.

## Exit criteria and reporting

For **each** test/review: include exact tool/OS/commit, command, passed/failed count, logs/links, actual scope, untested items, severity of open findings. Update the work queue by IDs. Technical closure needs all **current-stage** acceptance and regression gates green on the final SHA, with no known blocking defects. Independent reviewer/P0 statuses remain truthful. **No new phase until current dependent gates close; unrelated work only through dependency-aware safe routing protocol.**
