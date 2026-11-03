# Phase 01-G — Knowledge-limited autonomous route planning

## Implementation

- Per-NPC immutable, event-sourced navigation state: learned routes, visited places and an optional remembered destination.
- Local surveying reveals only routes whose endpoint touches the NPC's present location; no remote map knowledge.
- Opt-in autonomous exploration when explore >= 50, fatigue < 70 and hunger < 75. Only reachable, unvisited, *known* endpoints are considered. Candidates rank by minimum known travel duration then destination ID.
- An explicitly selected destination must already be known and reachable. Weighted Dijkstra computes the cheapest route over the NPC's learned graph only.
- `LivingWorldEngine(..., navigation_enabled=True)` surveys, plans and initiates real scheduled travel within the same atomic time command. Existing activity decisions recorded manually have priority over automatic navigation. When navigation is disabled, previous behaviors remain unchanged.
- No wall-clock updates, unauthorized player movement, teleportation or omniscient information. Current travel, arrival, interruption and replay guarantees are reused.

## Verification

Local `python -m pytest -q` from `simulation/`: **186 passed** before review; **188 passed** after review (160 previous + 26 navigation tests). `python -m compileall -q src tests scenarios` passed. A two-person isolated navigation demo completed: at simulation time 180, explorer Nora had visited home, forest, crossroads and tower and learned their adjacent roads; nonexplorer Basim stayed at home and completed routine activities.

Tests cover incident-road knowledge, unknown-destination rejection, shortest path, fatigue/interest limits, knowledge isolation, interrupts, restart/replay, event budget atomicity, actor forgery, paused-world behavior, optimistic revision, manually recorded decisions, and busy-state restrictions. The GitHub test file contains 26 navigation test cases. **No GitHub-hosted CI run** has been performed.

## Scope limits

- No road incidents, danger, weather, traffic, moving road positions or path closures.
- Destination choice is a **simple exploratory frontier policy**. It is not a general economic/social planner. A known destination can also be assigned explicitly through a trusted local call.
- An adjacent route represents locally observable road topology in the test world, not knowledge of remote secrets.
- No automatic rumor/map sharing. No network-facing authentication; trusted capability flags are internal-only.
- New schema version **7**, rules version **8**. Prior experimental databases need explicit migration or recreation; no real Carlos/Harthn state was imported.
- All changes are confined to `simulation/`. Do not merge this phase to `main` until reviewed.

## Post-review correction — knowledge bypass in manual movement

Review identified one concrete integrity flaw: after a navigation profile had been created, a trusted caller could still use the legacy `NPCMovementService.start` or a directly submitted `NPCTravelStarted` event to traverse a road present in the global graph but missing from the NPC's known routes. The automatic navigator was correctly limited, but the shared movement reducer was not.

**Correction:** `project_movement_event` now rejects travel starts over unknown routes whenever the NPC has an initialized navigation profile. Legacy 01-F worlds lacking that profile keep explicit-route travel compatibility. As soon as a new location is surveyed, the newly learned adjacent roads become eligible for travel. The check occurs inside the state projector and thus also applies to low-level event batches.

**Verification:** local `python -m pytest -q`: **188 passed** (186 baseline plus two new regression tests); `python -m compileall -q src tests scenarios`: passed. The two tests cover service-level rejection, atomic rollback, ability to travel after surveying, forged low-level event rejection, and deterministic replay. No hosted CI run. The movement source uploaded to GitHub matches the tested Git blob SHA.

**Compatibility and limitations:** the route knowledge rule is enforced after a navigation profile is initialized. This is not a public authenticated API; trusted local capability flags remain internal. No changes to Carlos story data or `main`. Phase 01-G is eligible for closure within the prototype scope, subject to the existing limitations.
