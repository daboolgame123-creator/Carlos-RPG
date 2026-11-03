# Phase 01-G — Knowledge-limited autonomous route planning

## Implementation

- Per-NPC immutable, event-sourced navigation state: learned routes, visited places and an optional remembered destination.
- Local surveying reveals only routes whose endpoint touches the NPC's present location; no remote map knowledge.
- Opt-in autonomous exploration when explore >= 50, fatigue < 70 and hunger < 75. Only reachable, unvisited, *known* endpoints are considered. Candidates rank by minimum known travel duration then destination ID.
- An explicitly selected destination must already be known and reachable. Weighted Dijkstra computes the cheapest route over the NPC's learned graph only.
- `LivingWorldEngine(..., navigation_enabled=True)` surveys, plans and initiates real scheduled travel within the same atomic time command. Existing activity decisions recorded manually have priority over automatic navigation. When navigation is disabled, previous behaviors remain unchanged.
- No wall-clock updates, unauthorized player movement, teleportation or omniscient information. Current travel, arrival, interruption and replay guarantees are reused.

## Verification

Local `python -m pytest -q` from `simulation/`: **186 passed** (160 previous + 26 navigation tests). `python -m compileall -q src tests scenarios` passed. A two-person isolated navigation demo completed: at simulation time 180, explorer Nora had visited home, forest, crossroads and tower and learned their adjacent roads; nonexplorer Basim stayed at home and completed routine activities.

Tests cover incident-road knowledge, unknown-destination rejection, shortest path, fatigue/interest limits, knowledge isolation, interrupts, restart/replay, event budget atomicity, actor forgery, paused-world behavior, optimistic revision, manually recorded decisions, and busy-state restrictions. The GitHub test file contains 26 navigation test cases. **No GitHub-hosted CI run** has been performed.

## Scope limits

- No road incidents, danger, weather, traffic, moving road positions or path closures.
- Destination choice is a **simple exploratory frontier policy**. It is not a general economic/social planner. A known destination can also be assigned explicitly through a trusted local call.
- An adjacent route represents locally observable road topology in the test world, not knowledge of remote secrets.
- No automatic rumor/map sharing. No network-facing authentication; trusted capability flags are internal-only.
- New schema version **7**, rules version **8**. Prior experimental databases need explicit migration or recreation; no real Carlos/Harthn state was imported.
- All changes are confined to `simulation/`. Do not merge this phase to `main` until reviewed.
