# Phase 01-K — Autonomous assistance decisions and fulfillment

## Scope implemented

- A deterministic, opt-in autonomous assistance policy for **NPCs only**.
- An NPC whose hunger is >=75 and initialized food <=2 may ask another idle,
  co-located NPC for 1–3 food units. Partner choice uses its own trust toward
  available peers; it **does not read their hidden stock amounts or needs**.
- The provider independently evaluates a typed request using **its own**
  trust, hunger, food balance, minimum reserve (2 units), and previously
  promised stock. It may promise or decline, without changing resources.
- Actual delivery is a later action in a separate logical tick when both
  participants are again available together and the supplier has enough food.
  If inventory is insufficient after an earlier promise, the supplier can
  withdraw the promise locally, with no partial transfer or free trust gain.
- Existing 01-J transition events and immutable audit ledger handle
  conservation, actor authorization, atomic commits, and event replay.
- No one actor performs more than one autonomous aid transition per tick.
  Food requests have a 900-second retry interval; no background progression.

## Verification evidence

The local test suite was run as four separate groups due to earlier time
limits. **310 tests passed**: 134 core tests, 107 movement/navigation/social
regressions, 41 Phase 01-J assistance/review tests, and 28 Phase 01-K tests.
`python -m compileall -q src tests scenarios` passed. The standalone
`demo_assistance_autonomy.py` passed and demonstrated Nora's food `1 → 4`,
Basim's food `10 → 7`, conserved total food `11`, and Nora's directional trust
change `+5` only on physical delivery. Replay verification matched the
committed state. The new test suite includes decision privacy, refusal,
existing-promise accounting, competing requests, travel and busy-state guards,
manual decisions, offline pause, deterministic replay, split/single step
agreement, resource conservation and event-budget rollback.

Tests were executed locally; no GitHub CI result is asserted. Exact Git blob
SHA checks confirmed that the published source, complete 28-test suite and
standalone demonstration match the locally executed files. Documentation
may be rendered or formatted differently between the local ZIP and GitHub.

## Limits and compatibility

- Social `offer_help` words do not automatically create inventory-backed
  commitments. Autonomous requests are typed because food shortage is
  explicitly modeled, not inferred from arbitrary dialogue.
- No NPC-generated water requests until a thirst model exists. Physical
  delivery is still instantaneous once parties are co-located and free;
  a carrying/interaction duration is deferred. Hunger does not decrease
  merely because a recipient now *owns* food: consuming food is a separate act.
- A forgotten/uninitialized provider inventory is excluded as a *schema
  eligibility* check; the requester does not learn its numerical stock.
- Remote or traveling aid is not supported, and promises cannot be cancelled
  remotely without a modeled messaging channel.
- Authentication flags are internal local capabilities, not a secure public
  API. Existing schema **9** and rules **12** are unchanged because no event
  format or reducer rule changes occurred. This prototype does not import
  or modify the current canonical Carlos RPG narrative.

## Status

Phase 01-K implementation and independent prototype review completed;
ready for closure within the documented experimental scope.


## Post-implementation review — 2026-11-04

**Two confirmed defects were reproduced before the fix and covered by three new tests:**

1. **Obligation order depended on request ID instead of age.** Both provider response and fulfillment loops sorted promise IDs lexicographically; a newer `a-sara-second` request could overtake an older `z-nora-first` commitment and consume stock needed for that earlier promise. Both phases now sort eligible obligations by `(created_at, request_id)`, preserving stable earliest-first priority.
2. **Long valid NPC identifiers could block world advancement.** Automatically generated request identifiers could exceed the event ledger's 128-character limit. The planner now uses a deterministic SHA-256-based request identifier when the readable identifier would be too long; the needy NPC still gets to request aid and the engine does not fail.

**Regression evidence:** the three review tests failed before correction and passed afterward. The full local suite passed **313 tests** in four groups: **134 core + 107 movement/social + 41 assistance/review + 31 assistance-autonomy/review**. `python -m compileall -q src tests scenarios` passed, as did the autonomous village demonstration, with 11 food units conserved, and full event replay matching the saved state.

**Compatibility:** database schema **9** and rules **12** remain unchanged; only the pure, opt-in autonomous decision policy has changed, not the event contract. Existing event histories still replay as recorded. The branch is not merged into `main`, Carlos narrative files are untouched, and GitHub-hosted CI has not run.

**Remaining model limits:** pending obligations can remain open indefinitely when parties do not reunite, since remote messaging and expiry do not exist yet. Actual help still requires proximity, and food ownership does not by itself reduce hunger.
