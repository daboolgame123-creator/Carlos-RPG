# PLAY-28B — finite hydrology and explicit rainfall (design-only gate)

**Status:** DESIGN_READY / NOT_IMPLEMENTED / NOT_TESTED
**Draft baseline:** PLAY-28A `264258fef0d8e2068e0d4d9ea5def6392058b4c6`
**Branch:** `design/play28-b-water-replenishment-20261108`
**Activation gate:** Do not implement on the PLAY-28A integration branch until its targeted,
three-day, and comprehensive Python 3.10/3.13 CI checks pass on an identical SHA.

## Objective

A well may run dry. It can recover only after an **explicit, authenticated, finite**
rain/recharge input. The existing courier still moves water between the well
and farm using traveled adjacent roads. Growing a crop still debits one
unit of water. A rain input is an external material boundary, not spontaneous
water generation by idle ticks or AI prose.

No general-purpose weather prediction, drought narrative engine, or
automatic climate loop in this slice.

## Proposed durable domain model

Add a new, explicitly versioned `hydrology_sources` mapping keyed by an
existing **location ID** (initially only `well`). Suggested source state:
- `capacity`: bounded nonnegative integer configured only at time-zero
- `received_total`: cumulative accepted units from measured refill events
- `overflow_total`: units explicitly lost to overflow, or reject overflow
  outright (preferred for v1)
- `last_refill_at`: logical timestamp, or null
- `refill_ids`: bounded stable IDs for exact-once replay, or separate
  append-only ledger. Choose one authoritative representation, not both.

Configuration must require a known, initialized `well.water` balance
`0 <= water <= capacity`, and reject nonexistent sites, duplicate
configuration and invalid amounts.

**Migration:** New persisted fields/events must bump both Schema and Rules
deliberately (candidate 37 / 49), and update all tests that explicitly
assert 36 / 48. Genuine historical 36 / 48 worlds must be refused
**without any mutation** unless a separate explicitly reviewed migration
is implemented. Prior feature-off behavior must remain unchanged.

## Candidate event contract

- `WaterSourceConfigured`: bootstrap-only, actor=null, time=0,
  payload `{site_id, capacity}`, known initialized well water.
- `RainWaterRecorded`: active-session-only and dedicated
  `hydrology_authorized` capability, actor=null, event.time exactly
  equal to persisted logical time, payload
  `{source_id, observation_id, units}`.
- `units`: strict integer >0, bounded by `capacity - current_water`
  and by per-event maximum; observation IDs must be globally unique
  within that source; no double counting by duplicate commands.
- No `ResourceChanged(source="rain")` fallback, no generic
  `agriculture_authorized` authority to mint water, and no
  `ScheduledEventCreated` user-injected protected recharge.
- Rain is **manually supplied observed input**. The engine must never
  autonomously invent `RainWaterRecorded` when `advance()` is called.

The exact field list, authority boundary, integer bound and replay
validation must be ratified before implementation. Store command
request hashing must include the new authority flag; the pure
`apply_event` validator must independently enforce that flag;
the store must check the active session, atomicity and revision.

## Conservation audit

At each checkpoint:

```
initial_well_water
  + sum(accepted_rain_units)
  = water_at_well + water_at_farm + water_in_courier_cargo
    + sum(water_spent_on_started_crop_growth)
    + any explicitly tracked overflow
```

For v1 prefer **rejecting** any rain beyond spare capacity:
overflow = 0 and the identity stays simple.

Check every intermediary and replay, including a courier loaded
mid-route, cargo delivery, planting, crop maturation, market food,
and personal meals. Rain never credits farm directly; it arrives
at the well and must be moved along the actual courier circuit.

## Scenario matrix (disposable worlds)

1. **Drought:** rain=0; well depletes; no fresh crop after water
   runs out. Hunger may rise; no miraculous credit or teleport.
2. **Moderate rain:** one explicit measured refill at a fixed logical
   tick; water stored only up to well capacity; later physically
   collected and delivered, with crop growth on its genuine
   schedule; no anticipation before the observation tick.
3. **Heavy rain / overflow:** reject overcapacity or account
   deterministically for overflow; all counters and balances
   remain conserved.
4. **Adversarial:** untrusted forged rain, missing source, double
   observation ID, negative/boolean/oversized units, stale revision,
   duplicate command, paused session, different event time,
   wrong authority, and source-capacity mutation. No partial commit.
5. **Replay:** independent database parity and snapshots; verify
   reload after restart with rain + courier cargo in flight.
6. **Endurance:** compare drought, moderate and rainy seven-NPC
   runs lasting >=3 logical days with full survival, actions,
   agriculture and logistics enabled. Distinguish *continued
   simulation* from *actual sustainable nutrition*; rainfall
   alone does not guarantee food sufficiency.

## Implementation order after PLAY-28A gate

1. Minimal schema/rules bump, source configuration, passive validation.
2. Dedicated `RainWaterRecorded` reducer and strict capability in
   `store.append` and `apply_event`; no autonomous emitter.
3. Authenticated local injection API using active clock and
   expected revision, not a player UI action.
4. Counterfactual tests drought vs measured rain; prove bounded
   storage and real courier delivery.
5. Targeted CI on Python 3.10/3.13, then comprehensive CI on
   the **same SHA**, plus predecessor feature-off parity and
   no-migration integrity checks.
6. Only then update PLAY-28 status and handoff evidence; do not
   claim system production readiness or external review.

## Specific risks identified in source inspection

- `domain.py` currently accepts `ResourceChanged` only for
  initialization or owner consumption: do **not** weaken that
  generic source to permit unrestricted rain.
- `agriculture.py` debits exactly one water unit on
  `CropGrowthStarted`; avoid counting mature crop as a
  second water debit.
- `supply.py` courier stock is one physical unit per active
  water consignment; observe that mid-travel unit in conservation.
- `living_world.py` advances time only after an explicit user
  command; no rainfall should arise from wall-clock downtime.
- `store.py` hashes capability flags into command identity and
  validates the active session. Follow the same pattern for
  hydrology authorization and include it in replay-safe writes.
