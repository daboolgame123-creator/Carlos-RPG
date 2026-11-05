# 02-A technical implementation report — finite environmental stocks

**Status: IN_PROGRESS pending final SHA/CI.**
**Branch:** `simulation-engine-phase-02a` from `1225ae066f22bc2688a583d46e63ceda80558a07` (01-Z, [final CI 42060397577](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42060397577)).
**Version:** Schema **15** / Rules **22**, previously 14/21.
**P0 OPEN** / independent review **DEFERRED**. Tests use disposable worlds. No story import, no `main` modification, no general migration.

## What changed
- A site can have an explicitly seeded **finite** `regrowth_reserve` in addition to known `wild_food`. At world setup, `EnvironmentalCycleConfigured` selects that site, an integer simulated interval, and a maximum deposit capacity. Requires time-zero trusted bootstrap and initialized, nonnegative stock. Unknown remains **unknown**, not zero.
- A fixed, protected, noninterrupting scheduled clock appointment consumes exactly one reserve unit and adds exactly one wild food unit when the interval elapses, the reserve is positive and the deposit is not full. When reserve reaches zero, no further appointment is scheduled; this avoids infinite empty event storms. A full deposit never wastes reserve but stays eligible if food is later gathered. Total `reserve + wild_food` remains unchanged by a renewal. Future agriculture/season/weather are not simulated.
- Generic schedule insertion is prohibited from impersonating the environmental appointment; generic cancel cannot disable one. Only an authorized `ScheduledEventFired` at the exact due time performs the conversion. No wall-clock advancement or clandestine food creation.
- A new strictly validated `environment_cycles` projection records cumulative ticks, converted amount, last and next due time, period, capacity and site. Verification reconstructs it solely from genesis events and scheduled firing events; snapshots remain checked. Old 14/21 saves are rejected without mutation; never silently upgraded.
- Existing `TimeEngine` and `LivingWorldEngine` execute these appointments without reading remote sites in NPC planning. Seven-NPC gathering can take subsequently available food only through its existing physically sourced local action with time cost.
- Unconfigured worlds get no cycles, no new scheduled actions, and no altered old event/semantic digests. Cross-version parity excludes only Schema/Rules and the one *empty* additive `environment_cycles` collection, preserving comparisons of NPCs, resources, events and beliefs.

## Tests
- **14 new tests** in `simulation/tests/test_environment_02a.py`, in addition to 643 previous tests.
- **Confirmed implementation CI:** [42062676270](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42062676270), SUCCESS, **656/656** tests for each Python 3.10 and 3.13. This is intermediate code CI, before the exhausted-reserve optimization; the latest verification must demonstrate **657/657** tests on both Python versions, and final SHA proof must be recorded.
- Coverage: successful 1:1 transfer, reserve depletion with terminal schedule, zero-stock long time, full-capacity no-waste, missing resources, malformed/unknown states and types, forged config/cancel/schedule/early fire, active session requirement, stale/duplicate commands, bounded batch rollback, two independent sites, split vs lumped deterministic clock, snapshot and database reopen, standalone 15/22 backup/restore, and seven autonomous NPCs competing for available harvestable food. A seven-NPC disposable demonstration in `demo_environment_02a.py` and workflow smoke must also pass at final SHA.
- The CI checks out the **frozen genuine 01-Z predecessor** (14/21), constructs an old SQLite world with real code, then checks the new engine refuses it without altering worlds/commands/events/snapshots. Previous parity and baseline checks remain.

## Review notes / limitations
**No approved independent review:** technical tests are authored in this development flow. The requested [independent review](phase_02a_independent_review_request.md) has not been conducted; do not mark APPROVED/CLOSED.

This is one constrained example of **finite environmental restoration**, not biology or generalized farming: `regrowth_reserve` is a finite test-world potential budget that is debited at each conversion. There are no weather/season growth inputs, renewable nutrients, production chains, settlement economies or persistent canon-game guarantees. The environment's ground truth remains inaccessible to distant NPC policy except by already established observation/knowledge mechanics.

**P0 still OPEN:** new Schema/Rules make earlier saves incompatible. The 01-Z backup candidate remains test-only; no independently reviewed cross-version migration, Windows disaster recovery, or production save policy. Keep all worlds disposable and any story import blocked.

**Technical review follow-up:** record the final commit SHA and its matching green workflow result in this report or in the final delivery; final documentation changes must be CI-confirmed too. No false independent sign-off.
