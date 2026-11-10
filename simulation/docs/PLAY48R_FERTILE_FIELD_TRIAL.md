# PLAY-48R — fertile east-field pilot with real 13-NPC physical crops

**Date:** 2026-11-11 (Iraq local). **State:** `PLAY48_OPEN / RELEASE_NO_GO`. Opt-in isolated simulation hypothesis, not a production change, not a new playable feature or a seven-day recovery claim.

## Source and scope

Base: `5bd9bd301b271595fee04c886e56b951f46c0c6f`, following verified R/P/Q causal experiments. Branch: `experiment/play48r-fertile-field-real-harvest-20261111`.

- The original 13 NPCs, physical roads, wood and charcoal professions, two fields, two couriers, working hours, authentic crop germination (one seed packet), 24h growth, finite water, registered bounded rainfall, actual salaries and **12 known copper coins** remain unchanged.
- Default existing eastern crop yield **7** remains unchanged. Only this opt-in time-zero experiment configures the actual `east-finite-harvest` recipe with **12** units per fully matured, physically harvested crop from the same eastern site. No extra stock at time zero, no extra NPCs, no post-genesis developer commands, no shorter growth or free rain. This is an **assumed fertile-land productivity** world variation; real farming improvements, soil/compost provenance and ecological plausibility are not independently validated.
- The existing conservation test now obtains grain yield from each immutable authenticated recipe, rather than a fixed `CROP_YIELD` map for both arms. Replay and full resource conservation still apply. This fixes the *test assumption*, not the simulator rules.

## Preliminary deterministic gate

[PLAY48R CI #42919278865](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42919278865) includes a fast genuine genesis/replay and 48h autonomous A/B comparison for Python 3.10 and 3.13. The bounded genesis tests passed on both; the long-run result is separately checked and must not be inferred from its queue status.

By reusing the previously authenticated food-capacity model, **necessary limits only**:

| Metric | Actual baseline recipe 3+7 | Fertile test recipe 3+12 |
|---|---:|---:|
| 13 NPC starting loaves | 3 | 3 |
| Starting water | 2 | 2 |
| Optimistic daily grain with enough authenticated water | 10 | 15 |
| Minimum daily meals, ignoring extra activity hunger | 13 | 13 |
| Maximum bread-equivalent production/initial stock in 7d with 6 observed rain units | 55 | 90 |
| Minimum meals to keep all strictly below 90 hunger for 7d | 61 | 61 |
| Maximum total bread-equivalent with **no additional rain** | 17 | 27 |

These static bounds are deliberately generous and ignore actual hunger, transport timing, fatigue, market ownership, distribution and farming conditions.

## Acceptance and known remaining blockers

- **R0:** bounded fixture and replay tests 3.10/3.13: confirmed green on the R pilot SHA `bb86167d43e005f49e942cb5d54cb4a31f7aa650`, [CI #42919278865](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42919278865) (job-level proof only; the whole run includes longer tests).
- **R1:** independently observed 24/48h sowing → maturation → harvest → physical deliveries → actual bakery batches → food sales/meals, compared with unchanged baseline, full replay and 12-copper preservation: required before deciding if productivity reaches the market.
- **R2:** [Complete Python 3.10+3.13 pytest regression #42919617997](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42919617997) run on SHA `aa836e46b764a4e4d4d287caf5c43acb51d6c97e` (same source, additional workflow file), result must be checked before attributing any success.
- **R3:** The alternative production must still establish real finite nutrient/soil/water provenance and actual recovery, not only raise a yield constant. Even a green simulator A/B does **not** prove medieval agricultural sustainability or seven-day survival.
- **Next:** If real production rises but residents still starve with bread in market, causally isolate *physical food ownership / courier wage and nutritional access* before more field expansions. Never bypass hunger safety guard, invent food/wages, merge to `main`, or unlock P0 save migration.

Evidence is tied to tested source SHA, not documentation-only commits.
