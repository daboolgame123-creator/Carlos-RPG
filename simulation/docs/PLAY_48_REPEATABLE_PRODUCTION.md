# PLAY-48 — Bounded repeatable physical production and real demand boundaries

**Date:** 2026-11-10 UTC  
**Phase status:** `PLAY48_OPEN / RELEASE_NO_GO`. These are **disposable test worlds**, not production-save migration or a self-sufficient village. No engine rules, Schema 42 / Rules 57, `main`, or player story changed.

## Baseline and scope

Branch `feature/play48-repeatable-physical-loops-20261110` starts at verified PLAY-47 integration `1dd038d731c5072edb9eea43d29e5b3e70436d79`. PLAY-47 was technically closed (external review deferred) on `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`. Finite scarcity, including a food shortage and 13/13 hunger-cap residents at day seven, is the historical measured outcome, **not** proof of economic recovery.

PLAY-48's objective is two or more real, authorized, locally traded and physically timed material cycles if finance, labor and demand permit, **without inventing supply, wages, buyers or routes**. Existing `ProductionStarted`, `MarketTradeExecuted`, `ProductionWagePaid` and physical movement reducers remain authoritative.

## Verified scope: 48-A, two independent raw-material loops

[GitHub Actions 42808944705](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42808944705) **SUCCESS** on Python 3.10 and 3.13; exact test SHA `8aa03adc41a6e69f24eea6307aa9141c2bb343fa`. Extended compound test at SHA `8ab782de656f26a87b11eadf24b299467b8b4d57` passed [CI 42809457769](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42809457769), **51 passed and 1 expected skipped** on each Python.

Authentic 6-NPC PLAY-45 physical world; no NPC is moved or told to shop after time-zero initialization. Finite tested inputs and wallets are explicit:

| Initial supply | Saw-board / wood bought | Smelting / ore bought | Built frames | Repaired gear | Total copper |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 wood + 1 ore, 6 copper | 1 | 1 | 1 | 1 | 6 |
| 2 wood + 2 ore, 12 copper | 2 | 2 | 1 | 1 | 12 |
| 0 wood + 0 ore, 12 copper | 0 | 0 | 0 | 0 | 12 |

With two source units, **two separately scheduled real lumber/carpentry cycles and two actual ore/forge cycles** occur. Two site-paid wages per upstream workshop are backed by physical receipts. Finite downstream builder and repair demand only consumes **one** plank and one fitting: remaining plank/fitting stay in the real workshop site inventory; frame and repaired gear remain at their actual sites. This is an honest **demand ceiling**, not a scheduler failure.

Adversarial guards: zero starting worker cash in (0/0), (0/2), (2/0) configurations forbids corresponding production, even if supplier stock is positive; no free credit. Replaying the final high-level clock command raises DuplicateCommand and does not add a receipt. Full SQLite `verify`, `snapshot`, `integrity_check` and `foreign_key_check` pass; source materials conserved against all started jobs.

## Verified scope: 48-B, real compound ore + charcoal

Initial **2 ore + 2 charcoal + 8 copper** across an autonomous 5-actor professional world. The blacksmith makes four personally routed, local purchases (ore twice and charcoal twice) and finishes **two distinct compound smelts**. Each job debits 1 ore + 1 charcoal atomically and uses the one real anvil, with correct per-input receipts. One finished fitting is locally purchased and repaired at the actual repair shop; one remains unsold at the forge. The real two-copper fitting sale funds **two separate one-copper wages**, leaving zero in the forge till; there is no duplicated receipt or unfunded salary. No direct NPC commands after genesis.

Result: [GitHub Actions 42809457769](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42809457769), Python 3.10 + 3.13, **SUCCESS**; 51 tests passed, 1 deliberately skipped (external predecessor fixture) on each. An initial experimental assertion wrongly assumed that one sale can fund only one wage; the actual two-copper proceeds legitimately funded two wages. [Failed probe 42809272354](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42809272354) was corrected by checking both source and destination copper receipts, not weakening the ledger.

## Third strand: 48-C, real 96h systemic blocker

A separate negative-control test `test_play48_post72_blockers.py` runs the *actual PLAY-47 13-resident* world to 96 simulated hours, daily SQLite close/reopen/full-replay, with only documented 2+2+2 bounded units of rain. It compares days three and four, courier health, deliveries, food stocks, sales, wages, job output, and copper conservation. **Verified green:** [GitHub Actions run 42808714301](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42808714301), both Python 3.10 and 3.13, one test passed on each at exact SHA `20170febecc72657293c9fd8b4f3e9ef4e0fa119`. At both 72h and 96h the two couriers are at hunger 100, with zero added deliveries, trades, finished jobs or wages. Five loaves remain in the market while copper stays at twelve. **No autonomous post-72h recovery has been demonstrated.**

Even a green negative-control run would not be a fix. PLAY-47 already demonstrated that hunger and lack of locally owned affordable food halt couriers despite unsold food; reserved consignment copper cannot be used as an NPC wallet. A valid next **gameplay implementation** needs a documented, funded and uniquely receipted food-access/transport contract and/or a genuine locally backed construction/repair buyer. It cannot inject food at t>0, let the courier spend entrusted copper or create free sales merely to show activity.

