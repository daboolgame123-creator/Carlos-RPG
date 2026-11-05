# Phase 02-H1 — Physical taking implementation report

Date: 2026-11-05
Branch: `simulation-engine-phase-02h`
Code checkpoint: `ec5d7eb0633a24554636c77cb3b0efde18f7a8a7`
CI: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42105931046 — **SUCCESS**, Python 3.10 and Python 3.13; **773/773 tests on each interpreter**.
Status: **TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN** — **02-H is NOT complete**.

## Implemented (02-H1 only)
- `PropertyTaken` transfers a finite, already-owned item from an explicit real site or present NPC holder to an on-site NPC actor, atomically and without minting. Requires known stock at BOTH ends and a unique taking ID; an ordinary listing cannot sell a unit after it is physically taken.
- Independent `taking_authorized` capability is persisted per command for deterministic replay and refused outside an active session. Market authorization cannot authorize a taking.
- Source location, actor presence, transit/busy/production checks, separately registered market steward for location stock, exact physical balance and bounds are enforced.
- No forced legal verdict or guilt: stored `permission_basis=no_grant_recorded` is a provenance note, NOT proof of theft/crime or lack of verbal permission.
- Explicit restriction: production tools required by a registered recipe cannot be taken with this first slice until a reservation-aware rule exists.
- Persistent `property_takings` record validated on each projection, including source/destination before-and-after quantities and time. Schema **22** / Rules **29**; old worlds are rejected, not migrated.
- No autonomous thief policy; no witness, complaint, court, fine, capture, recovery, or transfer of house titles in H1.

## Tests and evidence
`simulation/tests/test_property_02h1.py` adds 10 tests in a seven-person disposable village:
1. Real bakery bread moves exactly once; conservation and store replay.
2. Remote actor, steward using theft against site stock, mismatch site, insufficient quantity, unknown owner, and self-taking rejected with unchanged state.
3. Untrusted unprivileged event cannot take.
4. Market cannot sell more bread than remains after a taking.
5. Reused taking identifier is rejected as `DuplicateCommand` with unchanged state (because command hash includes expected revision).
Additional CI validates real previously saved 02-G Schema21/Rules28 world rejection with unchanged SQLite bytes, older historical parity and rollback tests, frozen semantic behavior where the new ledger is empty, all existing suites and smoke scenarios.
Evidence: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42105931046 verified both interpreters green.

## Mandatory outstanding work
- 02-H2: actual observed evidence, viewpoint secrecy, contradictory claims, never inference of guilt from rumor.
- 02-H3: authorized local complaint intake and acknowledgment, not punitive adjudication.
- WORLD-GAP-001..005 remain open; P0 productive-world save validation and **independent review remain open**.
- This phase did not change `main` or original Carlos story files; worlds remain disposable tests.
