# PLAY49-J — opt-in, one real costed cooked plate (experimental only)

Parent source: isolated PLAY49-I Rules71 audit candidate SHA `07aeb89ef33aac7cd45efd00f1e2d00ce81597f1`. No merge with PLAY48 or main, no release.

## Finite causal chain

- Existing real PLAY49-G fixtures generate two distinct physical orchard and dairy batches, wages, real site markets, and genuine Huda road travel. PLAY49-I's on-site merchant independently buys one fruit (2 actual copper) and one cheese (3 actual copper) for the tavern wallet on successive simulation ticks.
- The actual configured cook works at the tavern in a **trusted time-zero finite shift**. Existing `LivingWorldEngine` starts the compound recipe using both previously purchased, site-owned inputs, spends 300 real simulation seconds and creates exactly one food at job completion. No extra outputs or virtual work.
- A new `costed_prepared_food_enabled=True` **opt-in** selector is enabled only together with `site_procurement_enabled=True`. A present merchant may quote one plate using an actual completed recipe, unambiguous paid site-owned input purchase receipts since the preceding recipe job, and the existing signed cook wage. Price = 2 + 3 + 1 = **6 copper**, not the previous generic food quote of 2. No paid receipts or confusing ownership => no auto menu quote. Other food stalls and default-off behavior are unchanged.
- Public site food stays site-owned. The posted menu quote does **not** compel a sale. In the negative test, Huda has already eaten and is not hungry enough, so the meal remains unsold and the tavern has **zero** copper, no paid second wage. In the positive test, an **explicitly labeled test fixture NPCNeedChanged** sets Huda's hunger to 80; it is not alleged to have arisen naturally. The existing hunger/wallet buyer selector may then buy only because Huda is truly on-site, owns 8 copper and owns no personal food. Actual 6-copper purchase revenue and subsequent signed once-only 1-copper wage recover 5 copper working capital. 22 total copper conserved.
- This prototype proves a **conditional, single-plate autonomous cook/menu/sale**, not an endlessly self-sustaining village. It has no autonomous upstream fruit/cheese delivery, no natural hunger generation proof, no remittances, and no 96h/168h stabilization.
- No new event types, database columns, or state shape are introduced by PLAY49-J. It relies on pending Rules71 event compatibility from audit PR147. `Rules71` remains a candidate; old Rules70 saves must fail closed, never be silently reinterpreted.
- Acceptance: Python3.10 + 3.13 exact-head focused and full CI, verification/replay/snapshot, no nonphysical money, stale/missing quote refusal, legacy default-off; retain Draft/NO_GO pending PLAY48. No manual test required for these automated engine-only trials.

**Status: PREPARATION_ONLY / DRAFT / PLAY48_OPEN / RELEASE_NO_GO**.
