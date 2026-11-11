# PLAY-48AA — physically earned grain-for-bread farm shipment (experimental)

**2026-11-11. State: PLAY48_OPEN / RELEASE_NO_GO.** No production release, old-world migration, approval to merge into `main` or proof of 7-day recovery.

## Why this exists

[PLAY48Y](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741) proved Huda can earn and eat **two real original farm-owned loaves** after verified water delivery, enabling 3→10 physical deliveries and +2 village meals by hour48. This one-time stocked wage ends because **no bakery→farm food lane exists**. [PLAY48Z](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028314540) audited that a bakery→farm *road exists* but the actual return parcel is **coin_copper**. Merely adding loaves to farm at clock time is forbidden. [PLAY48V genuine 96h](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657) still has 13/13 starving and zero new work/food in hours72–96 despite Hana market wages.

## Experimental barter contract

- A time-zero trusted `SupplyCircuitConfigured` event can opt-in with `farm_bread_share=true` **for one specific courier**. The existing contract, default seven-stop route, remaining NPCs, production recipes, market prices, water/rain and worker wages are unchanged.
- On the *actual physical farm→bakery leg*, **one delivered grain unit** adds exactly one bread obligation to that **specific farm**. The obligation is an integer owed-right, **not a new inventory item**, food or receipt of personal hunger relief. The payer bakery must separately have an **already baked, owned, unlisted and unconsigned bread loaf** at its local site. The bakery keeps at least one such loaf after dispatch.
- The existing physical `bakery → farm` return leg is the only eligible leg for fulfilling a bread obligation. The scheduler chooses **one** item — either the old copper remittance or a real loaf — never both. When the bakery can carry both, even-numbered rounds prefer bread and odd-numbered rounds prefer copper; shortages fall back to whichever actually exists. Cash is conserved, but may be **delayed one tour**: this tradeoff is measurable and not described as no cost.
- `SupplyCargoPicked` debits **one** loaf from the bakery and puts it into the courier's *consignment-only* cargo; `SupplyCargoDelivered` moves **that loaf** to the farm's real initialized warehouse **only after walking the bakery→farm road**, then advances `bread_share_delivered`. The courier cannot eat the entrusted loaf. In-flight goods and pending claims are strictly persisted, checked and replayed.
- All market offers, already-promised bakery offers, bakery customer food reservations and existing copper wage reserves are protected. No additional wages to Huda are authorized by transporting bread alone: her existing farm wage contract has a **hard ceiling of two already prepaid loaves**. A separate, reviewed signed contract with farm-stock reserve and real water service proof would be required to fund later Huda wages.
- **Economic uncertainty:** one grain-for-one bread is a **generous experimental barter rate**, not established sustainable accounting for milling/labor/fuel or profitable baking. If the baker has insufficient legitimate surplus the shipment must not occur; the lack of actual bread is a valid negative result. A two-grain-for-one-bread or price-based contract must be evaluated independently before promotion to canonical world rules.

## Version and exact verification

Persistence shape of the opt-in circuit changes, so this branch explicitly increments **Schema 45 / Rules 60** from the previous experimental 44/59. It does not deserialize previous worlds as current or authorize migrations.

- [PLAY48AA targeted Python3.10/3.13 CI #43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266), code SHA `4b4c8b663ead5fa5483d23e8b9dee195777d6200`: **fast two tests PASSED each Python** after fixing fixture event-order assumptions (warehouse/cash slots can be initialized later within the same trusted t=0 atomic batch). A prior run #43032616419 failed an overly early initialization assumption, not a false resource transfer. Long real 13-NPC **48h A/B is IN PROGRESS** at the same code SHA; read log `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD` for actual bread returned and real baker/market costs, do not claim any positive shipments before reading it.
- [Y2 real 96h farm wage #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) still requires checking the final independent dual-Python results and professional-income distributions.
- [Y2 historical regression #43028818527](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028818527) succeeded both Python3.10/3.13 on **previous Schema44/Rules59 code**, not current 45/60. A new **45/60** exact-head historical regression and authenticated old-world rejection remain required; do not treat old green CI as new-head green.
- No seven-day full population survival, complete sustained income, drought/insolvent merchant acceptance, schema migration or final independent security review is claimed.

## What must be shown next

1. Actual 48h bread (vs cash) arrival evidence, baker food, farm food, market sales, coin totals and work. If bread delivered count=0, reject the runtime hypothesis and diagnose real missing timing/warehouse/supply rather than inventing an arrival.
2. New 45/60 tests against tampered claim/delivery counts, booking buyer offers, duplicated pickup, missing cash depot and exhausted courier without falling back to magic.
3. Evaluate whether 1-for-1 barter starves bakery of market output and, if so, use physically fairer exchange or priced procurement; this is **DECISION_REQUIRED** before making permanent.
4. Independently test a lawful **farm employer stock→salary escrow refill** only after real farm bread arrives and an authorized signed contract exists. Huda still must earn each wage from a fresh water delivery; no auto hunger fix.
5. Actual parallel 72/96/168h and final full exact-head 3.10+3.13 regression, adverse drought/insolvency, save-version review and explicit PLAY48 closing decision. Do not start PLAY49.

