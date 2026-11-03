# Phase 01-F — route-based NPC movement and local perception

## Scope delivered

- Immutable, persistent bidirectional route graph (`RouteCreated`) with positive simulated traversal costs.
- Durable `NPCTravelStarted` and scheduled travel completion, which changes location only at the correct logical instant.
- Local, time-stamped `NPCObserved` snapshots and automatic arrival observations; only co-located entity IDs are visible.
- Travel/session/role validation, prevention of concurrent travel or action, inability to cancel a running trip's reserved signal, strict idempotency/revision checking, and orphan-reservation rollback.
- Manual `TimeEngine` and autonomous `LivingWorldEngine` both process travel completion and player interrupts. Autonomous routine actions are suppressed for currently traveling NPCs.
- No story data, user characters or root narrative files were touched. No internet is required by the engine.

## Verification

`cd simulation && python -m pytest -q` -> **153 passed** before review and **160 passed** after review locally: 134 baseline tests and 19 Phase 01-F tests. `python -m compileall -q src tests scenarios` passed.

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

## Post-implementation review — 2026-11-03

**Reviewed and fixed three related in-transit consistency flaws:**

1. **False local presence:** travel preserves the origin in `Entity.location_id` until scheduled arrival, but the observation function counted a traveling NPC as physically present at that origin. `_visible` now excludes NPCs with active `traveling` status from local occupant snapshots. Historical observations are intentionally left unchanged.
2. **Impossible local messages:** a traveling sender or recipient could be considered co-located at the stored origin and create `NPCInformationDelivered`. Local delivery now refuses either party when in transit. Valid delivery after arrival is still allowed. This addresses only local delivery; remote correspondence is outside this prototype.
3. **In-transit decisions:** `NPCService.decide` could choose another action while the NPC was traveling. Both `choose_action` and the event reducer now refuse new decisions for travelers (and also prevent activity decisions while another action is running). Decision making resumes upon arrival.

Seven regression tests cover local visibility during travel, sender/recipient delivery refusal, successful destination delivery, suppression of ordinary and trusted-low-level decision attempts during travel, and normal decisions after arrival. **160/160 local tests passed** (153 previous + seven new); Python compilation and the travel demo succeeded. Exact published blob SHAs match the three locally tested modified Python files. GitHub CI was not run. No files outside `simulation/` or any Carlos narrative state were changed.

**Review disposition:** Phase 01-F can be closed within this test-world scope. Perception remains a co-location snapshot, not line of sight, sound, route encounters or automatic pathfinding.
