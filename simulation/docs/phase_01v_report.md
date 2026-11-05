# Phase 01-V — Scarcity and failure response: technical validation

**Status:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_PENDING — NOT APPROVED / CLOSED.
**Branch:** `simulation-engine-phase-01v` forked from 01-U checkpoint `47dd04ef6928af6c6b76fecdd1b29dc46a653755`.
**Tested code commit:** `0e70d4d3163b7336ad784848096e65f7edee2576`.
**CI:** [41989436509](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/41989436509) = **587/587 passed** per Python 3.10 and Python 3.13, genuine frozen 01-U default-off parity and older 01-T/01-S/01-R compatibility checks green.
**Schema / Rules:** 13 / 18, unchanged; no migration or event schema change. P0 backup/restore remains **OPEN**.

## What was implemented

- Opt-in `LivingWorldEngine(scarcity_enabled=True)`, disabled by default, requiring food-navigation and assistance flags (hence navigation, knowledge and foraging) explicitly. All previous modes remain intact with the new flag off.
- New `scarcity.py` provides pure policies based on an actor's **own logged experiences**. Constants `FAILED_SITE_RETRY_SECONDS=3600` and `REFUSED_PROVIDER_RETRY_SECONDS=3600` use logical time, not wall-clock or narration.
- With scarcity enabled, `choose_food_route` temporarily excludes a site where **that same NPC** had a `depleted` actual foraging outcome during the last 3600 seconds. A later hearsay claim cannot immediately overturn a personal failure. A newer *verified local observation* permits reconsideration; the guard expires exactly at the boundary.
- Other positively believed food destinations still compete using the actor's own known routes, weighted travel time and belief confidence; no global resource scan, secret inventory inspection, invented path, or teleportation.
- `choose_assistance_intent` avoids a provider who **refused** this requester's previous food request or **locally withdrew a promise**, within 3600 seconds of the logged refusal/withdrawal. It retains the predecessor's independent, global **900-second** minimum re-request period. A requester's own cancellation does not count as a provider refusal.
- No assistance request fabricates food or a promise. Actual `AssistanceFulfilled` is the only path of resource transfer and remains subject to prior conservation, co-location, capability, event-time, and replay validation.

## Verification

- **23 new parametrized test cases** over predecessor 564 → **587 tests**, passing in Python 3.10 and 3.13 on CI. Verified false rumours, exhausted supply, another actor's private failures, temporary exclusion of a recently depleted location, fallback to a different known route, exact 3600-second expiry and witnessed direct observation override.
- Verified declined versus withdrawn promises, requester's own withdrawal, another requester's private rejection, exact 900-second global re-request delay, exact 3600-second refusal expiry and a fully unavailable alternative yielding **no** new request or resource creation.
- **Real physical finite transfer:** a declined request to Basim is followed by a legal request to a different, sufficiently stocked provider. Transfer changes `nora.food` 1→4 and `zara.food` 10→7, preserving total food 11; the first refusal stays recorded. `verify()` reconstructs the resulting world.
- **Actual seven-NPC forage failure:** two of four contenders collect one unit each; two produce durable `depleted` records with zero quantity. `verify()` reconstructs the correct exhausted local source and conserved food.
- SQLite snapshot, close/reopen, duplicate command refusal, full event replay and budget-exhaustion all pass; rejected batches leave no world or event-log mutations.
- CI freezes the **actual 01-U** parent at `47dd04ef6928af6c6b76fecdd1b29dc46a653755` and runs the same knowledge+food-navigation+assistance-active fixture on each runtime **with 01-V flag off**. Both interpreters compare `events_digest`, `state_digest`, NPC count, revision, time, events count and replay for exact equality. Prior 01-R/01-S/01-T baselines stay frozen and pass.

## Remaining gates and limitations

- This is an implementation-assistant review, **not an independent APPROVED sign-off**. Phases 01-T and 01-U are also pending external review. If a separate reviewer finds a blocker in either predecessor, reassess 01-V and its tests and mark its dependency at risk until corrected.
- The personal-depletion suppression window is an **experimental planning policy**, not a permanent fact or global depletion ledger. False rumours can become actionable after the bounded penalty expires; a later verified direct observation takes priority.
- The existing assistance policy checks that a potential provider has a *registered initialized* food field; it does not reveal the provider's secret food quantity to choose whom to ask. Availability and trust ranking follow their earlier 01-U/01-K rules.
- The engine does not yet model weather, harvests, commerce, resource regrowth, political decisions, medical effects, or full risk-aware travel. Failures are possible and are not automatically solved by invented resource sources.
- **P0 OPEN:** synthetic disposable test worlds only, no automated migration or certification of durable long-lived saves; no main/story changes, no automatic PR merge, no 01-W implementation.

**Provisional verdict:** technically validated with green final code CI; **EXTERNAL_REVIEW_PENDING** until a separate read-only reviewer provides a verifiable verdict on this exact phase.
