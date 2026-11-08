# PLAY-28 — Real daily survival, food, rest, and work scheduling

**Status:** ANALYSIS_COMMITTED / IMPLEMENTATION_PENDING (2026-11-08).
**Base:** PLAY-27 documentation closure `1c2d86019e80159cc86c350576749345bbf0e29a`.
**Branch:** `simulation-engine-phase-play-28-survival-rest`.
**Safety:** no edits to `main`, canonical Carlos story, production P0 approval or historic feature-off semantics. External review deferred by owner.

## Why this phase is necessary

PLAY-27's 260,700-second economy-only trials disabled routine NPC actions; they are NOT evidence of livable endurance. Its limited full-metabolism trial reached hunger/fatigue 100 and stopped the harvest. The resource flow physically worked (well → field → bakery → market), but daily routines and food access do not yet make the village sustainable.

## Deliverable A — daily survival (first, narrow executable slice)

1. Observe hunger and fatigue in *existing* authoritative NPC needs, not a second shadow state.
2. Allow resting/sleeping to consume real simulation time; make it interruptible, location-bound, and compatible with existing work shifts and actions. No instant fatigue reset, teleportation or free food.
3. NPCs choose to eat only reachable, unreserved, personally owned food or food acquired by the existing purchase/transfer rules; no remote seller inventory telepathy. Consigned cargo can never be eaten by a courier.
4. Hunger and fatigue must influence work eligibility and travel, without permanent busy-spin or an infinite action chain when food is absent. Preserve deterministic decisions and explicit time advancement only.
5. Preserve atomic event batches, replay, save/restore and strict event/capability validation. Any new persistent event/field requires a deliberate Schema/Rules bump and compatibility handling.
6. Do not silently replenish copper or food. Absent provisions must cause measurable hunger and reduced output, not fictitious survival.

## Deliverable B — bounded water source (separate acceptance gate)

Implement only after A is green: a finite hydrological source with *explicit* rain/refill inputs, storage capacity and physical transport. No unbounded resource creation. Compare dry, normal, and rainy deterministic conditions, with no clairvoyant future weather for NPCs. Do not present this as a full weather simulation.

## Required real tests

- One baker: works → reaches bounded fatigue threshold → rests through explicit clock time → returns to work; also a no-food case that does not fabricate meals.
- One farmer: harvest cannot proceed without genuine seed, water, tool, physical time, and sufficient condition.
- One courier: retains consigned food even while hungry; does not accept cargo when too exhausted to deliver; valid cargo remains conserved across stop, rest and recovery.
- Seven named NPCs: at least 3 in-world days **with full metabolism and daily NPC activity actually enabled**; test starvation/shortage branch and provisioned branch independently. Do not pass by setting `economy_only_enabled=True`.
- Assert conservation of food, grain, seeds, water, cargo and copper across all participants, locations, reserved work, eating, and sold stock; no double sale/meal.
- Test boundary times, save/restore/replay, rejected forged events, oversized event budget rollback and disabled-feature historical parity.
- Targeted pytest on Python 3.10 and 3.13, then full regression on **the same code SHA**, including inherited frozen predecessor-parity and integrity checks. Link both successful GitHub Actions runs; report failures as failures.

## Design constraints and implementation order

1. Inspect `living_world.py`, `routines.py`, `npc.py`, `consumption.py`, `domain.py`, `time_engine.py`, `supply.py` and the PLAY-27 scenario before modifying behavior. Locate existing rest/need reducers; extend rather than duplicating.
2. Commit focused implementation and test changes in separate steps; begin with an isolated single-NPC rest and meal lifecycle, then the seven-NPC integrated world.
3. Keep water replenishment separate from rest/survival so the root cause of an endurance result is visible.
4. Close only after both CI gates succeed and a closure report states actual statistics, limitations and the exact tested SHA. Keep PLAY-14g, 03-A7c / 03-A, P0 and external review open.

## Explicit non-goals for this phase

No supernatural abilities, infinite water, unrestricted dynamic trade network, generalized weather, full wages/pricing, large-world performance claim, or proof of production readiness.
