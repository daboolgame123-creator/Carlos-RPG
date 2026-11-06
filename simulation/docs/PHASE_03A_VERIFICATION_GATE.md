# 03-A — isolated branch verification checklist

Date: 2026-11-06
Status: VERIFICATION_PENDING / NO INTEGRATION APPROVAL
Branch: `design-phase-03a-health`
Last implementation commit at authoring: `654a485046586ad05d054aba73e809af30c7ece0`
Do not use the documentation-only head as evidence that tests passed on final code.

## Current slices

| Component | Source | Test | Permission to change world |
|---|---|---|---|
| Injury intake proposal | `src/carlos_sim/injury_intake.py` | `tests/test_injury_intake_03a.py` | NONE |
| Injury state transition calculator | `src/carlos_sim/injury_transitions.py` | `tests/test_injury_transitions_03a.py` | NONE |
| NPC co-location recovery readiness | `src/carlos_sim/recovery_readiness.py` | `tests/test_recovery_readiness_03a.py` | NONE |

None of the above is a persisted InjuryRecorded event or gameplay healing. There is no trusted injury-source provenance or recovery scheduler authorization yet.

## What can actually be claimed

- A detached local copy of the pure transition module has been run in pytest: **22 passed** on local Python 3.13. This is unit evidence only, not GitHub exact-SHA CI or integration.
- Local package checkout is not available through GitHub clone in this chat container (network DNS access blocked). Full code is inspected via GitHub connection, but GitHub connection does not provide an arbitrary push workflow trigger.
- The present committed test files have **not** been verified with `python -m pytest` inside the complete Carlos engine. There are no current exact-SHA CI results in evidence for this branch.
- The `test_property_02h1.village` fixture was inspected; `adel` is located at `bakery` and `omar` at `square`. The remote-care expectation is grounded.

## Required targeted and regression commands

Run from `simulation` at the current exact SHA:

```bash
python -m pytest -q tests/test_injury_intake_03a.py tests/test_injury_transitions_03a.py tests/test_recovery_readiness_03a.py
python -m pytest -q
```

On Python 3.10 and 3.13, verify unchanged existing parity scripts and adversarial/recovery workflows. If any red test appears, inspect the source and fix on this branch before adding persistent injury state. Never change the expected parity digests or weaken trust checks simply to make CI green.

## Next genuine implementation gate

Before implementing an irreversible injury ledger:
1. Define and test a new **trusted injury source** event with authorization provenance and command idempotency. A supplied string `source_reference` is insufficient.
2. Add a versioned durable injury ledger for NPCs separately from player-only `rpg_profiles`; pin Schema/Rules and reject old files unchanged, unless explicitly migrated.
3. Implement a dedicated scheduling authorization for recovery; existing `ScheduledEventCreated` guard protects known action types but is not a recovery capability.
4. Test physical local presence, resources/cost, interruption, full replay, snapshot and backup/restore before claiming that any character recovered.
5. Keep both the lawful-title branch and this injury branch separate until independently validated and reconciled.

**No review or production acceptance is implied.**
