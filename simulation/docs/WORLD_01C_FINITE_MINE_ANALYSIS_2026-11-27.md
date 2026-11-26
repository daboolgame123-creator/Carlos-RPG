# WORLD-01c Finite Mine Analysis — 2026-11-27

## Verified starting point

- Development branch: `feature/carlos-world01c-finite-mine-20261127`, based on WORLD-01b commit `23d154042af75965d70a16063c7dc1280eb88b02`.
- Before starting this branch, PR #185 was rechecked: open, draft, unmerged and mergeable; head `feature/carlos-engine-needs-20261126` at `416e26b6c037b2fc504c8454d9b607aadeee7eba`.
- The previous WORLD-01b worktree is clean. This scope stays in a separate disposable test world; no `main`, story, UI or PR #185 changes.

## Code and test findings

1. `ProductionRecipeConfigured` already records a named NPC recipe with known local input, output, tool, duration and funded wage. `ProductionStarted` consumes only the configured input; the scheduled due event adds the output. The existing reducer is sufficient to model one finite ore-extraction batch.
2. The focused `LivingWorldEngine` path calls generic `choose_local_production` for workers on configured routines and resolves each scheduled due event. With `economy_only_enabled`, a miner can work from its actual shift without activating general NPC deliberation or unrelated needs policies.
3. `multi_professional_trade.choose_local_material_offer` already lets a registered, present miner sell only initialized local `iron_ore`; the focused engine can post the quote and normal market reducers enforce quantity, price, ownership and copper conservation.
4. Charcoal production is already covered by the existing test-village counterfactual: a finite `standing_timber` stock is cut to wood, the burner buys and carries wood, and the kiln recipe consumes wood to make charcoal. Relevant evidence lives in `test_play47_joined_professions.py` and the PLAY-48M employment scenario. Rebuilding charcoal production would duplicate an existing causal path.
5. Existing mine worlds initialize `iron_ore` directly at `iron_mine`, so they prove finite trade/stock but not a cause for producing that ore.

## Proposed bounded test

Add an isolated test world with a miner at `iron_mine`, one explicitly initialized unit of `iron_ore_reserve`, a pickaxe, one fully funded mine wage, and no opening `iron_ore`. Configure a finite recipe that converts one reserve unit into one ore over 120 simulated seconds. The focused living-world engine starts the miner's contracted shift batch, completes it only at the due event, pays its funded wage, and posts a local ore quote. Carlos begins with one copper, travels to the mine, waits through the mining appointment, buys one unit at the exact local price, and retains actual ownership. Try to start a second extraction after the sole reserve is consumed and require an atomic rejection.

The reserve is a declared test-world endowment. The recipe event explains its conversion; the test will not claim ore was created by an unexplained runtime source or model geology beyond this finite batch. Reuse the existing charcoal chain as a regression reference rather than adding charcoal code or stock here.

## Contracts and acceptance criteria

1. At bootstrap the mine has exactly one reserve unit, zero ore, one pickaxe and one funded copper wage; Carlos has exactly one copper. All values and their ownership are explicit.
2. On the miner's configured shift, the focused engine starts the recipe, consumes the reserve immediately, leaves the pickaxe and ore unchanged, and records a running 120-second job.
3. Ore and wage do not appear before the scheduled due time. At due, exactly one ore is produced; the pre-funded wage transfers once from mine to miner, and the miner posts only its actual local ore stock.
4. Carlos must travel to the mine. A real local offer and accepted player purchase move the produced ore and one copper through the existing event reducers; the mine cannot sell more than its actual stock.
5. A second extraction attempt with zero reserve is rejected with no state mutation. Track `reserve + mine ore + Carlos ore == 1` at the relevant post-extraction checkpoints; total copper remains 2.
6. `verify`, snapshot, and reopen reproduce the final event-sourced state. Existing PLAY-46 market/production and PLAY-48M finite wood-to-charcoal regressions keep their existing results.
7. No production source code, event type, schema/rules version, migration, story, UI, or persistent-world bootstrap change is needed unless the existing generic recipe path proves insufficient.

## Planned files

- `simulation/tests/test_world01c_finite_mine.py`: isolated finite extraction and local player purchase proof.
- `simulation/docs/WORLD_01C_FINITE_MINE_ANALYSIS_2026-11-27.md`: this pre-execution analysis and final evidence.
- `simulation/docs/WORLD_01_ANALYSIS_2026-11-27.md`, `simulation/docs/WORK_QUEUE.md`, and `simulation/docs/CARLOS_NEXT_CHAT_HANDOFF.md`: milestone and next-step record.

## Explicitly out of scope

Geological simulation, renewing veins, extra resource generation, autonomous mine planning, mine expansion, workforce rescue, new charcoal mechanics, continuous industrial demand, long-term mine viability, story changes, player UI, migration, release approval, merge, and any change to PR #185.

## Result

The generic production path was sufficient, so this milestone adds no engine source
code. The new disposable-world test uses one initialized `iron_ore_reserve`, a real
miner shift, a pickaxe, and a fully funded local wage. With the focused
`LivingWorldEngine`, the miner autonomously starts its recipe at time 0; the reserve is
consumed then, and ore, wage and a miner-owned market quote remain absent until the
120-second scheduled completion. The engine then produces one ore, pays one copper from
the mine's existing till, and posts a quote for the actual ore stock. Carlos travels to
the mine and buys that unit for his own copper. A second extraction with zero reserve,
and a separate world initialized with zero reserve, are rejected atomically.

The checked ore ledger remains one unit across the conversion:
`reserve + mine stock + Carlos's stock + running extraction reservation == 1`.
The world's two copper remain conserved. Snapshot, verify and reopen match the final
state. No persistent geology or replenishment is implied. The existing finite timber to
wood to charcoal chain remains in PLAY-48M and was tested as a regression, not duplicated.

Verification: **2/2** new tests; **6/6** combined finite-mine, metal-market, finite
charcoal and physical smelting tests on Python 3.12.14. The full suite on the
code-and-test commit `d655ae4e20add05a407127fc0c6cc67c5b75b5c6` passed **1951 tests,
1 skipped** on Python 3.10.22 (25:05) and Python 3.13.5 (19:45). No source code,
Schema46/Rules73, story, UI or PR #185 changed. GitHub Actions has no run for this
locally held commit; exact-head Actions verification is still required before closing
WORLD-01c. WORLD-01 remains in progress.

Next: publish/check the exact branch head in GitHub Actions. Only after that succeeds,
analyze WORLD-01d, an end-to-end disposable-world run that joins the proven finite mine
and wood-to-charcoal sources to Carlos's physical procurement and blacksmith job, with
exact opening budgets and no extra stock introduced to make the test pass.
