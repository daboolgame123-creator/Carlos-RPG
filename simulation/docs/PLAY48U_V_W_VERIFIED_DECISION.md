# PLAY-48 — Verified market wages, no fake recovery (2026-11-11)

**Status:** `PLAY48_OPEN / RELEASE_NO_GO`. This is an independent experimental branch, not approved production code. `main` and production save migration are untouched. Experimental code carries **Schema 44 / Rules 59**, whereas the older validated engine was **Schema 43 / Rules 58**. Those saves are NOT interoperable by assumption.

## Actual verified result — PLAY48-U

- [CI #42999941836](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42999941836) **SUCCESS** on Python 3.10 and 3.13, code HEAD `81b8446aa6551f121997b7c79d601df35d181682`.
- 13 unchanged people, total 12 copper, three genuine starting loaves including two original paid escrows, one original farm-water wage, existing water/rain/wood-charcoal and time-based 3+12 physical agriculture.
- Both A/B use the SAME trusted signed genesis. Only `market_sourced_wage_refill_enabled` differs.
- At **24 h**, neither world had any real new market wage; each had 3 actual consumed meals, 3 people hunger100, and 0 market food.
- At **48 h**, the treatment actually paid **two additional food wages to Hana**, each from newly produced, actually delivered, MARKET-owned food, capped by the merchant's signed maximum of 3 total wages (1 original + 2 additional); personal consumption recorded 3 Hana meals versus 1 in control, with **Hana hunger60 versus100**.
- Total 48h village meals **6 control vs 8 treatment**, starving at hunger100 **5 vs4**, real market food **10 vs8**, genuine Hana deliveries **35 vs35** and Huda deliveries **6 vs6**, Huda still hunger100. At this point extra wage did NOT increase courier deliveries; the improved individual food/health is a measured fact, not a demonstrated supply-chain revival.
- The 12 copper remain intact and no customer open offers or consignment lots were spent to pay wages. The new contract is bound to 2 extra units: NOT an unlimited wage cycle or an automatically sustainable economy.

## New acceptance experiments (strictly separate)

| Experiment | Exact source/run | Current known state / evidence needed |
| --- | --- | --- |
| **PLAY48-V:** genuine market wage 96h | `experiment/play48v-genuine-market-wages-96h-20261111`; [CI #43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657), SHA `37cd8fb5a1d5fed140a3c5d9ec19b4cac164e0a3` | Pending final Python 3.10/3.13; compare real 24/48/72/96h and genuine post72 deliveries+work+meals. A green test can measure negative results; no recovery inferred |
| **PLAY48-V full regression** | [CI #43007340412](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007340412), SHA `60f5650bdbbeabc47726f3ca8f12d22a415db7c0` (same engine; two workflow/test additions) | Pending complete 3.10/3.13 regression under intentional Schema44/Rules59 bump. New schema may reject historical save fixtures by design. Do NOT count old Schema43 tests from previous runs as new-head acceptance |
| **PLAY48-W:** two market couriers from genuine three starting loaves | `experiment/play48w-two-market-courier-contracts-20261111`; [CI #43007695830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007695830), SHA `c9f7c4309e392996da19a361fb1dbebe0c0cffb3` | Dual-Python **genesis** checks SUCCESS; actual 48h A/B still needs verification. Both workers' employer market contracts pre-reserve one real original loaf each from the 3; 1 remains for shop. This world is an explicitly DIFFERENT employer/initial stock ownership counterfactual from U, while W's own A/B share identical initial state |

## Root-cause limits

From [S3 96h test #42926808427](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42926808427): both finite-wage worlds have **13/13 hunger100 and zero post72 jobs, deliveries, meals and sales**. From [T market audit #42931612578](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42931612578), 10 genuine market loaves were simultaneously advertised as an open customer offer, while **zero of five hunger100 villagers possessed a personally spendable 2-copper purchase price**. Both couriers hunger100 at the well; market seller occasionally busy.

**Next:** Check V/W actual logs with exact source SHA before any new policy. If all people starve despite wages, broaden legitimate worker income/food access from *real completed services* and employer owned physical stock, not magical lowering of hunger or arbitrary new wealth. Preserve order of operations and pre-signed employer authority, open offer reservations, cargo custody, local routes, no shopper omniscience, and actual tracked water/food. Explicitly document old save version migration and full updated regression before phase closure.

Do not start PLAY49 or merge production without explicit acceptance.