## Verified scope: 48-D, two genuine downstream customers and scheduled demand

A separate 8-NPC scenario `test_play48_funded_downstream.py` initializes two distinct buyer-owned construction sites and two distinct repair sites with exactly two finite wood/ore units and **twelve known copper units**. The extra construction/repair crews have actual site recipes, physical tools, roads, opening wallets, and independently observed shifts; no NPC is moved or told to purchase after trusted time-zero initialization.

A simultaneous 250-second second-worker shift is a **negative control**: the second workers arrive while the first units are sold, acquire no stock, return and cannot rely on remote stock changes. Merely giving them money and demand **does not** grant market omniscience.

With the later second-worker shift at 520 simulated seconds and the unchanged original 250-second first shift, the world completes **two independent frame-construction jobs and two independent repair jobs**, in four distinct sites, after **eight actually paid and physically reached trades**: 2 wood, 2 ore, 2 plank and 2 iron fittings. Both buyers' own wallets decrease by two copper; all producer and buyer site resources balance, while total copper remains twelve. The frames are **physical site outputs, not complete houses**. Zero-cash buyers make no downstream purchases or jobs; a one-unit source cannot fill the second set of orders. Separate single-versus-segmented 6,500-second advances produce identical full states apart from the extra explicit clock revisions, and both pass SQLite reopening and genesis replay.

- [Acceptance run 42812662593](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42812662593) **SUCCESS**, Python 3.10/3.13, 55 pass + one intentional old-save skip per version.
- [Stronger receipt test 42813027213](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42813027213) **SUCCESS**, both versions, actual wallet debits and four physical customer round trips.
- [Clock partition parity 42813190428](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42813190428) **SUCCESS**, both versions.

This is a time-zero **real demand scheduling** solution in a finite disposable world, not a 96-hour hunger recovery or new universal demand-planning AI. Neither producer nor buyer can know future market stock without a real physical visit. No engine rule or persisted data format is changed.

## Verified scope: 48-E, locally paid food aid without a new event type

A separate small genuine PLAY-27 world proves a feasible **existing event-ledger route** to help a stranded hungry courier:

1. At market, actual NPC Omar spends **2 of his 4 real opening copper** to purchase one actual site-owned loaf from a co-present merchant. This transfers loaf ownership to Omar and pays the site.
2. The authorized survival coordinator raises Huda's actual hunger to **100**, and `audit_courier` confirms **no eligible courier action** at the hunger threshold, without starting the supply planner.
3. Under an explicitly operator-directed local trial, Omar carries his personally bought loaf along **three scheduled, adjacent physical road legs** to the well, consuming 150 in-world seconds. It is never teleported.
4. Huda makes an authorized `AssistanceRequested`; Omar accepts and physically hands over one loaf through existing `AssistanceFulfilled` receipts. Duplicate fulfilment fails closed. Site-owned market food is never reassigned without an actual purchase.
5. Huda eats **her own** loaf through `NPCFoodConsumed`, lowering genuine hunger from 100 to 75. The **existing** autonomous supply coordinator then records **one real delivery**. Original resource and food conservation audits pass; total copper remains twelve; no courier personal wallet is fabricated.

[Final executable targeted acceptance 42814104944](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42814104944) **SUCCESS**, 57 tests passed and one intentionally skipped per Python 3.10 and 3.13, exact SHA `54270a4dccb7203c9ed586cabe2ac9ad8127310f`.

**Crucial distinction:** purchase, 3-leg transport and assistance were **explicitly initiated by a trusted test driver**, unlike production loops in 48-A/B/D. This is a reducer/custody feasibility proof, **not** an autonomous relief policy, market salary, or 96h economic recovery. Any future autonomous support must decide **who volunteers/pays**, use personally known routes and real local inventories, honor courier consignment exclusions and prevent repetitive out-of-thin-air contracts. An employer-funded recurring compensation rule needs its own explicit contract and tests; no new event type or Schema/Rules change is approved here.

## Remaining gates before PLAY-48 technical closure

1. The real 96h run is green as an **unrecovered negative control**, not a recovery; retain its fixed causal findings (five unsold loaves, starving couriers, zero new receipts on day four).
2. Two full **frame-and-repair** iterations now pass in an 8-NPC bounded world with distinct, funded customer work orders; terminal frames/gear remain tangible site assets, **not completed houses**. The general NPC market demand/need lifecycle beyond these contracted projects remains open.
3. The manually instructed local food assistance successfully restores **one physically delivered courier leg** in a smaller world; it does **not** count as autonomous day-four recovery. That claim still needs a real post-72h delivery plus attributable later work, sale or meal in the 13-person world against the unrecovered control, with a funded human-compatible purchase/delivery policy.
4. Run targeted + full historical suites, including authentic old-world refusal, replay, aliasing and 7-day endurance as relevant, Python 3.10 + 3.13 on final exact HEAD. Follow branch's work queue, review and protection gates.
5. External independent review, real Windows/power-loss production saves and `P0_PRODUCTION_NOT_APPROVED` remain separate release restrictions. No auto merge into `main`.

**Decision now:** 48-A/B bounded physical-production evidence verified on earlier exact SHAs; **whole PLAY-48 remains OPEN** and no sustained seven-day or P0 approval is claimed.
