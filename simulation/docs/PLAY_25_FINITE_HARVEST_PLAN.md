# PLAY-25 — finite harvest-to-bread supply (plan)

**Status:** IN_PROGRESS / GATE_OPEN (2026-11-08). **Base:** PLAY-24 `386c6714d28819e1a7d84c6c768c005520be7768`.
**Branch:** `simulation-engine-phase-play-25-finite-harvest`. Never change `main`, canonical story, production schemas or global NPC defaults.

## Baseline and objective

PLAY-24's opt-in economy can bake, offer, buy and eat but relies on one initially stocked grain. Existing generic `ProductionRecipeConfigured` / `ProductionStarted` already performs strict physical transformations of *owned* local resources with real occupational checks, time, tools and completed jobs. We will extend the **verified autonomous chain** backwards: an actual farmer harvests a finite, initially owned standing-crop inventory with a sickle into grain, after which a separate baker converts that grain to food, a market keeper posts local stock, and an eligible buyer pays/eats. No player ordering of NPC production/trades.

## Scope and order

1. Make a disposable seven-NPC test world: Nora is a farmer and Basim a baker; both actually present at one communal town worksite on explicitly valid shifts. The field and bakery are represented as separate recipes and separate tools at that one site (single-site simplification). Seed only known finite crop lots, empty grain/food and copper accounts. Do **not** assign hidden teleportation, external deposits, new powers or extra materials during execution.
2. Exercise existing pure economic decision selector and event reducers in a single opt-in `LivingWorldEngine`. For a harvest recipe `crop_ready:1 -> grain:1`, a finite sickle and 60-second work slot are required. The baker consumes `grain:1 -> food:1` using the oven in 90 seconds. Test negative worlds: no crop, no sickle, farmer unavailable/off shift, baker absent/off shift, buyer without money. Compare actual events and resulting owner balances.
3. Include multi-batch finite-resource exhaustion, zero grain at bootstrap, conservation invariant `crop_ready + grain + food + consumed food`, copper conservation, exact elapsed clock, job due times, SQLite verify/snapshot/reopen, deterministic world replay, stale/duplicate and max-event rollback, player handoff privacy, and opt-out regression.
4. Add workflow targeting Python 3.10 and 3.13 with scenario + focused tests. Require successful targeted **and full simulation test** runs on the same code SHA before marking this phase technically closed. Only after evidence, update `WORK_QUEUE.md`, `ROADMAP.md`, report and phase status. No production approval implied.

## Strict limitations

- `crop_ready` is an **already ripe, finite physical reserve** at the worksite. This stage proves crop **harvesting**, not sowing, weather, growth or multi-day regeneration. It is not an infinite or truly sustainable food economy.
- The town farm and bakery are colocated **in this test world only**. No inter-site logistics, agricultural seasons, wages, dynamic prices or hunger deaths are implemented.
- Using existing production/market events should keep Schema 34 and Rules 46 unchanged. Add core changes only where a proven gap appears.
- P0 approval and independent external review remain pending, as in PLAY-24.
