# 03-A6 — material-backed scheduled NPC recovery design and acceptance

Status: IN_PROGRESS, unverified design contract. Base: code SHA `201d79a8` (03-A5 exact-SHA CI green).
No edits to main or property/legal branch.

## Scope
An NPC caregiver in the same location as an injured NPC can begin one 600-logical-second recovery treatment by spending exactly one **caregiver-owned** unit of the existing `food` resource, with a fixed improvement of 10 injury points when and only when the scheduled event becomes due and both NPCs remain physically present. This is supportive care/rest, **not** a clinical or magical healing model. It neither changes player HP nor adds medicine out of nothing.

## Source of truth and invariant
- Dedicated `RecoveryStarted` event runs only through trusted, active-session `recovery_authorized` capability, persisted in the commands table for full replay.
- Treatment record persisted in versioned `WorldState.treatments`. Start deducts `food` once from caregiver and creates a `scheduled` signal `{"__npc_recovery": treatment_id}` in the **same atomic store.append command**. All IDs, owner, location, time, schedule, resource, amount and improvement are validated against current immutable state.
- At due time the normal `ScheduledEventFired` reducer checks stored treatment and schedule and invokes `compute_recovery_transition`. If either NPC left the site, became busy or traveled, treatment becomes `interrupted`, no severity improvement, and spent food stays spent (no refund or unexplained resource minting). No event can fire before due, late, twice or out of order.
- Generic schedule creation must reject `__npc_recovery` without recorded trusted recovery capability and a pending treatment created previously in the same atomic command.
- Generic cancellation of a recovery appointment is forbidden; explicit cancellation/refund rules are future work. One pending treatment per injury, and no stale/evolving injury overwritten.
- World schema increments for the `treatments` collection and new SQLite command capability. Old worlds are rejected without migration or mutation.
- Player view remains hidden for NPC injury/treatment details.

## Verification
- Success path start, exact cost once, wait partial, due-fire, recovery updated 10 and persisted after restart, full replay, snapshots.
- Invalid: fake schedule, wrong injury/owner/site, idle caregiver missing stock, travel, duplicate treatment, fake improvement, wrong event actor/source, unauthorized/no-session, rollback, command idempotency.
- Cancellation protection and interrupted recovery.
- All historical parity/smoke/backup tests pass on Python 3.10 and 3.13 on exact SHA. No production approval without external review.
