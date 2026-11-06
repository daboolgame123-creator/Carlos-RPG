# OpenCode verification — J1c2b-LAW-DRAFT (2026-11-06)

**Purpose:** Verify only the newly implemented, *nonbinding* registered-institution authority proposal. Do not advance to legal title adjudication or rewrite the architecture.

## State and commits
- Repo: `daboolgame123-creator/Carlos-RPG`
- Branch: `simulation-engine-phase-04a-j1`
- Code added: `b3213a4aa06f0ab01f13af6101f9d42287fa71fe`
- Targeted tests added: `cdaad68d7dcb36aa064341d4d875b880f6551179`
- Queue updated: `90da2aa404af2e35596ec89aae3e0073539f9201`
- **Verify latest branch HEAD and working tree before running anything.** Do not use a fixed SHA if newer commits exist.
- Schema/Rules remain **29/37**.

## Analyze first
Read `AGENTS.md`, `simulation/docs/WORK_ROUTING_PROTOCOL.md`, `simulation/docs/WORK_QUEUE.md`, `simulation/src/carlos_sim/institution_authority_draft.py`, `simulation/tests/test_institution_authority_draft_04a_j1c2b.py`, and `simulation/src/carlos_sim/local_institutions.py`.

The new function `prepare_registered_institution_authority_draft` is a pure, trusted-internal, read-only charter **proposal** for an already registered factual institution. It MUST NOT install jurisdiction, law, court powers, physical transfers or legal title. Missing ID, forged ID and retroactive/equal-time input must fail closed.

## Execute on a disposable test environment
1. From `simulation`, run:
   - `python -m pytest -q tests/test_institution_authority_draft_04a_j1c2b.py`
   - `python -m pytest -q`
2. Check Python 3.10 and 3.13 wherever available.
3. Check relevant cross-version parity gates and adversarial CI, on the **final code SHA**.
4. Compare snapshot, `verify` and full replay results. The draft must not add an event or modify persisted SQLite state.
5. Check representative relocation after founding, malformed ID/time types, future logical time, mutation of returned draft, and institution with no legal mandate. Add focused regression tests if these reveal gaps. Do **not** infer representative consent from registration.
6. If a test fails, identify the minimal root cause and fix only this task. Preserve existing expected digests and rules-version checks; never disable a failing gate.

## Evidence and handback
Report branch, final SHA, exact commands, Python/OS versions, pass/fail/skip counts, CI run URLs and identified limitations. Update `WORK_QUEUE.md` from `VERIFICATION_PENDING` to `CLOSED_TECHNICALLY` **only** on passing exact-SHA full regression and required gates, with no blocking defect. Otherwise leave open and document failure.

**Out of scope:** actual law or enforceable title, court or seizure, historic migration, production/network approval, claimed independent review. `J1c2b-LAW` remains open and its additional legal authority decisions require their own justified implementation and tests.
