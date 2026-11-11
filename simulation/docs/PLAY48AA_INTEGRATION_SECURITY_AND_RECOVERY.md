# PLAY-48AA — record of signed bakery→farm food freight and 45/60 compatibility

**Date 2026-11-11. Project status `PLAY48_OPEN / RELEASE_NO_GO`.** This is an experimental pilot, *not* a released world rule or evidence of surviving 168h. Original `main` is unchanged and no production SQLite save has been migrated.

## Previous verified economics

- [PLAY48Y farm-site Huda wages 48h](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741) SUCCESS 3.10/3.13. The same 13 people and 12 copper, starting with only 3 old loaves (2 at farm, 1 at market) in both A/B arms. Huda earned and ate 2 actual farm-water wages and made 10 deliveries instead of 3; hunger 86 vs100 at hour48. Those 2 old wages were finite.
- [PLAY48V true 96h capped Hana market wages](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657) SUCCESS 3.10/3.13 as a **negative economic result**. Both villages reached 13/13 hunger100 by day4, with ZERO deliveries, work, meals or trade in hours72–96.
- [PLAY48Z physical transport audit](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028314540) SUCCESS 3.10/3.13. The road bakery→farm exists but the existing courier carries COPPER on that return leg; no FOOD freight rights existed.

## Pilot intervention and trust boundary

The new time-zero signed `farm_bread_share=True` on ONE courier circuit is an opt-in grain-for-bread barter. When its worker really delivers a physically collected farm grain unit to the bakery, its durable circuit earns ONE bread entitlement. An entitlement is **not** produced bread, an increase in site stocks, a wage or a meal. The bakery must have genuinely baked at least TWO unquoted/unconsigned bread loaves at pickup; it sends one **bakery→farm over an existing road**, retains one unpromised loaf, and does not carry copper on that same leg. When both options are available, alternate bread and copper return tours; do not secretly delete remittance. Only after an actual site delivery may the circuit mark one entitlement fulfilled and the farm physically own one more loaf. The courier cannot consume entrusted freight.

This one-grain-for-one-loaf rate is a *deliberately generous bounded trial*, not yet audited as a profitable medieval bakery contract; market output and bakery wages may suffer. No automatic new Huda salary follows this shipment: her original pre-signed 2-loaf farm escrow is still capped and exhausted. A future authentic stock-funded farm salary refill would need a separate signed authorization and water-service receipt with a new reviewed rule.

Because the returned-food entitlement fields are persisted, the pilot is explicitly **Schema45 / Rules60** (previous trial 44/59, prior production 43/58). Old worlds cannot be silently imported.

## Exact verified and pending results

| Gate | Status | Exact evidence |
| --- | --- | --- |
| AA0 signed grain-share genesis with zero new stock | VERIFIED | [CI #43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266), test code `4b4c8b663ead5fa5483d23e8b9dee195777d6200`; initial 2 fast tests PASS on **both Python3.10 and 3.13**. Earlier #43032616419 failed test-contract ordering when the farm food / courier cash slots were initialized later in the same trusted t=0 batch. Correction changes neither resource volumes nor courier physical route |
| AA1 adversarial site promises, same-leg copper conflict, cloned freight and tampered credits | VERIFIED | [CI #43034249899](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43034249899), integration code+tests SHA `c10748758cb3664c61ccd1e4c9579d12837c9b8f`: **7 tests PASS each Python3.10 and 3.13**. Synthetic hostile states test guards only, NOT proof that the active world delivered a loaf |
| AA2 *actual* signed 13-NPC 48h return food and wage/economy trace | VERIFICATION_PENDING | Same targeted [CI #43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266), two independent genuine 13-NPC worlds, 24/48h. Must read `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD` and count actual grain claims, physical bread returned, bakery and farm food, copper, meals, hungry people; no happy outcome assumed before logs |
| AA3 authentic old 44/59 SQLite save rejected without modification | VERIFIED | [full-regression CI #43033787068](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43033787068), both Python versions: an old world created under frozen code `1ca9edd7842db924985da9367499cc5183582563` is rejected by 45/60 **without changing file bytes**; this is NOT migration |
| AA4 complete historical 45/60 tests | VERIFICATION_PENDING | Same [#43033787068](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43033787068) on source SHA `a9001058c18831cad5e7ef73b5deb5bad0b2c930`: dual-Python all `simulation/tests` historical tests, with 23 explicit current-world version pins moved to 45/60 and older 43/58 corruption/rejection fixtures preserved |
| Y2 farm-wage 13-NPC 96h personal-income audit | VERIFICATION_PENDING | [#43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) old 44/59 source, still requires final result; genuine day4 recovery cannot be inferred from Y48h |

## Remaining blockers

1. If the new return route delivers **zero** actual loaves, diagnose production timing, real warehouse reservations or transport competition; do NOT spawn loaves or turn off safety constraints.
2. If farm bread is transported but does not reach hungry workers, design and independently authorize **real employer-funded wages from physically delivered stock**, not a new temporary time-zero bonus. Test bankrupt bakery/farm, drought, worker fatigue, wrong road, queued customer offers, no free bakery surplus, repeated/forged service, and real machine replay.
3. A 1:1 raw-grain→finished-bread exchange may be economically unsound. Compare real bakery trade/wages and consider 2:1 or contractual cash valuation **before** canonical adoption, recording any physical loss and market/customer access.
4. Real seven-day same-genesis 13-NPC A/B with live work, deliveries, meals past hour72; drought/insolvency acceptance; full final SHA historical regression; migration review and explicit owner close decision. Until then `PLAY48_OPEN / RELEASE_NO_GO`, no `main` merge, no PLAY49.
