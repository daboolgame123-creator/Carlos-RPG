# Phase 02-F — Home/work routines implementation and review handoff

**Date:** 2026-11-05  
**Branch:** `simulation-engine-phase-02f`  
**Baseline:** `simulation-engine-phase-02e`, SHA `c892cb0b3948b2affff03c82c65a3bc243049e39` (green)  
**Status:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN (not formally CLOSED)  
**Scope:** disposable test worlds only; no changes to `main` or original Carlos story.

## What is implemented

- Optional persisted `npc_routines` for existing NPCs: `home_id`, `workplace_id`, `work_start`, `work_end`, configured only by a trusted `NPCRoutineConfigured` at time zero. Work-free NPC profiles supported; no automatically granted salary, possession, contract or home ownership.
- Fixed 86,400-second simulated daily cycle with finite work window, including overnight periods. `next_routine_boundary` adds relevant future work start/end times to the deterministic autonomous time scheduler.
- `choose_routine_route` chooses only locally learned route legs towards work during a shift or home outside it; travel uses the existing physical movement event, journey duration, arrival scheduling and replay. No teleportation or remote map reveal.
- Existing explicit target and ongoing action, production and travel remain protected. Normal commuting is suppressed by urgent hunger, fatigue or risk; no silent cancellation of an active action.
- Work location/shift is enforced both in autonomous planning and in the trusted `NPCActionStarted` reducer, so a manually requested or forged remote work action fails atomically.
- `routines_enabled=False` is the default; unconfigured NPCs retain the original behavior.
- Schema **20**, Rules **27**. Genuine 02-E Schema 19 / Rules 26 worlds must be rejected unchanged; migration is not implemented.

## Tests added and covered

`simulation/tests/test_routines_02f.py` checks:

- No implicit remote road knowledge or teleportation.
- Actual timed first commute; eventual physical return; optional rest in the shift instead of a fixed assumed work count.
- No remote production/work at an unreachable workplace; explicit route discovery.
- Current physical needs overriding optional commuting; emergency during an already-running job never erases its completion.
- Exact shift start boundary and locally known route.
- Seven-NPC sample with three distinct shifts and four NPCs without routine configuration.
- Invalid and duplicate bootstrap, unknown location, malformed and boolean times, atomic batch rollback, invalid snapshot.
- Manual work outside assigned place rejected with complete transaction rollback.
- SQLite snapshot / process close / reopening during an active commute.
- Lump-vs-split simulated time preserving physical outcomes, and bounded event budget rejection with no partial commit.

CI also includes frozen historical parity benchmarks, genuine 02-E feature-off comparison, and true 02-E saved-world rejection check.

## Validation evidence

Full GitHub Actions [run 42098158161](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42098158161) on source SHA `bdffa60f34c3e4793318cdb6d304b4708faee83e` passed **753/753 tests on Python 3.10 and Python 3.13** and the entire matrix, including genuine frozen 02-E feature-off parity and untouched 19/26 saved-world rejection. Earlier run 42098083363 passed 753 tests on both interpreters, before adding the final frozen-parity CI gate. Documentation-only commits after the source checkpoint do not alter runtime behavior; check their SHA CI separately before final closure.

## Explicit limitations / future work

1. No mid-action cancellation of NPC labor or travel. A hazard or crisis changes the next eligible decision, or triggers only an existing validated interrupting signal. Cancellation/refund/recovery for outstanding productive commitments requires separate audited design.
2. Routine locations encode assignments, not property ownership, secure access, occupancy, tenancy, wages or employment rights.
3. No automatic wage payouts, random births, long-distance knowledge, or calendar tied to wall clock.
4. Full social reputation, employer contracts, theft, institutional authority, house households, and event-driven relationship changes remain for later phases.
5. Independent reviewer approval remains **deferred**, not waived. P0 production backup/restore certification remains **OPEN**. A green CI is a technical validation, not full certification.

## Independent reviewer checklist

Check `simulation/src/carlos_sim/routines.py`, `actions.py`, `living_world.py`, `domain.py`, versioned event store and all 02-F tests. Try forged home/work configuration, start-at-work without a known route, mid-travel duplicate commands, rushing a shift with split time, two simultaneous NPCs, delayed job completion, emergency starvation, last-tick work and overnight rollover. Verify the actual 02-E parent commit and event parity when routine feature is OFF. Return APPROVED/BLOCKED/INCONCLUSIVE with reviewed SHA and reproducible evidence.

**Reminder:** Never merge this review work into `main` or certify a permanent Carlos world until independent review and P0 conditions are satisfied.
