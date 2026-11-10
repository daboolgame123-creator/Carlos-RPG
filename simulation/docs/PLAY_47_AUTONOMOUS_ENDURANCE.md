# PLAY-47 — NPC economy: multi-day endurance and root-cause measurement

**Status:** see the [gated technical closure decision](PLAY_47_TECHNICAL_CLOSURE_DECISION.md).
The operative decision becomes `CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER`
only after the exact decision commit passes all full/targeted checks and is
fast-forwarded to integration. Until then PLAY-47 remains OPEN / RELEASE NO-GO.
The historical pilots below depend on PLAY-46's technical closure at
`a346d8b5f3fe4b736e420bfa3e470a8afa089313`. No P0 signoff, `main` merge or
durable-save support is implied.

The latest evidence is one real thirteen-resident full-life world through
seven days, in dry and finite-rain conditions, with food/water and ore/fuel/
smith/repair chains. The [evidence report](PLAY_47_CLOSURE_EVIDENCE.md) preserves
verified source/run identities and explicitly separates completed baseline
checks from the final decision candidate's required checks. Finite resource
failure is the measured outcome, with no recovery or self-sufficiency claim.

## Objective

Measure independently acting NPC economies over increasing in-world horizons, distinguishing **valid economic shortage** from **software integrity regression**. Never issue Carlos commands to drive NPC shopping, add free stock or mint copper to make a scenario pass.

This stage *cannot* claim a seven-day sustainable medieval village merely because a one-hour smith chain survives. A 7+ actor joined world integrating hunger, food/water, wood and ore production, local shops, courier routes, bounded resources and cash must be tested independently before full closure.

## Phased implementation and honest evidence gates

1. **47-A — accounting-only pilot (this commit):** read-only `audit_npc_economy()` projection with known-copper amount, explicit unknown ledger owners, stock counts, authentic trade/job/wage receipts, journeys and NPC needs. This is trusted operator-only diagnostics, **never NPC/player omniscience**. No changes to Schema 42 / Rules 57 or events.
2. **47-B — real short-world evidence (this commit):** reuse a verified unscripted PLAY-46 smith→repairer world; observe t=0, 700 and 3600. Require constant six initialized copper coins within the same known ledger scope; no unsourced jobs/trades, correct replay, physical travel. A one-hour test is **not** long-run evidence.
3. **47-C — genuine integrated world:** build a 7–10 NPC shared world (not two disconnected test villages) with food/water, physical hauling, market needs and nonfood workshops. Analyze mode-flag coexistence; `economy_only_enabled=True` disables ordinary survival dynamics, so do not use it as a hunger/endurance proof. Treat unimplemented mechanisms as blockers, not pretend they exist.
4. **47-D — 24h and 72h tests, then 7d where feasible:** checkpoint hunger, inventory, demand, cash distribution, funded/unpaid work, route timing, shortages and breakdown. Use segmented advances bounded by event budget. Treat starvation or bankruptcy due to finite real resources as a valid measured outcome, not a CI failure.
5. **47-E — isolate and repair root causes:** only patch reproducible software failures and misprioritized decisions. For resource infeasibility, document the economic constraint and propose a separate audited supply mechanism; do not inject stock mid-run.
6. **47-F — adversarial and closure:** invalid/unknown financial entries, seller absence, no known road, zero funds, job/wage duplication, real predecessors' save refusal, SQLite replay/snapshot/PRAGMA, time-step partitions and default-off equivalence. Run targeted and full Python 3.10/3.13 CI on **final exact HEAD**. Write decision report.

## Pilot constraints

The pilot provides no general economic solvency, demand model, resource regeneration, institutional investment, employer liquidity guarantees or player UI. The report's `copper_known_total` explicitly excludes owners whose copper ledger has not been initialized; an unchanged value is **not proof** of a complete-world monetary balance when `copper_scope_complete=False`.

## Rollback, trust and tracking

- The audit is read-only: no event/DB writes or new gameplay authority; unknown balances are never silently equated with zero.
- Reusing existing trusted test-world genesis does not authorize migration of PLAY-45 saved worlds to Schema 42.
- Playable Carlos input and untrusted network/API remain isolated; P0 production and external review stay open.
- Last SHA, genuine CI links, actual NPC/economy outcomes, observed bottlenecks and open gates belong in the next report.

## 47-C baseline experiment (separate from compound production)

