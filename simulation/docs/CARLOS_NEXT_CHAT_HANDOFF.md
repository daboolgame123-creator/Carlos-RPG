# Carlos RPG — Current evidence-based handoff (11 November 2026)

Read root AGENTS.md, the project work-routing rules, and [PLAY48U/V/W verified decision](PLAY48U_V_W_VERIFIED_DECISION.md) before implementation. Check the actual latest GitHub branch heads and CI jobs: **this file is a dated handoff, not live status.**

## Stage and code

- Repo: https://github.com/daboolgame123-creator/Carlos-RPG
- **PLAY48_OPEN / RELEASE_NO_GO**, no PLAY49, no `main` merge, no production save migration.
- Experimental `carlos_sim` code at shared base SHA `81b8446aa6551f121997b7c79d601df35d181682`, **Schema 44 / Rules 59**, not compatible with earlier persistence by assumption. Historic approved schema/rules baseline is 43/58.
- Engine remains independent, NPCs only locally know roads/offers. 13 residents, 12 physically conserved copper, and 3 real starter loaves, bounded real rain, real crop maturation/hunger. No artificial currency, food or instant service.
- Branch `experiment/play48u-market-sourced-wage-refill-20261111` contains experimental rules59 signed site-owned food wage replenishment and new `CourierProvisionReplenished` event, with `authorized_total_units` ceiling on trusted employer agreement. A real delivery, merchant local presence, free unlisted unreserved stock and same-command unique worker/service proofs required. **Open shop food quotes are protected**, as is consigned cargo; no payment before actual work.

## Verified economic result

[PLAY48U actual 48h CI #42999941836](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42999941836), **SUCCESS Python 3.10 / 3.13**: signed Hana market contract paid **2 genuinely new food wages** on top of her one initially escrowed loaf. Her cumulative meals 1→3, hunger after 48h 100→60, village meals 6→8, hunger100 villagers 5→4, market site bread 10→8, 35 authentic Hana deliveries in both arms, 12 copper unchanged. Huda still 100 hunger. Do not claim deliveries increased in this experiment. Separate baseline [S3 96h #42926808427](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42926808427) proves 13/13 starvation and zero new work or food after hour72 in the prior **finite** wage world. T market audit [#42931612578](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42931612578) proves 10 real bread and open quote available while none of 5 hunger100 people owns spendable 2 copper. Workers' ownership and personal wages are the bottleneck, not solely production.

## Currently running independent experiments

| Task | Branch / run | Correct status at last check |
| --- | --- | --- |
| PLAY48-V 96h actual signed Hana market wages | `experiment/play48v-genuine-market-wages-96h-20261111`, [CI #43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657), SHA `37cd8fb5a1d5fed140a3c5d9ec19b4cac164e0a3` | Python3.10/3.13 real 24,48,72,96h genuine A/B **in progress**, no results yet. Verify logs `PLAY48V_TRUE_FOUR_DAY_MARKET_WAGES_CAUSAL_PROOF`, including post72 working / deliveries / meals. |
| PLAY48-V complete historical regression | `experiment/play48v-genuine-market-wages-96h-20261111`, [CI #43007340412](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007340412), SHA `60f5650bdbbeabc47726f3ca8f12d22a415db7c0` (same engine and tests plus workflow) | Full Python3.10/3.13 suite **in progress**. Old hardcoded schema/rules fixtures may fail by design; do not claim regression success until exact results examined. |
| PLAY48-W two market-financed courier contracts | `experiment/play48w-two-market-courier-contracts-20261111`, [CI #43007695830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007695830), source `c9f7c4309e392996da19a361fb1dbebe0c0cffb3` | Both Python3.10/3.13 **genesis tests PASS**; real 48h A/B in progress. This is a *different trusted time-zero employer/stock-ownership scenario* than U (all original 3 loaves in market, market contract for Huda AND Hana at one prepaid bread each), but W control vs W trial share exact genesis. No artificial goods or currency. |
| PLAY48-W documentation update | `experiment/play48w-two-market-courier-contracts-20261111` HEAD after documentation commits | Documents alone not test success and do not alter engine code |

## Work rules

1. Always inspect actual GitHub Actions statuses and parse real logged JSON before reporting work as passed or claiming simulated hunger reduction. Correct test-oracle false positives independently.
2. Experimentally successful payroll does NOT mean viable 96/168h multi-day economy; **do not** disable hunger>=90 safety, pay for fake deliveries, reassign customer sales goods, mutate NPC directly, grant remote market knowledge, or invent stock.
3. If V fails after hour72 or W still leaves 13 NPCs starving, broaden legitimate job income and personally owned food access for non-courier workers, using genuinely employer-funded physical work and signed contracts. The existing Hana-only contract can pay max 3 per signed term, not indefinitely.
4. Reject new Schema44/Rules59 save migration and merge until full new-head regression, adversarial drought/insolvency, actual 7-day replay and explicit owner acceptance. Preserve immutable SQLite event log and historical integrity.
