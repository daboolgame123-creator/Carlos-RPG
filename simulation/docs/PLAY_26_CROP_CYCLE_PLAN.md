# PLAY-26 — bounded seed → timed crop → harvest → bread cycle (implementation plan)

**Status:** IN_PROGRESS / NOT_CLOSED (2026-11-08). **Parent:** PLAY-25 technical closure `1443f7b5e7ec4a35f1c99e5122e9d6beb628ebf0`.
**Branch:** `simulation-engine-phase-play-26-crop-cycle`. No `main` or canonical story modifications, no P0 approval or outside review.

## Verified problem and constraints

PLAY-25 harvested **finite pre-ripened** `crop_ready`, but cannot plant seed or wait for a real growing crop. Existing `ProductionRecipeConfigured` lets a farmer perform real 60-second `seed -> crop_seeded` planting work with a hoe; the worker must be physically present, equipped and on shift. Unlike production jobs, the crop must then grow *without keeping the farmer busy*. An existing environmental cycle applies only to `regrowth_reserve -> wild_food`; silently converting that system into magical farm stock is prohibited.

## Packages and success gates

1. New **opt-in** farming state/event projection with a configured plot at a real place and soil capacity; `CropGrowthStarted` consumes a previously planted `crop_seeded` and **one finite water unit**, schedules maturation after an explicit logical interval (one day), and stores durable plot status. A protected clock-firing matures to **one ripe crop and one seed** (biological seed yield from the planted seed), with bounded crop capacity; no untracked refills. Counts and schedules must replay deterministically.
2. Extend existing NPC economic planning with a planting recipe (farmer physically performs 60-second work, hoe required), a pure local selector to start growth after planting, and a dedicated `agriculture_enabled=False` gate that additionally requires `economic_enabled=True`. No direct player control over Nora/Basim/Salma/Adel, and no unseen remote resource knowledge. Keep stable scheduling and event-batch atomicity.
3. For long-range experimental snapshots, an explicit `economy_only_enabled=False` opt-in to suppress unrelated idle NPC action spam while **still executing agriculture, bakery and market decisions** at due times and daily shift boundaries. Only use this mode in the duration-stress scenario; it cannot be described as a full village survival/life simulation. This permits several logical days and finite resources without thousands of superfluous generic actions.
4. Disposable seven-NPC world starts with **zero grain and zero ripe crop**, finite seeds, water, hoe, sickle, oven and copper; growing may produce multiple sequential finite harvests if resources permit. Test no seed, no water, no hoe, out-of-shift, absence, capacity, plant+harvest contention, multi-day time, rollback, deterministic replay, SQLite restoration, original opt-out, and private player handoff.
5. Launch targeted Python 3.10 / 3.13 CI plus existing full regression for the **same SHA**. Only if both succeed may `WORK_QUEUE.md`, `ROADMAP.md`, the plan and report be closed in a separate docs-only commit.

## Resource logic and boundaries

One seed and one water are *debited* at planting+growth; after one full day, a mature crop is made via soil/sunlight/water and a seed is recovered through plant reproduction. The growth is documented, not an uncaused reset. **Water is finite**, and dry land stops planting; this proves at most a few harvests, NOT an indefinitely sustainable economy. No weather simulation, rainfall, free water, wages, dynamic prices, intersite cargo, starvation death or full multi-day NPC-survival proof in this batch. Those require follow-on stages and their own tests.
