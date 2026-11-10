# PLAY-48F — Autonomous, personally funded one-loaf aid relay

**Date:** 2026-11-10  
**Branch:** `feature/play48-autonomous-funded-aid-20261110`  
**Base:** reviewed, full-suite-green PLAY-48 evidence `3329d11eb19224f471492bf5ef121ffb0837916e`, [full CI 42814550949](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42814550949) **SUCCESS** for Python 3.10 and 3.13. This feature branch is an *independent, disposable* continuation, not an edit to the parent PR #69, `main` or production saves.

**Phase:** `PLAY48F_TARGETED_ACCEPTED / PLAY48_RELEASE_NO_GO`. Schema 42 and Rules 57 unchanged. No new persisted event type, save migration, balances, magic food or debt. Enabling this feature explicitly alters test-world NPC decision-making, never the historical default.

## Real-world policy, opt-in only

`LivingWorldEngine(..., aid_relay_enabled=True)` requires explicit boolean and the existing assistance, food-consumption, survival, navigation and economy capabilities. Default `False` leaves the historical two-pass same-tick assistance response and up-to-three-loaf request behavior unchanged.

**Consent and authority.** A hungry NPC requests **one existing unit of food**, using `AssistanceRequested`, from a currently co-present NPC. The record durably identifies the requester, provider, resource, original physical location, quantity and creation time. The provider alone decides whether to help: it must be free, safe, not critically hungry (hunger ≤60, fatigue ≤69), not a courier carrying consignments, not the on-duty local market steward and have nonnegative directed trust in the requester. An already promised personal loaf cannot be pledged again. Merely being named by a request is not consent: the original `AssistanceResponded` event records the provider's subsequent decision and `AssistanceFulfilled` records actual physical delivery.

**Knowledge and finance.** Provider only knows marketplaces previously recorded in **their own** `navigation.visited`, and travels over **their own** `navigation.known_routes`. No remote live-stock or price query is allowed. It can venture to an already visited market with its **own initialized, unreserved** copper; on arrival it personally inspects real posted offers and present sellers. It voluntarily spends at most **two copper** for one actual loaf. Uninitialized money, unsuitable owner ledger, unaffordable/overpriced quote, absent market visit, missing known road, stale/stolen cargo and future products cause refusal or no action, never free replenishment.

**Timed movement.** The same already implemented `ScheduledEventCreated` / `NPCTravelStarted` reducer authorizes every adjacent leg. A donor returns along personally learned routes to the request's **recorded original location**, not to a teleported remote NPC. Once back in the recipient's real physical presence, donor accepts; later the existing single-use assistance commitment transfers owned food atomically. The recipient can eat through `NPCFoodConsumed` and the existing physical courier can resume normal deliveries. No task changes player agency, legal title, NPC hidden beliefs, job wages, lender ownership or service authentication.

**Resource bounds and attempt behavior.** The aid donor will spend no more than 2 *personally owned* copper per loaf. The unfulfilled market hunt is bounded to 1,800 logical seconds. An expired buyer away from the requester can return on known roads and let the ordinary assistance response decline. Two duplicate helper commands never produce a second meal, trade or transfer. A provider lacking a learned route never guesses a way to the market. The opt-in flag reduces *requested* quantity to one; the default remains 3.

## Actual verifiable evidence

### Positive test — real autonomous loop

The authenticated `test_play48_autonomous_funded_aid.py` builds the original PLAY-27 7-NPC finite physical village with **3 genuine opening market loaves** and an **unchanged total 12 copper**. Omar first visits and personally surveys **market → bakery → farm → well** through historical, timed NPCMovementService actions, recording genuine firsthand knowledge; this is deliberate *prior history*, **not** test driver navigation after help is requested. A real survival coordinator later ages Huda to hunger=100 while Omar remains healthy.

From the moment help is requested, the test supplies **only clock advancement**. It does **not** move Omar, buy bread, request or accept contracts, hand over bread, feed Huda or manually invoke the courier. The NPC policies produce these facts autonomously:

1. Huda at the well signs `auto-help:huda:3750` for one personally owned loaf.
2. Omar takes **3 learned legs to market**, observes a local quote, buys one actual loaf using owned copper, and takes **3 learned legs back**: **6 genuine travel records, 300 logical travel seconds**.
3. Provider Omar personally accepts the one-loaf request; physical `AssistanceFulfilled` transfers exactly one bought loaf; Huda consumes it.
4. Normal autonomous supply coordination completes **at least one new real delivery**; original `audit_physical_supply`, SQLite snapshots, event replay, integrity and foreign keys pass.
5. Known copper stays 12; there is no courier personal copper slot. Reissuing an accepted clock command raises `DuplicateCommand`, preserving world and historical receipts.

### Adversarial and regression controls

- No matching co-present request → **no guessed rescue**.
- Genuine physical donor arrival without personally surveyed/recorded routes → **no remote market selection**.
- Missing initialized personal money despite market or player holdings → **no imagined wallet**.
- Absent local offer, or one posted with price **3 copper** → **no purchase**; first-hand quote at 2 copper may be accepted and paid once.
- Existing personal loaf already promised to Layla in an actual `AssistanceRequested` → `AssistanceResponded` sequence → donor cannot also promise it to Huda after a real walk to the well.
- Explicit disabled mode → original three-loaf requests and ordinary immediate decline, with no donor routes/trades.
- Boolean/gating checks reject invalid opt-in configuration; all old assistance, custody and local food tests remain in the targeted matrix.

**Last verified targeted proof before this documentation:** [GitHub Actions 42820201025](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42820201025), `994831632c5bb317f29b10740b8acf1bdba08952`, **Python 3.10: 90 passed; Python 3.13: 90 passed**. This exact commit was the fully tested source before the report; the documentation/workflow commit must be rechecked separately.

## Release boundaries and next gates

This is **one individual, personally funded rescue in a seven-NPC disposable world**, not seven-day self-sufficiency, a sustained wage policy, or an autonomous recovery after day three in the genuine thirteen-NPC PLAY-47 village. That old 96h negative control still shows five unsold market loaves and no post-72h deliveries. In that world, the relevant potential giver may not be co-present with the starving worker or may no longer hold unreserved copper; knowing that the market has food is not enough. Automatically teleporting relief, granting false employer rights or allowing a courier to spend consigned cargo is explicitly forbidden.

Before PLAY-48 technical closure: independently establish a donor's legitimate finance and physically learned supply/contact route in the **same** 13-NPC baseline, demonstrate a **post-72h actual delivery plus attributable later work/sale/meal**, validate against the negative control under identical weather/budgets, pass final exact-SHA targeted/full Python 3.10+3.13, and record review disposition. Production save migrations still require independent P0 approval and explicit owner decision. **Keep all PRs Draft; no merge.**