- Adds a **single real seven-NPC food/water village**, with `economy_only_enabled=False`, enabled survival, paid food purchases, actual farm→bakery→market physical distribution, hunger and bounded cash. Read-only audit checkpoints through **24 hours**, matching event replay and SQLite integrity.
- Independent **zero-water counterfactual** measures no free harvest over six hours. A shortage is not treated as a software failure; the opening three loaves may still be eaten.
- This is an **intermediate baseline**, not the final *joined* NPC world: the compound/professional planner currently requires `economy_only_enabled=True` and its coexistence with full survival needs explicit design and independent testing. **Do not claim 7 NPC full compound-professional autonomy or 72h/7d sustainable survival from this batch.**
- No schema/rules/event changes, no new privileges, no player-visible omniscient diagnostics.

## 47-C.2 — joined full-life professions (candidate; not accepted until CI)

- A **new opt-in engine constructor flag** `professional_full_life_enabled=False` permits the compound multi-profession planner in a world with real `survival_enabled=True` and `consumption_enabled=True`, without enabling the earlier focused `economy_only` mode. It rejects incompatible combinations and leaves old defaults byte-for-byte unchanged.
- In this mode an NPC with hunger ≥75, fatigue ≥70, safety ≥75, or injury needing rest does **not** start a new professional purchase, deposit, material trip, or production job. Ordinary NPC survival/food/rest decisions remain active. No new reducer authority, resource creation, persisted fields, schema/rules bump or player commands.
- The dedicated joined test world starts from the previously verified seven-person physical farm/bakery/market world; adds miner, charcoal burner, smith and repairer (11 NPCs total), real roads, two-material smelting and a repair workshop. **Only existing opening copper is reallocated at trusted time zero**; all 11 personal wallets plus every physical site have an explicitly initialized balance so global accounting is complete. This scenario is for **900 seconds only**, not 24h or 7d survival.
- Acceptance requires actual food trade and independent ore/fuel purchases in the **same WorldState/SQLite database**, smelting, dynamic hunger, consistent 12-coin total, replay/snapshot/PRAGMA, and targeted + full 3.10/3.13 CI. Until evidence exists this is a **candidate**, not a completed merged-life feature.

## 47-C.2 audit finding: staffed shops versus general NPC actions

The first integrated test confirmed the smith *physically reached* the iron mine, the ore/charcoal quotes existed, and miner/burner remained at their stalls, but ordinary full-life `NPCActionStarted(work)` had made the sellers **busy**. The trusted market correctly rejected purchasing from a seller doing an incompatible activity. The correction is **not** to relax `market._present()`: only in `professional_full_life_enabled`, a healthy on-duty shop keeper or production-role worker does not start a conflicting generic NPC task. Hunger ≥75, fatigue ≥70, serious danger or injury permits the full-life survival/rest choices to resume. Prior modes remain unchanged. Confirm by targeted exact-HEAD CI before claiming this behavior fixed.

## 47-C.3 strengthened acceptance candidates

The short 900-second joined-world test was verified by [targeted CI 42647367865](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42647367865): **23/23 on each Python 3.10/3.13**, eleven NPCs, six real local trades (3 food + ore + charcoal + fitting), two completed jobs, one real funded wage and twelve copper conserved with all owners initialized. **This is not a long-term claim.**

Next targeted tests check: (a) a smith beginning at hunger 80 does not depart on procurement or ignore food/rest priority; (b) one clock jump versus segmented time yields identical economic receipts, stock totals and hunger; (c) the same joined world reaches 24h with copper and physical supply conserved, replay/snapshot/integrity checks and measured starvation. These three tests remain **unverified until their exact SHA CI finishes**. A documented famine is valid; creating money or food to make it look healthy is not.

## 47-D — Necessary feasibility diagnostics (pending CI)

In the **real joined 11-NPC genesis**, the PLAY-37 closed-world operator-only mathematics is reused without changing food rules. With ordinary hunger 1 point / 300 seconds, the actual time-zero needs imply **at least 107 meals in 24h** (optimistic physical supply at most **6**, deficit at least **101**) and **at least 360 meals in 72h** (at most **9**, deficit at least **351**). This ignores activity hunger and assumes ideal distribution; neither figure is a forecast of meals actually delivered. The single field's upper output is 3 loaves/day and the single courier 4/day, while the 11-person steady-state lower demand is 127/day; market supply upper ceiling 3/day. A trusted zero-water world retains only 3 initial loaves, with 72h shortfall at least 357. An already-existing slower time-zero physiology (3600s/point) lowers demand to 11/day but leaves the max market output 3/day, deficit at least 8/day; over 72h minimum demand 12 versus 9 theoretical loaves. These are *candidate assertions* pending official CI on this commit. They demonstrate that neither path timing nor a new NPC planner can make the closed village self-sufficient without additional genuine land, water, labor, food delivery and ownership transfers.

