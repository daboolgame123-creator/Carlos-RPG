# PLAY-28 — Real daily survival, food, rest, and work scheduling

**Status:** PLAY-28A CLOSED_TECHNICALLY (2026-11-08); PLAY-28B isolated integration in progress (not merged).
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


## PLAY-28A — verified technical closure (2026-11-08)

**Exact tested code SHA:** `b17f390cca49b8467f7b43edcb88ca56788d64c5`.
**Schema / Rules:** 36 / 48.
**Branch:** `simulation-engine-phase-play-28-survival-rest`; no merge to `main`.

All three GitHub Actions gates completed SUCCESS on the SAME code commit,
with Python 3.10 and Python 3.13:
- Focused real resting/meal/courier/production safety:
  https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42466507878
- True three-day active NPC metabolism + physical production/logistics:
  https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42466507869
- Full predecessor-aware simulation regression suite:
  https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42466507857

Three-day trial observed **two independently initialized seven-NPC worlds**,
each at 259,200 seconds with all metabolism and everyday behaviors enabled:
- **No food allotment:** daily NPC action counts [171,174,174],
  0 meals, 1 matured crop, 1 courier delivery; hunger reached 100.
- **Finite 18-food personal allotment per NPC:** daily action counts
  [150,164,174], 126 meals, 2 matured crops, 2 courier deliveries;
  some NPCs still reached hunger 100.
- Every quarter-day material audit, verified complete event replay, and
  a persisted snapshot comparison succeeded; no free food was credited.

**Interpretation:** Simulation continuity, resource conservation and
meaningful poverty consequences have been established. These results do
NOT establish food self-sufficiency, long-term economic sustainability,
safe production deployment, or closed external security review.

**Infrastructure issue resolved:** intermittent GitHub Actions HTTP 504
while installing Python 3.10; pinned CI runner to Ubuntu 24.04.
The final successful gate is stronger evidence than earlier interrupted runs.

**Next independent slice:** PLAY-28B finite hydrology uses Schema 37 /
Rules 49 on `design/play28b-integrated-hydrology-20261108`. It requires
separate acceptance and is not part of the validated PLAY-28A SHA.

**Review gates still open:** independent external review and legacy
release/production gates; never represent PLAY-28A as a public game release.
