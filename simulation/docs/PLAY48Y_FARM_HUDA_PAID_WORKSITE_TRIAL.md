# PLAY-48Y — truthful farm-worksite food wage trial for Huda

**2026-11-11 — PLAY48_OPEN / RELEASE_NO_GO.** Isolated trial, not a new resource system, not a production save migration, not an authorized `main` merge. The branch begins from the experimental **Schema44 / Rules59** code and already-versioned tests. The last fully verified historical test run `PLAY48X #43014260381` (at SHA `b939992d9d342175d042cb206e4c545fc4ea2a15`) passed **1,696 tests on each Python 3.10 and Python 3.13**, plus real old **43/58** save immutable rejection. This does NOT automatically approve Y's new fixture changes.

## The observed reason for the trial

From [real 48W A/B #43007695830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007695830), making the merchant sign two *market-based* food-pay contracts failed to nourish Huda: her documented route delivered WATER to the FARM but she never met the MARKET FOOD-DELIVERY wage condition. Her **market wages paid=0**, hunger100, and only 3 supply deliveries by 48h. Hana instead received two real, genuine wages beyond the time-zero escrow, and village meals increased 5→7, though the extra income did not reach Huda.

A real worker should collect an agreed wage at the **actual worksite** after verified labor. The existing pre-signed `farm_water_delivery` proof is appropriate; unlike the new merchant rule, it does NOT require a fictional market stop. But the existing farm pre-payroll was only **one loaf**, and no actual recurring farm-owned bakery bread is delivered to refill it.

## Bounded test-only intervention (no minted bread)

- Same **13 residents, 12 original copper, 3 initial bread loaves**, real 24h crop maturation, original finite water/rain, physical roads, real timber/charcoal jobs and both courier circuits.
- Trusted genesis ownership variation: **2 original real loaves at FARM and 1 at MARKET**, *instead of* the historical **1 FARM / 2 MARKET**. Farm immediately escrows its 2 actual loaves to the already implemented signed `CourierProvisionConfigured` for `huda`. Market keeps 1 loaf for possible sale.
- This is NOT a regular gameplay transfer or food subsidy. The existing `_joined_bootstrap` test fixture has a new explicit, bounded parameter `farm_initial_food_loaves=2` allowed only with `farm_opening_food_wage=True`; default remains 1 (old fixture unchanged).
- The **two** independent 13-NPC worlds are strictly equal at time zero, including escrowed food and copper. Only `early_courier_food_wage_enabled` differs. Earned farm wages may only pay after a true WATER delivery while Huda is physically at the farm, with a genuine same-command delivery receipt and immutable pay record. The old market employee Hana receives no newly invented wages in this trial.
- Both run for **real 24h and 48h**, recording personally earned and eaten Huda meals, completed logistics, bread baked and sold, 13-NPC starvation, all 12 copper, food conservation and reopened SQLite event replay.
- **No renewable wages are implemented here.** At most two loaves can ever be earned by Huda, even if the test improves her hunger temporarily. An A/B benefit must not be called economic recovery. The shifted opening bread also means 1 fewer loaf initially available to shoppers, a real trade-off that must be reported.

## CI / next gates

- [PLAY-48Y CI #43017271741](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741), exact source SHA `81cddebbc738832c2409f603f38d2fb6f805eca4`: **Genesis and physical conservation checks PASSED Python3.10+3.13**. The true 48h independent A/B is a separate longer stage and must be checked for results before reporting effect.
- [PLAY-48V actual 96h #43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657): independent actual multi-day recovery remains pending until explicit logs; do not extrapolate from green 48h.
- [PLAY-48X full historical 44/59 CI #43014260381](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43014260381): **SUCCESS both Pythons 1696/1696 each**, but old 43/58 saves rejected; no migration.
- If the farm wage buys time, the next real design needs **bakery-produced, employer-owned food to be physically carried to the farm on a documented route after actual procurement**, not a magically refilled farm pantry. A payment from off-site bakeries, a fabricated local road or two extra infinite farm loaves is disallowed. Track purchase/barter/consent and shop-offer reservation protection. At famine, genuine negative outcomes must remain possible.
- No PLAY49, production approval, save migration, or `main` merge.