## 47-E — Labor-aware capacity envelope (candidate, targeted CI pending)

A purely read-only test-world capacity model counts the **added farmers and couriers as additional hungry residents** rather than treating production/labor as free. Inputs are derived from the actual joined eleven-NPC genesis (Schema 42 / Rules 57). Its output is an optimistic **necessary** steady-state daily bound; it is *not* a predictor of travel success, individual distribution, pre-harvest food timing, wages or authenticated rain. It never writes events or mints stock. Search limits are explicitly bounded, not an unbounded impossibility proof.

At current 300s/point hunger and a 3-loaf/field/day, 4-loaf/courier/day upper capacity, an eight-field/six-courier proposal actually requires **12 additional NPC workers** (11→23). The new demand is **265 meals/day** vs only 24/day ideal delivery; searching up to 64 plots/couriers still finds no adequate throughput pair. The supposedly free workers in the earlier simplistic 4-plots/3-couriers proposal were a material omission.

Under the **already-supported, time-zero 3600s/point** physiology, the smallest bounded *steady-state throughput* pair is **8 real fields and 6 real couriers**, which adds 12 workers: 23 residents need a theoretical minimum **23 meals/day**; field/courier maxima are both 24/day. This is only a necessary throughput arithmetic candidate. Its three-day full-plot use requires **24 physical water units**; the established village starts with only **2**, leaving **22 missing**. With no attested rain the most that could reach the market in three days remains **9 loaves including the three initial ones**. Hypothetical added water is an input to the operator planner and is **never credited to SQLite or an NPC**. No field, courier, work contract or water is added by this study. A viable real-world test needs validated water provenance, land and staff, enough opening stored food, credible worker hours, physical paths and pay, followed by actual replay/clock-partitioned acceptance.

## 47-F — Real joined 72-hour endurance (candidate until CI)

A separate test now advances the **same actual eleven-NPC, fully joined survival+compound-economy world** in twelve genuine six-hour increments out to 72 hours, both with the default 300s/hunger and the already-supported 3600s/hunger calibration. It neither manually drives NPC decisions nor changes the finite initial food, water, tools or copper. Daily observation records the number at hunger 100, market trades, completed jobs, funded wages, exact 12-copper world ledger, and known water; water is never replenished without a trusted rain source. SQLite event replay and snapshot are checked at 24h, 48h and 72h with `PRAGMA integrity_check` at the end. The world's **actual economic collapse or famine is an expected legitimate measured outcome**, not evidence of sustained resilience. No free resources, post-genesis monetary intervention or special hunger immunity is allowed. Real 7-day financially and nutritionally sustainable acceptance remains **NOT DONE**.

## Provenance correction — water scenario versus actual physical ledger

The labor-aware bound explicitly distinguishes `water_observed_at_t0` (the world’s **two verified physical water units**) from `hypothetical_future_water` (an **uncommitted scenario assumption**). It also returns `water_scenario_total`, which must **never** be presented as an observed world balance or rain receipt. The test asserts both fields even in the otherwise theoretically sufficient 8-field/6-courier case: 2 observed + 22 assumed = 24 scenario units. Neither the operator model nor the test writes rain, transfers or water into SQLite. Any future simulation must obtain fresh water through an independently authenticated real hydrology source and transport it physically.

## 47-G — Physical water-courier test correction (candidate until CI)

**Critical test-harness gap discovered:** the joined eleven-NPC test previously configured an authentic `SupplyCircuitConfigured` courier, but its `_engine` helper did **not** pass `supply_enabled=True`. Earlier 24h/72h observations of unchanged water and zero new food therefore **did not prove the courier had operated**. They remain valid observations of a supply-disabled closed world and evidence that the original finite resources were insufficient; they must not be treated as a passing end-to-end *water-to-field delivery* acceptance.

