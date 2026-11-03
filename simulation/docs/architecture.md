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

## Phase 01-C post-review invariants

- The SQLiteEventStore session set is shared by all TimeEngine instances attached to that store. Mutating NPC events are blocked while that world is paused; replay and snapshot recovery remain read-only and work without an active session.
- NPCDecisionRecorded validates next_decision_at >= current_simulation_time + 60, as well as the deterministic score/actor checks. The service cannot configure a cooldown below 60 seconds.
- NPCInformationDelivered stores an explicit, time- and location-checked delivery in the destination NPC inbox. BeliefReceived requires an existing delivery ID, matching key and recipient actor and consumes it once. Delivery history prevents reusing identifiers after acknowledgement. A trusted NPC capability is required to register information delivery. This is an audit of reported provenance, not external cryptographic authentication or guaranteed rumor truth.
- Schema/rules versions are 4/5; earlier test database formats are rejected pending an explicit migration.

## Phase 01-D: scheduled NPC action execution

`NPCActionService.start` requires a previously recorded intention at the same simulation time, an active play session, and fresh world revision. It atomically submits a trusted `ScheduledEventCreated` signal with reserved `__npc_action_id` payload and a matching `NPCActionStarted` event. `WorldState.actions` is immutable and records the start, due time, running/completed status and bounded outcome. Per-NPC overlapping actions are rejected; different NPCs can act concurrently.

The existing `TimeEngine.advance` drives all completion signals in chronological order. On `ScheduledEventFired`, the state projector calls the deterministic action resolver **before** removing the matching signal and produces needs/counter effects within the same transaction. These are derived domain effects, not separate commands, and are replayed identically. Automatic NPC completions are not player interrupts; explicitly interrupting signals remain so. Cancelling a running action's scheduled signal is rejected rather than creating a stranded action.

Durations, bounded effects and resource-counter requirements are fixed prototype rules, not Carlos story facts. Generic `ResourceChanged` cannot consume or mint reserved action counters after initial setup; only a completed, auditable action increments them. A live `SQLiteEventStore` session is now required for all clock writes, including trusted low-level calls, closing an earlier direct-call bypass. The action capability is an internal convention only, **not authenticated authorization**. World schema/rules 5/6 reject earlier prototypes pending explicit migration.

## Phase 01-E — Autonomous lifecycle coordinator

`carlos_sim.living_world.LivingWorldEngine` is a trusted, opt-in orchestration layer above the existing event store and immutable reducers. For an explicitly authorized advance command, it simulates the complete timeline in memory and submits a **single** atomic event batch via the existing `clock_authorized`, `npc_authorized` and `action_authorized` capabilities. It neither changes the database schema nor the event reducer contracts (schema v5/rules v6).

At each timestamp: existing due signals are fired in durable `(due, order, id)` sequence; a signal marked for player attention interrupts before further autonomous planning at that instant. Idle NPCs whose cooldown has elapsed are processed in ascending NPC ID order. Each makes a strictly per-NPC, deterministic knowledge-limited decision; its matching completion signal and `NPCActionStarted` event are created in the same transaction. Then the clock moves to the earliest due signal, the earliest newly eligible idle NPC decision, or the caller's target time. NPC actions and user-visible interrupts may occur at the same logical timestamp without skipping queued signals.

Each NPC's autonomous action ID is derived deterministically from `(npc_id, start_time)`; collision is rejected, not silently merged. Action completion effects use the existing strict action resolver. An event count limit is checked **before** every projected event; exceeding the budget aborts the entire advance and writes nothing. The original `TimeEngine.advance` is unchanged as a manual mode. This layer does not automatically progress while disconnected, and deliberately excludes NPC movement, actual inventories, social relationships, knowledge perception, trade, combat, LLM narration, and a player-action ingestion API.
