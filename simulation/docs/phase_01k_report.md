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

Phase 01-K implementation and preliminary local testing complete;
independent phase review remains pending.
