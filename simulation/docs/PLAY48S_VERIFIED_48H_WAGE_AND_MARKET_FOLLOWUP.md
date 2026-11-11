# PLAY-48S — actual 48-hour bread wage result and next test gates

**Date:** 2026-11-11 Iraq / 2026-11-10 UTC. **State:** `PLAY48_OPEN / RELEASE_NO_GO`, Schema 43 / Rules 58 unchanged. No `main` merge or production save migration.

## Verified authentic 13-NPC same-genesis A/B

Test source: `99b615d5b0453dd2eee84d6657f89f4d8bb9d098`, [GitHub CI #42924173716](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42924173716), **all four jobs SUCCESS on Python 3.10 and 3.13** (12h real delivery/wage+forgery gate, and full 48h physical village A/B).

Same precise **3 opening real loaves, 12 copper, 13 residents**, true 24h grain maturation, separately recorded bounded rain, actual wood/charcoal, documented fertile east-field productivity 12 grain per genuine watered harvest, true physical roads, and both employers pre-fund one existing loaf to their courier. Only opt-in **payment timing** differs; original H1 market wage remains available as designed even in the control.

| Verified observable | Strict original timing, day1 | Earlier existing service pay, day1 | Strict day2 | Early pay day2 |
|---|---:|---:|---:|---:|
| Real consumed meals, cumulative | 1 | 3 | 5 | 6 |
| Huda physical deliveries, cumulative | 3 | 3 | 3 | 6 |
| Hana deliveries, cumulative | 3 | 3 | 34 | 35 |
| Bakery completed bread batches, cumulative | 0 | 0 | 12 | 13 |
| Actual bread sales, cumulative | 1 | 1 | 4 | 4 |
| Food units still owned by market | 0 | 0 | 9 | 10 |
| NPCs at hunger 100 | 3 | 3 | 5 | 5 |
| Huda hunger | 78 | 53 | 100 | 100 |
| Hana hunger | 78 | 53 | 100 | 100 |
| Total copper | 12 | 12 | 12 | 12 |

**Causality:** Existing real food-wage contract pays one bread each to Huda and Hana for actual service. Both **eat their own** bread by day one when hunger crosses the autonomous threshold; eating consumes owned inventory, not consigned cargo. This causes 2 additional actual meals and 25 fewer hunger points at the end of day one, and allows Huda to complete 3 additional documented deliveries by day two. However both workers eventually reach hunger 100 again because the signed employer escrow is exhausted. No seven-day or day-four economic recovery has been demonstrated.

## Open independent bounded gates

1. **PLAY48-S3:** four-day 13-NPC A/B, identical genesis, [CI #42926808427](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42926808427) exact test SHA `151104b93ae696898b982f7dba33eea75fd42ab8`; checks days 1/2/3/4, actual post-72 deliveries, jobs, meals, market sales, fatigue/hunger, total food/copper and reopened SQLite. **Check 3.10/3.13 final statuses; no result inferred while running.** The control still legitimately pays Hana under existing H1 after a real food market delivery.
2. **PLAY48-T:** independent operator-only bread saleability diagnostic [CI #42931612578](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42931612578), code SHA `463e76cbbb54b7d9d5de29c510231d2ac54b3a85`, 48h 13-NPC paid-world physical market stock versus genuinely open quotations, seller physical presence and 13 personal hunger/wallet/route access records. **Never expose global audit details to NPC planner.** Check actual CI and logged `PLAY48T_REAL_DAY1_DAY2_MARKET_FOOD_ACCESS_FORENSICS`.
3. **PLAY48-S2/T design:** Pre-existing pre-funded employer food wage is finite (at most 3 original units under current reducer). Replenishing it from new *real employer-owned bakery bread* after verified subsequent services needs a new authorization model, fresh service receipt idempotence, market inventory ownership and sale-reservation reconciliation, and **explicit rules/schema/version treatment**. Do not silently change `CourierProvisionConfigured` bootstrap-only semantics, mint ration/cash, divert entrusted cargo, ignore earned labor or bypass hunger safety guard.
4. Genuine 96/168h recovery remains an **acceptance** claim, not a unit-test pass. Preserve genuine drought, insolvency, hunger and failure outcomes and do not start PLAY49.

The recurring-wage design threat model is [PLAY48S2_RENEWABLE_FOOD_WAGE_THREAT_MODEL.md](PLAY48S2_RENEWABLE_FOOD_WAGE_THREAT_MODEL.md). Permanent food access must be achieved by a real, accountable economic cycle — not simply raising field yield once.
