# Phase 01-F — route-based NPC movement and local perception

## Scope delivered

- Immutable, persistent bidirectional route graph (`RouteCreated`) with positive simulated traversal costs.
- Durable `NPCTravelStarted` and scheduled travel completion, which changes location only at the correct logical instant.
- Local, time-stamped `NPCObserved` snapshots and automatic arrival observations; only co-located entity IDs are visible.
- Travel/session/role validation, prevention of concurrent travel or action, inability to cancel a running trip's reserved signal, strict idempotency/revision checking, and orphan-reservation rollback.
- Manual `TimeEngine` and autonomous `LivingWorldEngine` both process travel completion and player interrupts. Autonomous routine actions are suppressed for currently traveling NPCs.
- No story data, user characters or root narrative files were touched. No internet is required by the engine.

## Verification

`cd simulation && python -m pytest -q` -> **153 passed** locally: 134 baseline tests and 19 Phase 01-F tests. `python -m compileall -q src tests scenarios` passed.

`PYTHONPATH=src python scenarios/test_village/demo_movement.py` produced a reproducible movement interruption at time 40, arrival at time 90, and a local observation changing from `[basim,nora]` at the square to `[guard,nora]` at the bridge.

Tests cover co-location privacy; timed arrivals; multi-hop travel; concurrent movement and busy guards; explicit observation; no player-control hijacking; prevention of orphan schedules; session pause; stale revisions; restart/replay; unchanged legacy tests; deterministic arrivals at the same tick; historical stale sightings; and snapshot validation. **GitHub CI was not run.** The results refer to the locally tested source, and published file content must match its Git blob hashes.

## Limitations and non-goals

- This phase initiates travel only through an explicit trusted movement request, **not an autonomous selection of destinations**.
- Perception is location-wide (all co-located entity IDs): no line of sight, concealment, range, crowds, vision or hearing.
- Travel is recorded at its origin until arrival; intermediate coordinate positions and road encounters are not modeled.
- Observations are historical snapshots, not verified world-truth updates for observers and not automatically converted to semantic NPC beliefs.
- Travel-cancellation and route changes after bootstrap are not implemented.
- Internal capability flags are not user authentication or external API permissions.
- **Schema v6/rules v7** are incompatible with older experimental databases without explicit migration or recreation. Real Carlos game state was not imported.
