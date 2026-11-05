# Phase 01-V — Provisional design: scarcity, failed attempts, and alternate response

**Status: TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED — NOT APPROVED/CLOSED (corrected branch).**
**Branch:** `simulation-engine-phase-01v`, forked from technically tested but not independently approved 01-U checkpoint `47dd04ef6928af6c6b76fecdd1b29dc46a653755`.
**Predecessors:** 01-T and 01-U = `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING`. New work may need revision if OpenCode reports a blocker.
**Baseline:** Schema 13 / Rules 18; 564/564 green on both Python 3.10 and 3.13, [01-U final CI](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41931491155). **P0 save/restore remains OPEN**. Disposable test worlds only.
**Change type:** bounded opt-in deterministic planning policy, no new DomainEvent, persisted field, Schema/Rules upgrade, migration or remote visibility.

## Scope and causality

Scarcity is consequential: an NPC who **personally failed** to collect food at an exhausted local site should not immediately believe the next unverified positive rumor about that same place; a hungry requester who was **explicitly refused** food should choose a different physically present provider at the next legal request time. Neither case grants resources, alters somebody else's memories, or creates a new right to food.

### A. Prior personal forage failure (not all-world knowledge)

- Opt-in `scarcity_enabled=False` on LivingWorldEngine. When enabled it requires the existing food-route stack (`food_navigation_enabled`, `navigation_enabled`, `knowledge_enabled`, `foraging_enabled`) plus `assistance_enabled`; do not activate anything implicitly.
- `choose_food_route(..., scarcity_enabled=True)` filters **only this NPC's own** `foraging_attempts` records for `outcome='depleted'` at the proposed site, within a named **3,600 logical-second** retry window.
- A later `food:present` **hearsay** cannot instantly undo that personal failure, even if it has a later alleged observation time. Directly verified local `observation:site` after the failure permits reconsideration; after 3,600 seconds, a new positive belief can be reconsidered. The older food-state belief contract is unchanged; no irreversible blacklisting.
- Continue selecting among other positive-belief sites reachable through **personally learned roads**; use exactly the same known-time/confidence/site tie-breaking as 01-U. Local forage, explicit manual targets and completed tasks keep existing priority.
- Do not inspect peer forage histories, remote resource balances, hidden roads, or use event-log queries as a planner oracle. For uninitialized food, unknown remains unknown. At arrival, 01-T observation and 01-S real forage rules remain authoritative.

### B. Refused assistance and provider choice

- `choose_assistance_intent(..., scarcity_enabled=True)` preserves its **existing global 900-second minimum re-request interval**, physical co-location/availability, hunger/food eligibility, inventory initialization, and request/response/fulfilment contracts.
- When choosing a provider, skip only providers in this NPC's own persisted `obligations` for `resource=food` with a **declined** response or a provider's communicated `promise_withdrawn` cancellation within the last **3,600 logical seconds** (based on the persisted `resolved_at` timestamp).
- The requester's own withdrawal does not count as a provider refusal; a stale refusal eventually expires. A character may still voluntarily request help manually from anyone under existing service rules; this policy changes only autonomous preference.
- Never read a provider's **private food quantity** to rank providers; the existing check that an inventory field is initialized is retained as a schema eligibility guard (this existing limitation is explicitly documented). Do not fabricate trust changes when a request is refused; no resource is transferred until a genuine `AssistanceFulfilled` event.

## Required tests / trust boundaries

1. Two positively believed known sites, one personal failed forage → the alternate is chosen even when the failed site has a shorter known route; absent own failure or after timeout, the original cost order is restored.
2. Failure by a different NPC must not affect the chooser; a **newer direct personal observation** can invalidate the refusal to revisit, whereas an unverified rumor alone cannot.
3. Refused provider is skipped after the **existing** 900-second global wait; another co-located, eligible provider may be requested. No provider → no new request; after the new 3,600-second window a provider is eligible again. A cancelled request by the requester doesn't count.
4. No leak of peer needs, remote resource truth, false factual guarantees, or hidden routes.
5. Genuine events: simultaneous foraging and depletion record no duplicate food; refused help moves no food; reports/decisions persist across SQLite close/reopen and replay.
6. Closed session, stale revision, event-budget exhaustion and idempotent command have no partial durable effects.
7. CI on Python 3.10 and 3.13; **compare the 01-V runtime with the frozen actual 01-U runtime** with all existing flags enabled and only new flag disabled, asserting identical event and state digests.

## Acceptance and handoff

- Phase 01-V may become **TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING** only after all regression checks on the final SHA, full design/report and a distinct review request. No self-review counts as external approval.
- Never merge review-only PRs, change `main` or original Carlos story files, import user worlds, silently upgrade 13/18 saves or claim P0 completed.
- If the separate OpenCode reviews of 01-T / 01-U find a blocker, mark 01-V as **dependency at risk** and reconcile before any formal closure or long-lived world.

**Implementation evidence (2026-11-05):** [01-V report](phase_01v_report.md) and [independent review request](phase_01v_independent_review_request.md); tested code `0e70d4d3163b7336ad784848096e65f7edee2576`; [CI 41989436509](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41989436509) 587/587 on each Python interpreter, with frozen 01-U parity. No external sign-off yet.

## 01-V amended implementation record (2026-11-05)

- Corrected branch: simulation-engine-phase-01v-review-fix. Explicitly merges corrected 01-U, including corrected 01-T source, without changing original reviewed branches.
- Inherited fixes: one recipient/site food-sharing delivery per round; no same-tick hearsay relay; safe bounded history ID parsing; U-3 decision cooldown for both food and fallback travel while food-navigation mode is on.
- [CI 42013057857](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42013057857): 593/593 on Python 3.10 and 3.13, including 25-NPC full stack. No schema/rules upgrade; external review postponed by user, not independently approved. P0 OPEN.
