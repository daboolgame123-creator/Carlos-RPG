# PLAY-29 — technical acceptance gate (evidence ledger)

**Status at initial writing (2026-11-08): VALIDATION_PENDING — NOT CLOSED.**  
**Source candidate:** `d67fefc09dddb17175e3799492167e4d4b03196c` (Schema 39 / Rules 51).  
**Scope:** disposable seven-NPC simulation worlds only; no main merge, canonical story save, or migration.

## Verified evidence

- **72h controlled action-cost comparison:** [GitHub Actions #42475946942](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42475946942) — `completed/success`. Both worlds use the 3600-second hunger clock; the action surcharge is the only intended variable. Observed hunger-at-cap went from 7 (original action cost) to 0 (calibrated) after 72 logical hours.
- **Full regression on Python 3.10 + 3.13:** [#42476104910](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42476104910) — **`completed/success`: 1,670 tests passed on Python 3.10 and 1,670 on 3.13 (3,340 total), zero failures**. Run pinned to `1a4a4021367c670781eea5dee030fe9d93e65f37`. Seven-day add-on at `d67fefc0` changes only its scenario test and workflow.
- **Real 7-day finite-food survival observation on 3.10 + 3.13:** [#42476455377](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42476455377) — `in_progress` at writing; **not accepted yet**. Pinned to `d67fefc09dddb17175e3799492167e4d4b03196c`.

## Required before technical closure

1. Confirm all jobs in both pending runs report `completed/success`, matching the intended SHAs. If a job fails, examine its step/log and fix the *specific blocker* in a new branch; repeat affected gates.
2. Extract the seven per-day `PLAY29_SEVEN_DAY_FINITE_FOOD_OBSERVATION` records from completed 7-day job logs, including hunger-at-100, high-risk NPCs, eaten meals, remaining personally owned food, crop maturation and courier deliveries. **A green test asserts clock/replay/resource integrity, not that starvation was avoided.**
3. Explicitly report whether the seven-NPC village was self-sustaining. **Do not claim self-sufficiency** from the seven-day test: it begins with six finite personal meals per NPC, one plot, two finite water units, no automatic rainfall, and no demonstrated replacement supply.
4. Check frozen time-zero-only world policies, historical version pin/fail-closed behavior, no free resources, and SQLite replay against full regression results. An unreviewed permanent migration is out of scope.
5. Only after the above, change this document to `PLAY29_CLOSED_TECHNICALLY` with final results, exact SHAs, dated job links, and unresolved long-term food-production needs. An externally approved release and `main` merge remain separate decisions.

## Scope boundary

No automatic food, copper, well refill or supernatural material creation. Further food capacity work must use real planted land, finite seed and water, travel, labor, crop growth time, and physical distribution. Avoid unrelated improvements as prerequisites to closing the verified calibration experiment.
