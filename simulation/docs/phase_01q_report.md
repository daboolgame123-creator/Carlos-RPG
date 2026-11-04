# Phase 01-Q — Finite food recovery from the environment

## Purpose and scope

After closing three performance-focused phases, Phase 01-Q returns to
**causal, traceable simulation behavior**. The test world already
supported owned food, consumption and voluntary physical assistance,
but could not replenish an individual inventory from an environmental
food deposit. This phase establishes **finite gathering** without
adding complex farming, spawning, a biological growth model, trade
pricing, theft, combat or narrative generation.

A location can be bootstrapped with a known nonnegative integer stock
`wild_food`. A character can recover exactly one unit only **at that
location and immediately after completing their own 90-second
`investigate` action**. This is an explicit trusted-local action, **not
an autonomous AI policy**. The recovery occurs at the same logical
instant as the investigation's completion; it does not invent an
additional duration. If no resource exists or the deposit is
exhausted, the command fails without creating food.

## Event and conservation

`NPCFoodGathered` has `{npc_id, action_id, site_id}`, attributed to the
actual NPC, and uses the preexisting trusted `action_authorized`
capability. `SQLiteEventStore.append` also requires an active
session before committing this event. The reducer checks:

- distinct trusted action provenance: the NPC's own completed
  investigation, completed **at the current logical tick**;
- actual local presence (not in transit), no running activity;
- explicit preinitialized `wild_food` owned by the location and
  explicit `food` stock owned by the NPC, **never missing = zero**;
- action ID was not used for a prior gathering; quantity is always one;
- simultaneous collectors consume the finite stock sequentially in
  durable event order, and a second attempt cannot duplicate stock.

In the same event: site `wild_food -= 1`, owner `food += 1`.
The new frozen `WorldState.gatherings` history records action,
identity, site, time, transferred quantity and before/after balances.
Public snapshot and full replay validate history, including resource
conservation and matching previously completed investigation.

No actor can use ordinary `ResourceChanged` to mint wild or owned
food. Every state change remains deterministic, guarded by the
existing append transaction, revision comparison, capability storage,
event hashes, snapshot checks and fail-closed rollback.

## Compatibility

The extra durable `WorldState.gatherings` collection requires
**Schema 12 / Rules 16**. Previous experimental schema 11/rules 15
SQLite worlds are **not implicitly migrated**. Recreate isolated
fixtures or implement explicit audited migration before attempting
to reuse older saves. No actual Carlos story content has been
loaded or changed, and `main` remains untouched.

## Tests and scenario

GitHub Actions Python 3.10 and 3.13:
**432/432 tests passed** on each runtime before final documentation.
The Phase 01-Q suite added **13 tests**, covering scarcity, exactly
one recovery per completed investigation, two concurrent
investigators, unauthorized and distant actors, missing/unknown
inventories, session freeze, atomic rollback for duplicate attempts,
restart + snapshot + full replay, stale revision, audit corruption
rejection, and downstream real eating.

Existing 10- and 25-NPC scenario event digests, event counts, times
and revisions match independently checked-out Phase 01-P. Raw
full-state hashes are *intentionally different* because schema 12
adds a `gatherings` field and new version identifiers; each version
is independently verified by full event replay. Full 150-NPC
performance tests were deliberately **not** repeated in this
behavior-focused phase.

Runnable synthetic demo:
`PYTHONPATH=src python scenarios/test_village/demo_gathering.py`.
Two characters finish investigations at simulated second 90,
recover a total of 2 wild-food units from a deposit of exactly 2,
and one subsequently eats their owned portion. This is a disposable
test world, not an episode of Carlos.

## Out of scope / next step

The foraging command is **explicit**, not automatically initiated
by the autonomous planner. Food does not regrow while the app is
closed or while the logical time is frozen. This prototype does not
yet model ownership of land, hunting success, changing ecology,
seasonality, spoilage, agriculture, cooking, prices or death from
hunger. A natural next phase is **knowledge-limited autonomous
gathering** and local scarcity-aware intentions, with separate
careful validation of pathing, current inventory and resource
competition.

**Review verdict:** tested and complete within Phase 01-Q scope;
not a claim of production-ready gameplay. Final CI on this exact
documentation commit is recorded in the GitHub Actions branch runs.
