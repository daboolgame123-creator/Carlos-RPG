# WORLD-01d Integrated Finite Supply Analysis — 2026-11-27

## Verified starting point

- WORLD-01c is closed technically on `feature/carlos-world01c-finite-mine-20261127`.
- GitHub Actions run [#45914899491](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45914899491)
  passed Python 3.10 and 3.13 on exact head `5109c108e24cac10d813469a3e8a65ac2e9f5a25`.
- The finite mine path is covered by `test_world01c_finite_mine.py`: initialized
  reserve, timed NPC extraction, funded wage, local sale and player purchase.
- Player procurement and physical delivery to a funded blacksmith contract are covered
  by `test_world01b_player_workshop_supply.py`.
- Finite `standing_timber` → wood → purchased/carry-delivered wood → charcoal is covered
  by PLAY-48M; local compound procurement and blacksmith production are covered by
  PLAY-46. These separate scenarios have not yet proved the joined path in one world.

## Goal and classification

Join the verified mine, timber/charcoal, and player-forge chains in one disposable
event-sourced world. Establish whether the existing `LivingWorldEngine` and normal
market, movement, workshop, and player reducers can complete that chain without a new
engine rule.

Classification: `CHAT_EXECUTABLE`. Expected scope is a new integration test and status
documentation only. Add engine code only if the current causal path fails for a
demonstrated reason; do not add opening stock or relax ownership checks to make it pass.

## Existing contracts and planned world

1. At genesis, initialize exactly one `iron_ore_reserve`, one `standing_timber`, the
   miner's pickaxe, woodcutter's axe, kiln tool, forge anvil, and explicit copper
   balances. Opening mine ore, wood, charcoal, and fitting are all zero.
2. Configure three timed NPC recipes using existing contracts: reserve → ore, timber →
   wood, and wood → charcoal. Use the funded wages already exercised by WORLD-01c and
   PLAY-48M. Keep each worker at a real site with a configured shift and a registered
   local stall.
3. Configure the existing compound charcoal-burner procurement path over one actual
   adjacent road from kiln to lumberyard. The burner must spend its own initialized
   copper, visit the seller, buy actual wood, carry it back, deposit it, and wait for
   the charcoal recipe's due event. No remote stock lookup or teleport is allowed.
4. Configure Carlos's existing player-bound blacksmith recipe with one ore and one
   charcoal input, an existing anvil, a 90-second duration, and a wage funded by the
   forge's opening till. Carlos travels to the mine and kiln, buys each actual local
   output using owned copper, returns to the forge, deposits both materials, and works.
5. Keep the engine in focused economy mode so unrelated hunger/survival behavior does
   not alter this bounded material-causality test. Reuse local engine policies only;
   do not add a new game mode or persistent-world bootstrap.

## Affected files

- `simulation/tests/test_world01d_integrated_finite_supply.py`: one disposable joined
  world and its causal/ownership assertions.
- This analysis, `WORLD_01_ANALYSIS_2026-11-27.md`, `WORK_QUEUE.md`,
  `ROADMAP.md`, `ROADMAP_CHANGELOG.md`, and `CARLOS_NEXT_CHAT_HANDOFF.md`: report only
  verified results and the next open task.
- No source file is expected to change.

## Acceptance criteria

1. Verify the opening state has one iron reserve, one timber reserve, no ore/wood/
   charcoal/fitting, and an explicitly conserved copper total.
2. At 60 seconds, miner and woodcutter jobs are running; reserve and timber inputs are
   consumed, but neither output nor its wage has been paid early.
3. At the due events, exactly one ore and one wood are produced from those inputs.
   The miner and woodcutter receive only their configured, funded wages.
4. The burner posts a real wood purchase trade at the lumberyard, holds wood only while
   carrying it, deposits it at the kiln, consumes it in a completed timed recipe, and
   leaves exactly one charcoal at the kiln. The burner spends its own opening copper.
5. Carlos sees and buys the actual mine and kiln offers only while co-present; his two
   purchases and the burner purchase each transfer exactly one unit at the configured
   one-copper price. Market trades and route arrivals identify each transfer.
6. Carlos physically returns to the forge, deposits his owned inputs, and completes
   exactly one fitting job after 90 seconds. The output and funded wage do not predate
   completion; all copper remains conserved across wallets and site tills.
7. No duplicate extraction, free charcoal, second sale, or over-deposit is possible.
   Assert unchanged state after at least one exhausted-source or unowned-material
   rejection; existing WORLD-01b/c tests retain the detailed adversarial checks.
8. `verify`, snapshot, replay, and database reopen reproduce the final event-sourced
   state. Run the focused integration and relevant WORLD-01b/c, PLAY-46, and PLAY-48M
   regressions, then the full Python 3.10/3.13 suite and exact-head GitHub Actions.

## Risks and explicit exclusions

- The integrated schedule may expose an interaction gap between timed timber output,
  burner road knowledge, and compound procurement. Inspect events and local knowledge
  before changing code; do not substitute a manually posted remote quote.
- All money must be initialized to exact owners: Carlos needs two purchase coins; the
  mine, lumberyard, and kiln must fund their respective wages; the burner must fund
  its wood purchase; the forge must fund Carlos's wage. Sum and assert the total.
- This proves one finite batch only. It does not claim sustainable employment,
  renewable deposits, population survival, continuing industrial demand, or story
  continuity.
- No new material, cash, job, market knowledge, route knowledge, automatic save
  migration, schema/rules change, original-story change, UI work, `main` change, or PR
  #185 change.

## Results — 2026-11-27

Implemented the joined world in `simulation/tests/test_world01d_integrated_finite_supply.py`.
The existing engine contracts completed the entire finite chain without a source or
schema change: the miner and woodcutter produced one unit each from their declared
reserves; the burner spent its own copper to buy and physically deliver actual wood;
the timed kiln recipe produced charcoal; Carlos bought the actual local ore and
charcoal, carried and deposited both at the forge, then completed one funded fitting
contract. A second mine extraction was rejected after the reserve was exhausted.
Trade ownership, copper conservation, event replay, snapshot verification, and reopen
state matched.

- The new integration test plus WORLD-01b/c, PLAY-46, and PLAY-48M focused regressions:
  **7 passed** on Python 3.12.14.
- Full local suite on the code/test commit `7b5dddb5d1d51c0432bf2870672edd1c68e783e4`:
  Python 3.13.5 — **1952 passed, 1 skipped** (19:19); Python 3.10.22 — **1952 passed,
  1 skipped** (26:01).
- GitHub Actions [#45922155158](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/45922155158)
  passed both Python jobs on that exact code/test SHA. Its logs report **1952 passed,
  1 skipped** for each version.

No engine source, Schema46/Rules73, story, UI, `main`, saved-world migration, or PR #185
was changed. This is one finite test-world batch; it does not establish renewable
resources, sustainable employment, population survival, or a production-world setup.

## Technical status and next analysis

WORLD-01d is `CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER`. The wider
WORLD-01 scope remains `IN_PROGRESS`; production-save approval remains
`P0_PRODUCTION_NOT_APPROVED`.

Next, analyze WORLD-01e: whether the engine needs a reusable, explicit world setup
contract for locations, roads, finite reserves, stalls, recipes, and funded jobs, or
whether the existing event-based genesis contracts already provide the needed world
composition. Define a small acceptance test before changing engine code. Keep the
scope simulation-only and outside the UI.