This opt-in joined-world test fixture now enables the **existing** trusted courier logistics flag, without changing gameplay defaults or reducers. The 900-second joined-world test requires at least one genuine courier load and delivery, a real reduction of well-water stock, and the separate physical conservation proof `audit_physical_supply`. A zero-water joined world proves no water or crop is fabricated. Actual 72h tests will now exercise the courier as well as food and material commerce. Until the exact-HEAD CI verifies the new scenario, neither its previously reported 72h hunger profiles nor its success result may be reused to assert these **new** logistics-on conditions.

## 47-G.1 — Operator-only courier bottleneck projection (candidate until CI)

The read-only `audit_courier` helper distinguishes an **explicitly disabled engine logistics flag** from a real empty source, cargo pickup/delivery, physical route opportunity, scheduled pause and physiological inability. It calls the trusted existing selectors (`choose_cargo`, `choose_courier_leg`) instead of inventing its own courier intentions. Missing source inventory is `unknown`, not zero. It exposes an **operator-wide trace only** and cannot alter a single world event or be passed into NPC/player knowledge. Tiny independent tests cover flag misuse, enabled versus disabled at the same live world state, empty well, unknown identity, and immutable replay. The integrated 900-second test also samples this projection following real delivery. This is instrumentation and **not** a supply policy or proof of viable long-run calories.

## 47-I — Water-to-food evidence and a bounded supply design

Local Python 3.13 observations on the joined 11-NPC world with physical supply enabled:

- Huda loaded one water unit at the well at second 0 and delivered it to the farm at second 50. Nora started planting at the delivery tick and the crop began growing at second 110. The dry control recorded a copper delivery, with zero water deliveries and zero crop starts. Counting all courier deliveries alone would conflate cash and water.
- Under default hunger, one crop ripened at second 86,510. At 72 hours it remained unharvested, Huda still held the second water unit at the well, and all 11 residents were at hunger 100. Six trades, three completed jobs including planting, and one funded wage conserved 12 copper.
- Under the existing slower hunger policy, Nora completed the first harvest and produced three grain units. The market-first trial still had all three units at the farm at hour 42. Huda's hunger was already 92 at the 30-hour departure. Basim had received no grain by hour 42.
- In the slower-policy comparison, the same three opening loaves went to Nora, Huda and Basim at genesis. Huda ate her loaf and carried one grain unit to Basim, who completed a batch by second 110,000. This demonstrated the first physical bake with finite opening provisions. Each scenario retained its original opening water and copper.

The candidate tests check the full physical food and water balance every six hours, record the farm, courier, bakery and market positions of those resources, and reopen SQLite at daily boundaries. The short partition test compares the courier and farm states across different advance schedules. Acceptance requires exact-head CI after the parent PR gates.

The slower-policy event ledger also exposed a scheduling conflict. By hour 54 the repairer had recorded 1,323 homeward legs from the repair shop to the smithy and 1,324 procurement returns in the opposite direction. The procurement travel pass intercepted his commute at the smithy. Full-life workers with an explicit schedule now start optional procurement travel only during their shifts. The regression gives the repairer a short shift, checks that he finishes his paid-material repair and walks both real roads home, and verifies SQLite replay. Focused economy modes retain their existing travel policy.

### Capacity under the current circuit contract

Each courier can serve only one configured field. Eight fields and six couriers therefore deliver at most **18 loaves/day** against at least **23 meals/day** under the slower policy, even with sufficient water. With eight fields and eight couriers, **25 residents** have a modeled minimum of **24 meals/day** and an ideal field output of **24 loaves/day**. This leaves zero modeled margin for activity, late crops, absent workers or missed trips. Twenty-four full crop cycles would require 24 water units. The current fixture owns two at genesis, leaving 22 without a source.

The next field trial can reuse the two-field and two-courier road layout from PLAY-38, the bounded well and attested rain receipts from PLAY-39, and the finite opening provisions from this trial. Settle ownership and funded wages at their physical sites, then track each lane independently through two harvests, baking, market arrival and actual purchase or consumption. Start the drought control with the same opening resources and omit rain receipts. Check replay after reopening and compare transport and food receipts across clock partitions. Use observed batch, water, labor and delivery timings to size a larger village and its opening reserve before a seven-day run.

## 47-J — Two fields, two couriers and a liquidity bottleneck

A local Python 3.13 probe ran the joined 13-NPC economy for 72 hours with two routes and the existing slower hunger policy. Both variants began with two water units, three loaves and twelve copper coins. The wet variant recorded two finite rain receipts through the existing hydrology service, at hours 24 and 48. The dry variant received no rain. The probe reconciled food, water and copper every six hours and reopened and verified the SQLite state at daily boundaries.

