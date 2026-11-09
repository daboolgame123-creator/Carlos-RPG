# PLAY-47 — NPC economy: multi-day endurance and root-cause measurement

**Status: OPEN / FIRST INSTRUMENTATION PILOT.** Depends on PLAY-46's **technical** closure at `a346d8b5f3fe4b736e420bfa3e470a8afa089313` (Python 3.10/3.13 full CI green, review deferred by owner). No external approval, P0 signoff, `main` merge or durable save support.

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
