# PLAY-30A — physically bounded harvest-yield experiment

**Status:** IMPLEMENTED FOR CI / NOT VERIFIED UNTIL ACTIONS SUCCESS.  
**Branch:** `experiment/play30-bounded-harvest-yield-20261108`  
**Version:** Schema **39** / Rules **51** unchanged: this is a *trusted disposable-world recipe choice*, not a change to the engine's persisted event contract.

## Question

In the same seven-NPC medieval village, will a more fertile, explicitly configured plot produce more grain, and will existing NPC logistics distribute it? Do not confuse "crop matured" with "food actually accessible to consumers."

## Method

- Keep the same **one** real plot, **one** initial seed, **two** finite well-water units, two-day growth cycles, farm labor/hoe/sickle, travel, mill/bakery labor, local copper, autonomous NPC plans and bounded courier routes.
- Freeze the trusted `finite-harvest` production recipe at creation: either **one grain** or **three grain** from each real one-unit ripe crop. The three-grain case represents *experimental biologic yield* from the same ripe harvest lot; a stored recipe, **not** a runtime mutation or any newly minted grain command.
- Reuse existing `ProductionStarted` / `ProductionCompleted` scheduled job events, no instantaneous crops. No policy may be changed by Carlos after bootstrap.
- Audit seed/water equality, actual ripening, single-person action exclusivity, copper equality and no unknown stock. Extend grain-equivalent accounting to count **ripe crop lots and active harvest reservations at their documented yield**, without double-counting them together with finished grain.
- Simulate two real harvests for 7 NPC at fixed water, with separate dry/seedless/tool-less negative controls. Compare crop maturity, actual harvest and baked items, market transfers, personal consumption and accessible food; do not assume gain in health from additional stock alone.
- Default is exactly `harvest_yield=1`; old fixture initialization remains bit-for-bit equivalent. Only `harvest_yield in {1,2,3}` with strict integer type is allowed.

## Acceptance gates

1. Targeted CI on Python **3.10** and **3.13**: real double-harvest A/B with physical audit; drought, seedless and no-hoe; invalid yield rejections; snapshot/replay and anti-mint injection.
2. Full exact-SHA regression/compatibility on the same two Python versions.
3. Documentation of measured outcomes, including whether real baking/distribution progressed (not mere theoretical grain); explicitly record any remaining survival shortfall.

**Out of scope:** expanding acreage, seed breeding, soil fertility simulation, terrain constraints, rainfall generation, real food demand economy, wages, canonical world saves. No `main` edits, no productive/P0 approval, no external independent review claim.

This first slice measures what the existing versioned production contract can already represent. A general persisted soil/land/yield system would need its own explicit future Schema/Rules bump, compatibility suite and authorization boundary; do not silently add it.
