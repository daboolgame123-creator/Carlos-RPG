# PLAY-37 — root-cause treatment plan for an autonomous medieval food economy

**Date:** 2026-11-08. **Status:** diagnosis/acceptance prototype; permanent gameplay changes deferred until each causal gate is measured. **Source:** PLAY-34, PLAY-35, PLAY-36 verified independent-village integration experiments and code-level policy review. **Not a claim of sustainability**.

## A. Proven constraints and causal chain

The physically isolated seven-NPC test starts with 3 loaves, 1 seed, 2 units of water, one one-plot field, one baker, one courier, and 12 copper total. The crop matures **86,400 logical seconds after actual planting**; the seed returns at maturation and can be replanted. Each growth consumes 1 finite water. One real crop produces 3 grain under this test recipe, and one grain can become one loaf. With no weather receipts, wild-food regeneration, imports, added water or external actors, the **optimistic three-day supply ceiling is 3 + 2 × 3 = 9 loaves**.

Default metabolism adds 1 hunger per 300 simulated seconds; activity is additional. Eating consumes one physically owned loaf and reduces the eater's hunger by 25. Work is blocked above hunger 89 or fatigue 69. The courier is prohibited from starting a leg at hunger 90+ or fatigue 70+. Fatigue accumulates 1 point every 600 seconds outside an active rest action. In `economy_only_enabled`, general NPC actions—including rest—do **not** run, so high fatigue is a separate guaranteed later lockup in that focused mode. Full NPC mode has rest decisions, but verified PLAY-36 full-mode results also show famine; never generalize the no-rest limitation to it.

For this fixture, baseline hunger starts at Basim 0; Salma, Nora, Huda 20; and Adel, Omar, Layla 80. Without meals, Nora/Huda reach hunger 90 in 21,000 seconds; Basim in 27,000 seconds. The first field cannot mature before 86,400 seconds even with instant planting; the actual observed due time was 86,510 seconds. At the end of 72h, only one crop matured, remained unharvested, no bread was baked and the water courier was carrying an undelivered unit. Price and cash allocation affect initial meal access, but **cannot fix the pre-harvest workforce collapse**.

### Necessary quantitative feasibility bound (not sufficient)

To keep each NPC's hunger **strictly below 90 at every instant** until 72h, ignoring all additional activity hunger, a perfect planner would need at least

`sum(ceil(max(0, initial_hunger[NPC] + floor(259200 / hunger_period) - 89) / 25))`

physically consumed loaves. Initial hunger and ownership are validated from the actual genesis world, not invented. For `hunger_period=300`, the bound is **232**, a minimum deficit of **223** from the optimistic 9. For `hunger_period=3600` (the pre-existing, trusted time-zero optional policy), the bound is **12**, deficit **3** even with perfect distribution and no extra activity. This is a necessary condition, **not a survival guarantee**: local access, shifts, fatigue, resource timing and consumption rules can make the real demand larger. The no-rest fatigue threshold for Huda/Nora is 39,000 seconds, for Basim 42,000, also well before first maturation.

**Important:** Changing an input to make the budget arithmetically feasible is a **world-design choice**, not a bug fix. No arbitrary extra food, mythical rain, blanket hunger immunities, credit or teleported transfers may be used to claim success.

## B. Causal fault tree and verification work

