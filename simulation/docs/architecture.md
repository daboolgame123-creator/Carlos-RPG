# Implemented architecture (Phase 01-A)

1. `DomainEvent` is a versioned, validated JSON-compatible envelope. Only four event types have reducers in this phase.
2. `apply_event(WorldState, DomainEvent)` is a pure deterministic projection. World state and nested mappings are immutable after construction. A rejected event does not mutate the previous state.
3. `SQLiteEventStore.append` opens an `IMMEDIATE` transaction, validates the expected world revision, applies all requested events in memory, and stores a command idempotency record, ordered event envelopes, and world head metadata atomically. A failed batch rolls back.
4. `load` can begin from the latest verified snapshot or genesis. It applies tail events in event sequence order. `verify` compares snapshot-based state against an independent genesis replay.
5. `snapshot` stores a canonical JSON state and SHA-256 hash in one transaction. Snapshotting and reading never advance simulation time.
6. `player_view` exposes only world ID, current logical time, and revision; no hidden NPC data is published until proper perception and visibility mechanisms exist.

## Schema

SQLite tables: `worlds`, `commands`, `events`, `snapshots`. Event sequence is per world and equals post-event world revision. `worlds` stores immutable genesis JSON plus current head metadata. Event payloads and snapshots have stable, canonical SHA-256 hashes. SQLite foreign keys are enabled.

## Boundaries and deliberate exclusions

- No background timers, wall clock simulation or real time progression.
- No NPC choices or time scheduling in this phase.
- No session authentication or network API; `append` is a trusted application API only.
- No actual story state; tests create their own worlds.
- A full event schema registry, rule version migrations and replay of model-generated dialogue are deferred.

## Integrity assumptions

One SQLite writer is coordinated through `BEGIN IMMEDIATE`. Duplicate `command_id` and identical command content is idempotent; reusing an ID with different content is rejected. Revisions protect against stale updates. A valid SQLite transaction commits the event batch as a unit. A write-capable attacker who can edit database files and hashes is outside the current threat model.
