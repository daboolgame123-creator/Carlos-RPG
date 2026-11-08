# PLAY-39A — finite cart capacity, no extra mouths or magic freight

**Status:** draft engineering branch; full historical CI and independent review separate. **Scope:** first productivity/carrying-capacity change in the [root-food-economy plan](PLAY_37_ROOT_FOOD_ECONOMY_PLAN.md). The earlier PLAY-38 addition of a second farmer + courier increases supply but also increases hungry mouths. A real wagon with finite loads can improve food and water throughput **per existing worker**, not by creating a new person.

## Configuration and physical boundaries

Existing `SupplyCircuitConfigured` payload stays precisely unchanged for legacy one-parcel courier trips. New, **trusted time-zero only** variant adds `cargo_capacity=2|3`, requiring an already **physically initialized and owned** `cart=1` in that courier's resource balance. No vehicle, invalid capacity (bool/float/0/4), forged route or changed owner is ever accepted. The cart cannot be silently used without this recorded certificate. One courier still traverses every actual adjacent road, with normal transit times, injuries, fatigue and hunger.

The new cart circuit persists `cargo_capacity`; each picked parcel stores its precise `quantity` and debits the **actual local owner's known stock**. The courier inventory holds that much until a verified arrival at the recorded destination; the delivery reduces the courier's stock and credits destination stock **by the exact same quantity**. Delivery and pickup require a matching, authorized resource-specific reducer; one outstanding cargo parcel per courier remains the limit, and the courier cannot stack parcels or bypass a route. The pure selector considers only local stock and the courier's own remaining carrying capacity, never a distant bakery's hidden balance.

Food consignments are not edible personal inventory: consumption subtracts the **entire reserved quantity** (not just one loaf) before allowing an NPC meal. Legacy one-parcel food reservations remain exactly one.

## Version and compatibility boundary

New persisted fields and event payloads require **Schema 41, Rules 54** (previous 40/53). Current-regression pins are updated; historical versioned fixtures remain historical and must never be rewritten into new saves. Historical saves are **not silently migrated**. Until an explicitly reviewed transition mechanism exists, old-version snapshot opening is expected to fail closed, not be reinterpreted under new quantity semantics.

## Acceptance

Two actual farms, two couriers, physical cart initially owned only by Hana, finite two-water-unit well, actual one-hop water delivery, harvest→grain→bread→market via real NPCs, monetary conservation and SQLite genesis replay/snapshot. Adversarial checks: missing cart/invalid capacity, unowned and oversized/zero/negative/boolean parcel requests, cargo duplication, legacy quantity smuggling, tampered snapshot cargo count and protected courier food. Run on Python 3.10 and 3.13, plus full historical regressions on exact last commit before any merge.

**Limits:** This improvement changes physical throughput, NOT wages, distributed food access, population food requirements or genuine 7-day farm sustainability. Next work: credible crop yield/acreage with actual workers and attested water, employer-funded food and locally delivered meals, then 7-day two-village control/drought acceptance. No claim that the medieval village is now self-sufficient.
