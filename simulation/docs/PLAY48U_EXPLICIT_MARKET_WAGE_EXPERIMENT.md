# PLAY-48U — signed market-funded courier wages, research branch

**Status:** `EXPERIMENT_ONLY / PLAY48_OPEN / RELEASE_NO_GO` (2026-11-11 Iraq). This is NOT a full village recovery. The production world remains Schema **43** / Rules **58** until an explicit migration/acceptance. This branch intentionally bumps to **Schema 44 / Rules 59** because a signed wage-limit field is persisted and a new event alters the contract. Old saves must **not** be loaded as new saves without authorized migration; `main` unchanged.

## Evidence that motivated it

- [S3 true 96h A/B #42926808427](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42926808427) SUCCESS on both Python versions. Thirteen NPCs, 12 copper, same original food. Both finite-wage worlds reach **13/13 hunger=100 by hour96** and absolutely zero new deliveries, jobs, meals or sales from hour72 to96. Early wages improve meals 6→7 and jobs 23→26 but do not cure the village.
- [T true operator-only 48h market access #42931612578](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42931612578) SUCCESS Python 3.10/3.13. **10 real bread at market and 10 unit open quote** day2; seller is physically at market site but temporarily busy, so not available to trade at checkpoint. **Zero of five residents at hunger100 can personally afford the 2-copper price.** Two couriers at hunger100 are physically at well, cannot begin a new leg. Do not confuse marketed/quoted bread with actual food access, coins in business treasuries with people's personally spendable cash, or personally observed information with global operator diagnostics.

## Implemented bounded hypothesis

`CourierProvisionConfigured` still requires trusted time-zero signed employer. New optional `authorized_total_units` defaults EXACTLY to the already-paid-for `units`, so all old one-shot contracts remain **non-renewable**. The owner may explicitly sign a higher hard maximum (at most **3**, market site only). This does not create money, food or escrowed stock at sign time.

An opt-in `market_sourced_wage_refill_enabled` only activates on an **actual food cargo delivery to that market**, by that exact courier, physically present and not busy, in the SAME trusted atomic active-world supply command. It requires the pre-signed market contract, no remaining prepaid escrow, unpaid distinct delivery count, and at least **2 truly uncommitted real site-owned loaves AFTER subtracting all OPEN customer sale offers and any physical cargo reservations**; one unlisted loaf is retained with the merchant. The wage is never sourced from food already advertised to buyers. The actual market keeper must be available locally. The event sequence is:
`SupplyCargoDelivered(food)` → `CourierProvisionReplenished` → `CourierProvisionPaid`.
The store validates strict adjacency, actor/service/time; the reducer independently validates location, employer ownership, signed ceiling, inventory, custody, salary receipt and uniqueness. Real market bread decreases by one before that one salary is escrowed and paid into the worker's **personal** food inventory. No entrusted cargo can be eaten.

The single market-employed worker here is **Hana**; Huda's pre-signed farm-water contract remains one-shot because that farm has no baked bread. Even if market wages work, they CANNOT be claimed to rescue Huda or solve everyone's hunger.

## Independent verification gates

1. [current PLAY-48U CI #42999941836](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42999941836), code SHA `81b8446aa6551f121997b7c79d601df35d181682`: both dual-Python fast security/genesis tests SUCCESS, including forged service and forged re-funding rejection and a synthetic reducer-only adversarial test rejecting already-listed stock and repeated pay receipts. **48h authentic A/B remains pending as of this document.** The prior #42999260384 and #42999798275 were cancelled by workflow concurrency on source changes; do not count them as economic failures. Do not claim wage refills happened until `PLAY48U_GENUINE_MARKET_BACKED_COURIER_REFUND_48H` is read.
2. If no actual refills despite physical stock, inspect time-synchronous real supply delivery receipts, merchant availability and hard caps. Never remove a guard just to make counters rise.
3. Once any real physical refill is verified, add adversarial tests for wrong worker, duplicate receipt, unsignalled employer, expired hard ceiling, insufficient stock, steward not present, trade/cargo reservations, deliberate drought and insolvent markets. Record successful deliberate rejection and replay, not only pure policy calculations.
4. Measured 72/96/168h genuine A/B and full exact-head Python3.10/3.13 regression are still required before decision. This isolated experiment does not authorize saved-world conversion, automatic payroll, a new job branch, `main` merge or PLAY49.

**Economic goal:** genuinely earned income and personally accessible physical food. No fictitious hunger reduction, coins, bread, available NPC route, storefront, subsidies, or production.
