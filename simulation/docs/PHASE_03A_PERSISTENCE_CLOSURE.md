# Carlos RPG — Phase 03-A4 bootstrap NPC injury persistence: technical closure

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-persistence`
**Verified code and tests SHA:** `95e2e54da312b246c13d77a2b6d724155c4e9ecd`
Schema / Rules: **30 / 38**
Status: **CLOSED_TECHNICALLY — bootstrap-only injury persistence**.
Not a production approval, not a closure of overall 03-A (runtime injury and recovery remain unimplemented).

## Evidence on exact verified SHA

- GitHub Actions [run 42263516435](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42263516435).
- `test (3.13)` job 128049328833: **success**, `1079 passed in 88.96s`; full action run passed including smoke tests and frozen historical parity.
- `test (3.10)` job 128049329121: **success**, `1079 passed in 90.42s`; full action run passed including smoke tests and frozen historical parity.
- [Draft PR #7](https://github.com/daboolgame123-creator/Carlos-RPG/pull/7) remains open. Not merged to main or legal/property branch.

## What is implemented and verified

1. New `WorldState.injuries` collection with strict snapshot validation, immutable projections, and Schema 30 / Rules 38 versioning.
2. `InjuryRecorded` event accepted **only through trusted time-zero bootstrap** for an already configured NPC; no actor impersonation, IDs/severity bounded, no duplicate IDs, no damage inferred from arbitrary narrative or unrelated events.
3. Stored events reproject into the NPC injury ledger across SQLite reopen, snapshot and full event-log replay. Failed writes preserve state.
4. Negative tests include invalid times/severity, duplicate ID, wrong subject/source, after-time-zero attempt, old-version rejection without rewriting metadata/events, and no disclosure of NPC injury through general `player_view`.
5. Existing world versions remain unsupported rather than silently modified; tests pin the new current version while retaining frozen historical version assertions. Semantic parity strips the **provably empty** new injury collection for legacy comparison and rejects it when nonempty.

## Explicitly not implemented

- Runtime injury causes, weapon/combat injury, illness, random damage, fall injuries, NPC health-point estimates, automatic HP changes.
- Injury-causing trusted gameplay command/event capability and its SQLite command provenance.
- Recovery scheduling, therapeutic resource costs, healing effects, capability impairment, death/medical diagnosis, client-visible symptoms.
- Production approval, real-world saves migration or an external adversarial review.

## Next substage (03-A5) — MUST start with analysis

To support runtime injury, use separate trusted local authorization, recorded per-command SQLite provenance and replay, deterministic source/cause contract, and strict observation/locale/capability guards. To support recovery, integrate existing logical schedule and resource flow with separate anti-spoofing capability; never use passive wait as automatic healing. Bump Rules (and Schema if structurally required), preserve old-world rejection, add end-to-end tests and exact-SHA Python 3.10/3.13 CI before closing. Implement on a separate branch from this verified SHA and do not merge without passing tests.

## Routing
- This closure covers **only 03-A4 bootstrap injury persistence**.
- The separate `J1c2b-LAW` and the production/external gates remain unchanged.
