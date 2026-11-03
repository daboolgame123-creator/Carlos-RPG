# Implemented architecture (Phase 01-A)

1. `DomainEvent` is a versioned, validated JSON-compatible envelope. Four event types have reducers. Ordinary events cannot advance time; non-null actor references must exist.
2. `apply_event(WorldState, DomainEvent)` is a pure deterministic projection. World state and nested mappings are immutable after construction. A rejected event does not mutate the previous state.
3. `SQLiteEventStore.append` uses a caller-supplied `bootstrap` flag, persisted with each command for deterministic replay. Initial resource allocation is permitted only in trusted bootstrap at time zero; consumption requires a matching owning actor and cannot increase a balance. This is not a network authorization boundary. It opens an `IMMEDIATE` transaction, validates the expected world revision, applies all requested events in memory, and stores a command idempotency record, ordered event envelopes, and world head metadata atomically. A failed batch rolls back.
4. `load` can begin from the latest verified snapshot or genesis. It applies tail events in event sequence order. `verify` compares snapshot-based state against an independent genesis replay.
5. `snapshot` stores a canonical JSON state and SHA-256 hash in one transaction. Snapshotting and reading never advance simulation time.
6. `player_view` exposes only world ID, current logical time, and revision; no hidden NPC data is published until proper perception and visibility mechanisms exist.

## Schema

SQLite tables: `worlds`, `commands`, `events`, `snapshots`. Commands also retain their bootstrap provenance. Rules version 2 rejects older experimental databases without migration. Event sequence is per world and equals post-event world revision. `worlds` stores immutable genesis JSON plus current head metadata. Event payloads and snapshots have stable, canonical SHA-256 hashes. SQLite foreign keys are enabled.

## Boundaries and deliberate exclusions

- No background timers, wall clock simulation or real time progression.
- No NPC choices or time scheduling in this phase.
- No session authentication or network API; `append` is a trusted application API only.
- No actual story state; tests create their own worlds.
- A full event schema registry, rule version migrations and replay of model-generated dialogue are deferred.

## Integrity assumptions

One SQLite writer is coordinated through `BEGIN IMMEDIATE`. Duplicate `command_id` and identical command content is idempotent; reusing an ID with different content is rejected. Revisions protect against stale updates. A valid SQLite transaction commits the event batch as a unit. A write-capable attacker who can edit database files and hashes is outside the current threat model.

## Phase 01-B extension

`WorldState` now projects `scheduled` (active scheduled signals) and `next_schedule_order` from domain events. The schedule is part of the event-sourced state and therefore persists through snapshots and deterministic replay.

The only supported future item type is `signal` with a JSON payload and an explicit interruption flag. `TimeEngine` advances the logical clock during an open in-process session. At each earliest due time, the engine emits a `TimeAdvanced` event, then `ScheduledEventFired` in stable order. `ScheduledEventCancelled` removes pending signals. Firing a signal never itself changes resources or NPC intentions.

Events due at the same time are sorted by due time, monotonically increasing schedule order, and ID. An interrupting signal halts the current advance after recording the occurrence. The remaining requested duration is returned for an optional later action. Event batches are committed atomically by the store; a configured per-command event cap prevents runaway processing.

`TimeAdvanced` and `ScheduledEventFired` require a trusted internal `clock_authorized=True` append flag; this is an application convention, **not user authentication**. Schemas change from 1/2 to 2/3; test DBs from Phase 01-A must be explicitly re-created or migrated. Real-world elapsed time is never used.

## Phase 01-C: NPC prototype

`WorldState.npcs` is an immutable, event-projected dictionary. `NPCConfigured` is bootstrap-only. `NPCBeliefReceived` adds a claim to the intended individual's private beliefs; `NPCNeedChanged` validates previous/current need values; `NPCDecisionRecorded` validates actor identity, action, policy score and decision cooldown. `NPCService.decide` checks active session and optimistic revision before recording a decision with `npc_authorized=True`. The flag is an internal convention only, never an API permission mechanism. No intention is automatically translated into an action or state change. Schema/rules versions are now 3/4.