| Outcome after 72 hours | Dry | Receipted rain |
| --- | ---: | ---: |
| Rain credited | 0 | 4 |
| Water used for crops | 2 | 3 |
| Mature crop lots, original and eastern fields | 1 + 1 | 1 + 2 |
| Baked loaves | 7 | 7 |
| Bread in the market | 7 | 7 |
| Paid food purchases | 3 | 3 |
| Residents at maximum hunger | 13 | 13 |

By hour 48 the market held the seven new loaves, and all three opening food buyers had spent their balances. Their three meals came from opening stock. One further crop ripened in the east in the wet case, while hunger stopped the workers before they converted it into additional bread. The next comparison should trace sale-funded pay through the existing physical copper routes to determine whether an earned wage can finance a new food purchase. This batch adds no wages, credit or currency to the running world. Acceptance still depends on the parent and this candidate's CI.

## 47-K — An earned wage returns to the bread market

The professional full-life configuration rejected the existing opt-in market
journeys. The focused-economy test already covered funded shopping in isolation.
This batch allows both planners to be enabled together in full-life worlds and
runs funded food travel before optional material procurement. Existing travel
claims, rest needed for an injury, and the normal local market checks still
govern these errands.

The nine-resident two-field fixture starts Farid with an empty wallet. A real
sale funds a physical copper shipment to the farm, where a completed harvest
earns the contracted wage. At two copper he travels over known roads, buys one
loaf at the market, eats it and returns. At one copper he returns with his
wage after finding the loaf unaffordable. Both cases preserve all twelve copper
and verify the SQLite replay at each checkpoint. This isolates one completed
cycle; the 13-resident endurance fixture still needs a longer circulation trial.

### 47-L — Two harvest wages, one purchase in the 13-resident village

The wet variant signs a two-copper harvest wage at genesis and enables the
existing full-life shopping planner. Farid earns two wages, at seconds 86,570
and 174,770. His first wage pays for a market loaf at second 140,600, lowering
his hunger from 70 to 45. At hour 72 he still has his second wage and is at the
smithy, while the food market has six loaves. The current shopping selector
ends exploration at any local stall, including the smithy. The next regression
should let a hungry funded shopper continue past a non-food stall using only
local observations and learned roads. The experiment reconciles all twelve
copper and verifies SQLite replay at each daily boundary.

### 47-M — Returning to a personally known food stall

Full-life shoppers can pass a stall with no local food listings. A fresh wage
permits one return attempt to a personally used food stall via learned roads.
A prior visit funded by an earlier wage cannot trigger an old return trip.
The 13-resident rainy run records Farid's second purchase and meal at second
213,600, after his second harvest wage. Both trips spend exactly two copper.
The original focused shopping mode retains its existing policy.

### 47-N — The fourth-day circulation limit

Two local continuations started from the same verified 72-hour funded save.
One continued with the remaining three water units, and one received two more
units through a finite rain receipt. At hour 96 the added rain was still in
storage. Both worlds had harvested three crop lots in total, stored ten grain
units and retained five market loaves. No fourth-day harvest, wage, purchase,
or delivery occurred. Twelve residents reached maximum hunger, and the market
held four copper while the east farm and Farid held zero. Every checkpoint
accounted for twelve copper and all water and food, with SQLite replay matching
the final state. The funded CI fixture now includes the wet fourth day.

## Closure execution

See [the PLAY-47 closure plan](PLAY_47_CLOSURE_PLAN.md) for remaining gates and the first controlled recovery experiment.

### Closure verification batch — incoming market custody

The extra personal loaf control exposed a second boundary: its sale can credit
personal copper into a courier's consignment-only slot. A local settlement
reproducer failed supply validation. Market settlement now rejects incoming
water/grain/copper into exact-custody slots before writes, and food/grain/material
selectors skip quotes whose payment recipient cannot receive the price. Site
stock sold by a courier steward remains eligible because payment belongs to the
site. No courier pay contract, new account or Schema/Rules change was introduced.

The seven-day thirteen-resident wet/dry control, final SQLite reopen/replay and
96-hour full semantic clock comparison are **verification pending**, not a
recovery or sustainability result. The [closure evidence report](PLAY_47_CLOSURE_EVIDENCE.md)
records exact PR/run identities, observed failures and the future funding
contract boundary. PLAY-47 remains OPEN until the final candidate checks pass.
