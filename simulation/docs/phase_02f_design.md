# Phase 02-F — Homes, work locations, daily routine, and interruption policy

**Status:** DESIGN COMPLETE / IMPLEMENTATION NOT STARTED / NOT APPROVED  
**Date:** 2026-11-05  
**Base:** `simulation-engine-phase-02e` after green CI [42095487418](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42095487418). External review remains deferred and the production backup/restore P0 gate remains OPEN. Work only with disposable worlds.

## Player-facing intent

Seven NPCs can have distinct assigned homes/workplaces and daily windows. A worker travels physically to the workplace on learned roads, works there during the appropriate shift, and may return home afterward. Characters without an assigned schedule retain all 02-E behavior. Need/survival and direct events can override a normal plan; nothing teleports or forces a character to finish every workday. A missed shift is a genuine possible outcome, not an engine failure.

## Scope and invariants

1. **Explicit trusted setup only:** an optional per-NPC routine profile is assigned at time zero to an existing NPC, referring only to existing places. A home location and optional workplace must be real. Configuring a profession or an address does not transfer ownership, wages, keys, goods or legal occupancy.
2. **Clock and time:** fixed integer in-world day of 86,400 simulated seconds; windows expressed as seconds from day start. No wall-clock scheduling or advancement while the player session is closed. A shift never changes world time by itself.
3. **Known routes only:** the NPC must use an existing learned path and the real `NPCTravelStarted`/scheduled completion semantics. Having a home address does *not* grant secret map knowledge, disclose remote hazards, or authorize remote inventory reads. If no known path exists the NPC stays and may discover adjacent roads using existing local surveying.
4. **No forced displacement of activity:** an NPC cannot start routine travel while traveling, producing, or already performing an action. Existing player-commanded/explicit navigation target takes precedence unless a future validated cancellation policy allows a change. Do not cancel scheduled work or travel silently.
5. **Survival beats convenience:** critical hunger and urgent safety are evaluated before voluntary work commuting. A routine must not override existing foraging, food navigation, or consumption where those have higher justified survival priority. Temperament/needs can cause deviations, but only based on that NPC's allowed information.
6. **Routine must avoid loops:** deterministic choice with stable ties, cooldown and bounded events; at an endpoint no repeated travel or redundant state events. A missed shift may trigger homeward travel without endless shuttle cycles.
7. **Compatibility:** guard the new behavior behind an opt-in feature and optional profile; baseline 02-E worlds with no routines must maintain exact event/decision parity apart from an explicitly documented version increment. No silent migration of older schema/rules.
8. **Atomicity and trust:** bootstrap profile and any new operational events must be validated by reducer and persisted by the event store with explicit authorized provenance. A text instruction, narrator claim, or forged schedule may not set an NPC's residence or move an NPC.
9. **No global director:** occupations and routine assignments do not give knowledge of other NPCs' plans. NPC schedules need not be chosen for the purpose of encountering Carlos.

## Suggested narrow implementation (to be reviewed before code)

- Store a validated `npc_routines` map separate from the NPC's dynamic needs and its 02-E autobiographical memory, with `home_id`, optional `workplace_id`, `work_start`, `work_end`, and an optional local routine state only if strictly required by deterministic replay.
- Introduce a strictly validated, time-zero-only `NPCRoutineConfigured` event for an existing NPC.
- Introduce a pure `choose_routine_intent(state, npc_id)` module, returning `commute_work`, `commute_home`, `at_work`, `at_home`, or `defer`, with reason and route. Use `shortest_known_route` and existing movement events for each actual leg.
- Integrate the routine choice into LivingWorld's current explicit decision order without overriding pending actions, local urgent survival or manually selected destinations. Work/rest actions reuse the existing physical action completion path; no wages, house occupation exclusivity, job contract or employment guarantee is invented.
- The full routine (which may span days) is executed only when time is explicitly advanced; no asynchronous tick.
- Do **not** add mid-flight cancellation in this phase unless an independent policy and replay test prove it safe. An emergency can change the *next* decision, or use an existing explicitly interrupting scheduled signal, but must not erase unfinished actions.

## Acceptance tests — all required for technical validation

1. Home/work at known places; 2–3 connected roads; actual travel durations and arrivals; work only at location when due.
2. Seven NPCs with different windows; at least one without configured routine; unconfigured one shows exact 02-E events and scoring.
3. No known road to a workplace: remain in place, neither teleport nor discover a remote route.
4. Time partition invariance: a continuous advance versus equivalent split advances yields the same meaningful state and physical outcomes after normalized command IDs, under the same enabled features.
5. A running job or producing NPC is not moved or interrupted merely because the shift begins.
6. Critical hunger or explicit hazard changes the *next eligible* choice and never triggers unauthorized cancellation, instant arrival or food fabrication.
7. Time window boundaries: just before, exactly at start/end, overnight/day rollover; no double work from one tick.
8. Invalid bootstrap: unknown NPC/home/workplace, malformed schedule, bool-as-int, duplicate configuration and late configuration are rejected atomically.
9. Save/snapshot/restore/replay preserve routine and travel with exact authorized events, including process restart before arrival.
10. Repeated command/forged travel/scheduled event fails closed; budget failure rolls back the entire high-level command.
11. Frozen full predecessor 02-E reference is run with feature OFF; compare event and semantic state digests excluding solely documented version fields.
12. CI green at the **final code SHA** on both Python 3.10 and 3.13; independent review separately remains required for APPROVED/CLOSED.

## Deferred explicitly

- Employment contracts, wage payment, jobs marketplace, property/land titles, tenancy/eviction, family households and sleep quality.
- Autonomous reassignment of home or job, long-term preference learning, career advancement.
- Emergency cancellation/refund of already-running economic commitments without an audited cancellation and compensation model.
- Political orders, curfews, law enforcement, crime, reputation effects, or dialogue-generated residential changes.

## Gate

Only mark **TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED** after real implementation and all tests pass. Never mark APPROVED/CLOSED without independent sign-off. P0 remains OPEN; do not merge into `main`, rewrite original Carlos story records, or certify a durable production world.