| Causal layer | Evidence | Planned remedy | Falsifiable gate |
| --- | --- | --- | --- |
| Demand vs physical growth | 9 upper supply vs 232 minimum need at old default | Explicit world-scale nutrition, harvest yield, acreage and population model | Closed-world lower/upper bounds established before each full simulation; unviable fixture correctly flagged |
| Time/effort mismatch | Hunger threshold before 24h crop; fatigue threshold before first harvest | Make day/night, rest, action effort and crop duration coherent, with **trusted** per-world calibration instead of weakening safety limits | Workers remain physically capable through the first attainable harvest in at least one funded/feasible world; still exhaust under overload |
| Material regeneration | Crop returns seed, but consumes one nonrenewable unit of water | Closed water accounting and authenticated rainfall/terrain flows; explicit drought | Rain receipts or actual local storage explain every replenished water unit; drought prevents growth |
| Professional logistics | One courier trapped with reserved water; static multi-stop route and late hunger | Local bounded cargo contracts, rerouting/return, realistic schedule and recovery; no cargo-eating | Parcel/copper provenance, no teleport, co-location and durable delivery or documented failed attempt |
| Food ownership | Market has goods while nearby workers cannot eat; money may be elsewhere | Locally financed labor meals / earned wages with immutable provenance and voluntary NPC policies | No assistance or salary without actual owned stock, funded payer, accepted work and delivery |
| Independent agency | Economy-only skips normal NPC decision loop, including rest | Define one authoritative NPC scheduler for combined roles, preserve intentional focused bench mode | Full NPC life shows rest, farming, logistics and emergency choices without scripted success, no multiple same-tick actions |
| Scale and resilience | Seven NPCs can share only 3 starting loaves | Multi-plot production/seasonality and true demand throughput; money secondary | At least 7 simulated days, controls + weather/drought + market exclusions, no guaranteed happy ending |

## C. Execution sequence: solve dependencies, not symptoms

1. **PLAY-37A — hard feasibility gate (this PR).** Pure read-only, explicit test-fixture arithmetic; two metabolism policies, water 0/1/2 controls, worker hunger and no-rest fatigue deadlines, privacy and replay. This tells us when feeding everyone is literally impossible, even with perfect logistics.
2. **PLAY-37B — viable world-design envelope.** Specify at least one credible, time-zero resource/water/labor/consumption scenario that has supply **above** the necessary demand bound, without cheating or claiming that quantity automatically reaches people. Run a control and a drought world. Do not silently change old-world defaults. Any material regeneration must be an authenticated environmental input or an internally causal, auditable ecosystem.
3. **PLAY-38 — professional work-and-rest continuity.** Investigate a unified role scheduler: routines, fatigue, day/night rest, nutrition and crop timing. Workers may become sick/exhausted and jobs may fail. Check both economy-only and full-NPC behavior, precise 1-second boundaries, determinism, replay, versioning and historical compatibility.
4. **PLAY-39 — actual local food delivery and wage/meal contracts.** Use existing authorized physical exchange contracts where possible; introduce new event types and version pins only when a missing capability is proven. Transfers must debit an existing owner and reach the beneficiary in the actual location, never remotely. Distinguish employer meal, charity, market sale, courier consignment and personal food. Reject double spending, owner impersonation and meals of reserved cargo.
5. **PLAY-40 — renewable material cycle and demand/production audit.** Multiple genuine fields/couriers as appropriate, crop seed return, finite land/labor/tools, verifiable water inflows and transport throughput; monitor loss/shortage. No free magical harvest, infinite rainfall or producer credit.
6. **PLAY-41 — independent 7+ day village acceptance.** In at least two **feasible** independent 7-NPC villages, validate individual hunger/fatigue, crop→grain→bread→owner→meal, 100% physical ledger conservation, replay/restart, privacy and role autonomy. Include **adverse** worlds with drought, exhausted workers, empty wallets, failed routes and credible hunger; famine is permitted when causally warranted. Pass on Python 3.10 and 3.13 and historical CI on exact SHA; independent review / P0 remain separate release gates.

## D. Governance and non-goals

No player-centric quest work in this sequence. No fake survival results from prefunded test bootstrap loaves. Do not treat `economy_only_enabled` as the definitive game-world behavior. Until the system supports a **feasible** closed or evidence-backed open resource flow, simply increasing NPC "willpower" to work while dying of starvation is not acceptable. The canonical story and `main` remain untouched. Prior PLAY-32–36 requests are stacked/draft until full final-commit CI confirms compatibility; successful targeted tests alone do not justify release.

**Decision policy:** A feasibility proof may close PLAY-37A but **not** the overall famine problem. Complete end-to-end, multi-day, autonomous survival/recovery in a physically feasible world is the only basis for declaring the root problem solved.
