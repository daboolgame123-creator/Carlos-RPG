# Phase 01-U — Provisional design: travel to remembered food by known roads

**Status:** DESIGN RECORDED, **IN_PROGRESS**, subject to the conditional-transition governance in [DEVELOPMENT_PROTOCOL.md](DEVELOPMENT_PROTOCOL.md) §J. Phase 01-T is `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING`, **not independently APPROVED**.

**Branch:** `simulation-engine-phase-01u` forked from green Phase 01-T documentation checkpoint `d2a397bde95d2596592818f348d68b030f78f48a`.
**Baseline:** Schema 13 / Rules 18; 544 passing tests per Python 3.10 and 3.13, CI [41928668332](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41928668332).
**Type:** opt-in planner/behavior, knowledge/privacy; no new event fields, no schema/rules changes or historical migration.
**Worlds:** disposable synthetic villages only. P0 backup/restore certification remains OPEN.

## Objective and testable behavior

A hungry NPC with **no owned food**, sufficient physical capacity, and a *private belief* that a reachable destination contains food can independently begin a journey using **only that NPC's learned roads**. The selection must be causal even if a rumor is false and the real destination is empty.

The NPC must never peek into remote `resources`, the private beliefs of other NPCs, routes not in its own navigation record, or a hidden global atlas. Starting a trip never materializes food, teleports the actor, reserves a remote deposit, or promises a successful forage. Physical travel takes the exact route duration; an arrival observation under `knowledge_enabled` can correct a false/outdated belief. Existing local forage priority remains higher than optional exploration/food navigation.

## Feature boundary

- New explicit coordinator flag: `food_navigation_enabled=False`. When true, require `navigation_enabled=True`, `knowledge_enabled=True` and `foraging_enabled=True` (otherwise fail config validation). Default-off legacy behavior must retain the 01-T event digest and semantic digest.
- New **pure** food-route chooser: take only the current NPC's `food:*` beliefs and `navigation[npc_id].known_routes`. Apply the same hunger/fatigue/safety/private danger/owned food eligibility as 01-S local forage. The current site cannot be a travel destination.
- Candidate `food:present` sites need a positive effective confidence and an existing `shortest_known_route`. Never treat `unknown` as `empty` or as evidence of food. Select by minimum total **known** travel seconds, then higher effective confidence, then lexical site and path; no RNG.
- Preserve an explicit NPC `navigation.target` assignment; a food whim never silently replaces it. Continue any existing action/travel without preemption. Respect an already recorded same-tick action decision and the established decision cooldown; waiting on a cooldown must not cause the NPC to start optional exploration away from an eligible, reachable remembered source.
- Coordinator surveys **only local adjacent roads** as already implemented, then evaluates the food route, then falls back to unchanged `next_route` if no food intent. Food travel records a normal `ScheduledEventCreated` + `NPCTravelStarted` with an explanatory reason naming the subjective belief, known destination and path cost. There is no new entity, event type, or reducer rule.
- At each reached location, existing `ScheduledEventFired` + 01-T arrival observation executes, and the next decision is recomputed. At a truly stocked destination, 01-S local forage can start; if it was empty, the new direct `food:empty` belief suppresses repeated travel toward the same mistaken claim. Nobody is guaranteed food or rescued by magic.
- Never implement supply regrowth, path capacity, rumor truth-filtering, combat, economy, manual-player controls, or Carlos story import in 01-U.

## Failure and security matrix

1. Distant abundance without a learned `food:present` belief must not initiate food travel; the chooser's output remains unchanged if remote truth or other NPCs' private beliefs are modified.
2. Food belief without any connected **known** route must not create an invented route or teleport. Survey only reveals roads at the current node.
3. False hearsay may induce a wasteful but lawful trip. Arrival converts the *recipient's* own belief to a direct observation (or remains unknown if site's stock is uninitialized); other characters are unaffected.
4. Hunger/fatigue/safety/danger/owned-resource constraints must be respected; unknown personal food is not zero. Explicit target/action decisions take precedence.
5. Repeated commands are idempotent; partial event-budget or closed-session failures commit nothing. Split-step vs single-step must preserve semantically equivalent physical events for the same boundary.
6. Provenance: action reason reports subjective belief and estimated **known-route** cost; resources and destination contents are never included as facts.
7. Snapshot, SQLite close/reopen, full event replay, `verify()` and 01-T default-off parity must remain green. Test Python 3.10 and 3.13.

## Implementation outline

- `src/carlos_sim/food_navigation.py`: pure chooser, constant policy, deterministic `FoodRouteIntent`.
- `src/carlos_sim/living_world.py`: opt-in flag and known-road route-selection call before existing navigation; same travel scheduling/events and local-forage priority.
- `src/carlos_sim/__init__.py`: optionally export public pure selector.
- `tests/test_food_navigation.py`: actor-isolated unit tests, false-rumor journey, real arrival and post-arrival forage, unknown stock, path and stamina constraints, priority and persistence, strict event budget and legacy flag-off checks.
- `docs/phase_01u_report.md`: tested results, compatibility assessment, pending independent review, and remaining gaps.

**Acceptance:** only a passing implementation with immutable CI evidence may be called `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING`. It must never be described as independently `APPROVED` without a separate reviewer. Reevaluate if Phase 01-T receives a blocking finding.
