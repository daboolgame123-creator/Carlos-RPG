# PLAY-48H2 — Causal spatial food-access audit, no recovery claim

**Branch:** `analysis/play48h2-causal-food-access-20261110` from `integration/play48h1-43-58-regression-gates-20261110`. **Version remains experimental 43/58.** Does not change game decisions, producer inventories, money, existing contracts, player visibility, routes or save state.

## Verified failure requiring a different correction

The real full 13-NPC 0→96h experiment at [GitHub Actions #42832657469](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42832657469) passed both runtimes but showed **zero 72→96h trades/jobs/meals/deliveries**, 12/13 at 100 hunger, with five original market loaves unpurchased and three saleable plus one reserved after H1's one paid ration. A fully funded, service-locked individual ration is authentic but has no leverage after workers have already become unable to travel. **Do not multiply wages or invent money until the local road/ownership reasons are measured**.

## The isolated operator-only instrument

`food_access_diagnostics.audit_food_access_barriers` accepts only a verified immutable `WorldState`, returns an entirely read-only view (without new event, event capability, NPC behavior or player API), and reports per NPC:
- exact physical site, hunger, fatigue, unreserved personally owned food, and separately any food parcel under courier custody;
- personally spendable known copper **versus courier exact-custody cash**; a missing slot remains unknown, not zero;
- **only personally learned** routes to market, actual route travel seconds, busy state, courier strict safety/health travel blockers;
- only currently on-site co-present seller's offered real food at its actual price, minus reserved cargo, with true individual affordability; does NOT infer future price or remote knowledge;
- signed but **unearned** employer escrow, distinct from personal ration and from saleable market inventory.

The module is explicitly not importable by NPC planning pathways and never supplies remote stock or route information as NPC decisions.

## Next genuine action — no cherry-picked proxy

Use this audit at the real 72h checkpoint and at the first wage/market access cutoff. Classify who is hungry, cash-stranded, geographically blocked, or holding entrusted rather than personal money; then design a **physically delivered, actually funded, accountable food-access route or professional contract** that can act *before* a courier reaches the 90-hunger cutoff. If the source cannot support it with original finite stocks, report the economic scarcity rather than modifying the scenario. Compare 0→96h with unchanged input copper/food/rain and require actual new post72 delivery **plus** attributable later work/meal/sale and preserved world replay.

**Not a recovery, not a P0 release, not a PLAY-48 closure, no merge to main.**


## Full genuine 72-hour causal cut-off experiment

`test_play48h2_72h_access_cutoff.py` runs the exact existing 13-NPC world with the original three market loaves and twelve copper; only two **existing** opening market loaves are signed into escrow. It replays 24/48/72h with each original rain receipt, then emits every worker's actual current location, physically known route to market, cash ownership/custody, hunger, and employer escrow in an **operator-only** log. Runtime behavior remains unchanged. **A passed test is a verified diagnosis, not a remedy.**
