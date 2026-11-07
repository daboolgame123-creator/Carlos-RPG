# PLAY-23 — Bounded grain-to-meal chain: planning and acceptance

Date: 2026-11-07. Status: CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER.
Base: PLAY-22 documented HEAD `19be894a6965c205539257d97f3db8a3391e8cea`.
Branch: `simulation-engine-phase-play-23-food-chain`.
Scope: disposable seven-NPC PLAY-21 ecology world; no `main` merge, story import, new schema/rules, player health, NPC death, or fictitious resources.

## Verified technical gap
- The seven-NPC ecology consumes all eight seeded food units and leaves all seven with high hunger by t=1800; no recurrent farm-to-meal loop exists.
- `NPCProductionService.start` enforces real actor, profession, location, site-owned recipe inputs, tool reservation and due timestamp. `ScheduledEventFired` creates only site-owned product.
- `NPCMarketService.post/buy` enforces registered site steward, physical buyer/seller, owner balance, price, initialized copper and transfer. An NPC's purchased `food` stays owned but does NOT lower hunger until `NPCFoodConsumed` occurs independently.
- A separate test-only trusted coordinator MAY initialize an explicit one-time grain/oven/coin endowment and request a producer job and an explicit NPC market transaction. That is a **scripted trade** in this phase, **not autonomous NPC economic choice**; future autonomous purchase planning requires policy design and testing.
- Production and sale will run during a test setup window 0..90 using `TimeEngine`, before starting the seven-NPC ecological living-world planner. This models physical baking duration and transaction ownership but DOES NOT claim other NPCs were autonomously active during the setup window. Thereafter living-world NPCs make their own feeding/navigation choices.

## Implementation batch and verification
| Work | Execution | Required acceptance |
| --- | --- | --- |
| 23a | New *separately marked* production ecology fixture derived from PLAY-21. Initialize one grain, one oven, square-owned food=0 and copper=0; Adel owns 2 copper; configure one baker recipe (grain:1 → food:1 after 90s), Salma site steward. | At time zero no manufactured food, no old-world changes, marker distinct |
| 23b | Start Basim's real baking job, reject second overlapping job and premature offer; advance exactly 90s and verify one site-owned food unit, zero remaining grain and unchanged oven. | No output before due, no instant production or duplicated raw goods |
| 23c | Compare `sell` vs `hold`: Salma posts one priced offer; explicit entrusted/test-scripted NPC buyer Adel either buys at exact price or does not. Refuse remote buyer, wrong-price and insufficient-coin transactions atomically. | Copper conserved, seller not granted free coins, food ownership explicit |
| 23d | Start the existing real seven-NPC ecology on the completed physical state, advance player clock explicitly and check whether Adel autonomously eats from his personal inventory in `sell`, but cannot do so in `hold`. | Mealtime belongs to NPC planner; transfer != meal; extra food shifts actual documented outcome |
| 23e | Full conservation ledger (8 original wild/owned food + 1 original grain, which may convert exactly 1:1 to food), privacy and SQLite full genesis replay/restart, duplicate/revision rejection, dual Python tests, scenarios and full repository regression. | All targeted/full CI successful on exact code SHA before technical closure |

## Constraints
- No automatic salary, free grain, site-to-NPC teleportation, omniscience or forced behavior by Carlos.
- Sold food must be bought with initialized NPC copper. The fixed recipe/price/trade are test-only inputs; they are not autonomous buyer/vendor decision policies.
- Long-term food sustainability, NPC starvation consequences and real NPC economic planner **remain open**; one grain is not an infinite cycle.
- Existing PLAY-20/21/22 worlds retain old opt-in behavior. P0, PLAY-14g, 03-A7c, 03-A and external review remain OPEN.

## Verified technical closure (2026-11-07)

- Last real code-and-test commit: `23f64c5627c5a141dd00ffc560dccc29eac2190c`; **Schema 34 / Rules 46** unchanged.
- [Full CI 42407810466](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42407810466): `completed/success`, 1,508 passed on Python 3.10 (732.87s) and 1,508 passed on Python 3.13 (507.13s), exact code SHA.
- [Targeted CI 42407810568](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42407810568): `completed/success`, 70 passed per version, followed by two real 360-second grain-to-meal world trials on each version, identical outputs.
- At the first independent NPC tick t=90..91, scripted sale to Adel resulted in a documented NPC meal and hunger 80->55. No sale means Adel received no site-owned food, ate no meal then, and hunger remained 80. At t=360 both worlds had 6 NPC meals from different sources; sale: site food0/wild3; hold: site food1/wild2. Total grain+food=9 conserved, copper=12 conserved.
- Rejects: invalid actor, busy producer, early quote, remote buyer, fake unit price, filled quote, absent grain, poor buyer, duplicate and stale commands. SQLite full replay, reopen and player-view privacy verified.
- Full [report](PLAY_23_FOOD_CHAIN_REPORT.md). Purchase/baking setup is scripted during t0..90, **not autonomous economic behavior**. Repeated sustainable farming/economy, mortality, P0 and external review remain OPEN.
