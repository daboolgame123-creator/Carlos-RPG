# PLAY-37B — causal experiment BEFORE any game-wide physiology change

This is **not** the PLAY-38 implementation and cannot close the root famine issue. The root plan is [PLAY-37](PLAY_37_ROOT_FOOD_ECONOMY_PLAN.md). We need to know whether the 300s hunger rate is the *only* reason workers fail, or whether independent fatigue, shifts, real local access and courier circuit logic would stop a calibrated world too.

Two independent 7-NPC worlds run **full NPC autonomous decision mode** for **48 logical hours** each. The same starting 3 physical market loaves, 2 water, 1 conserved seed, 3 grain per harvest recipe, 12 total copper, roads, worker roles and starting needs are supplied by the same tested bootstrap. No player actions, runtime gifts, extra harvests or teleported resources.

**One and only one changed factor:** The second world explicitly records the **preexisting trusted time-zero** metabolism policy `hunger_seconds_per_point=3600, activity_hunger_percent=20`; the baseline uses unmodified default `300,100`. This is a *controlled diagnostic*, not a change to old saves or game canon. Physical agricultural events, scheduled NPC rest, courier movement and real purchases must still happen normally. At logical t=0,3600,86400,90000,172800, track named worker hunger/fatigue, actual rest/work, farm jobs, harvests, bread, courier deliveries/blocks, market sales, true meals and individual hunger caps. Each checkpoint requires physical conservation, genesis replay and SQLite snapshots.

The necessary 72h food-budget math already proves both remain **unviable** over the longer horizon with only 9 theoretical loaves: at least 232 meals vs 9 at original rate and at least 12 vs 9 in slower mode, before effort and geographic access. The 48h trial only isolates *mechanism changes*, not a sustainable village. A genuinely feasible system requires bounded renewable water and enough physical output, worker rest, actual provisioning and paid local food transfer before day/week claims.

Quality: targeted Python 3.10/3.13 on final SHA; full historical regressions required before merge; `main` untouched. Open security/production P0 and independent external review.
