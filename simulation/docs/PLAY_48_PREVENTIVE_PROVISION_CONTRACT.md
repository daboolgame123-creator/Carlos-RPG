# PLAY-48H — Preventive, employer-funded courier food: contract decision and proof gates

**Date:** 2026-11-10 UTC  
**Branch:** `feature/play48h-preventive-provision-contract-20261110`  
**Parent:** `37a240ca9d16ae6d24740694c516189eb4041f82` (genuine PLAY-48G negative-control test branch).  
**Current state:** `PLAY48H_CONTRACT_DESIGN / IMPLEMENTATION_NOT_STARTED / PLAY48_RELEASE_NO_GO`.  
**Current implementation version:** Schema **42** / Rules **57**, unchanged by H0 analysis and its diagnostic test. No main merge, production save changes, or new NPC behavior.

## Exact problem confirmed by existing code and GitHub Actions

- Genuine 13-NPC wet-world baseline, including finite original water/food/copper, reaches 72h with 12 copper, five unsold site-owned market loaves, and both couriers incapacitated by hunger. Enabling the opt-in privately funded rescue only at 72h does **not** create an eligible local sponsor or restart any actual work at 96h. [Exact comparison CI 42821426908](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42821426908) passes on Python 3.10 and 3.13 as a **negative** result.
- `production.py` contains `ProductionWagePaid`: completed job ID + authorized on-site site-funded copper transfer + durable `work_wage` receipt. `supply.py` contains `SupplyCargoDelivered` and per-courier `deliveries` counters, but **no matching remuneration entitlement or unique wage receipt for courier services**.
- A courier's `coin_copper` is optionally an **exact-custody consignment slot**, not a personal wallet. `market.trade_receipt_allowed` correctly refuses the courier buying with that slot. The new food wage must not convert that cash into personal currency or treat a courier's consigned food as edible.
- Five market loaves at 72h are **site-owned**. Their existence is not consent, donation, personal NPC stock, free meals, or proof of a solvent employer.

## H0 executable evidence — find legitimate service proof, not a fictitious payroll

`simulation/scenarios/test_village/test_play48h_provision_preflight.py` replays the **unchanged genuine thirteen-NPC** seed through each of the first three days, with the same finite observed wet weather and SQLite reopen/verify. It enumerates the *actual* `SupplyCargoDelivered` event sequences authorized by the supply capability. Every `seq` is a unique historical service proof; the aggregate `deliveries` counter alone is insufficient to prevent paying the same service twice. The diagnostic emits funding and health checkpoints and deliberately **does not** mutate the market, auto-pay workers or claim day-four recovery. No new synthetic actors, routes, resources, or wallets.

## Recommended candidate: a genuinely sourced in-kind service entitlement (H1, not yet implemented)

| Term | Exact proposed contract |
| --- | --- |
| Employer / payer | Explicit **site owner `market`** only when entrusted by a trusted time-zero agreement; merely owning goods in the market does not authorize paying wages |
| Beneficiaries | Individually identified, pre-existing physically routed couriers `huda` / `hana` only; no player proxy |
| Source | **Real, site-owned food**, not consigned courier cargo, coins, future harvest, guessed funds, or personally owned goods of another NPC |
| Consideration | A genuinely completed `SupplyCargoDelivered` of `food` at `market` after scheduled adjacent-road transport |
| When to settle | At the market with recipient physically present, no later than an actual permitted health/transport window; no remote salary delivery |
| Quantity | Bounded, explicit units (first experimental candidate: one loaf for an eligible completed food delivery, with per-contract cap); never assume the village can afford perpetual wages |
| Proof and idempotency | A durable `contract_id`, immutable **delivery event sequence/revision**, unique payment receipt and atomic one-time redemption; a delivery is payable at most once |
| Ownership | On settlement, food transfers from the payer's real inventory/escrow into the courier's **personal** unreserved food; only then may `NPCFoodConsumed` eat it |
| Missing stock | Fail closed: no transfer, no promise of paid benefit unless already secured; a genuine unpaid obligation, if modeled later, must be explicitly represented rather than silently discarded |
| Autonomy | Once an authorized contract exists, the clock may settle it by ordinary local facts; it never manufactures authorizations, money, knowledge, or food |

### Funding choice must precede implementation

**Option A — reserved, fully funded ration (preferred contractual semantics).** At time-zero, authorize and atomically reserve actual existing market food for stated courier entitlement(s). Stock is conserved and allocated to an auditable site-owned escrow at the **same physical site**. Market offers and logistics must subtract the reserved quantity; otherwise a customer could sell or a courier could pick the pledged loaf again. Payment draws down the escrow, records the source and delivery-service proof and transfers individual ownership only at settlement. If the original market inventory cannot safely support both reserved rations *and* existing offers, the configuration must reject or the **explicit test-world market allocation** must be rebalanced from existing stock; do not add extra loaves. No unlimited reserve refill.

**Option B — on-delivery available-stock bonus (simpler, weaker).** Check real unreserved site food at each completed service and pay only if currently affordable. This is **not a guaranteed employment wage**; it cannot be described as a funded commitment in reports. Use it only if an explicitly optional contingent benefit is the intended gameplay design. If it has no stock, the operation records no payment and must not create a silent debt.

**H0 design choice:** Prefer A for signed compensation. **Do not implement until the time-zero site-offer/reservation interaction is audited.** In particular, `SupplyCargoPicked`, `MarketTradeExecuted`, local consumption, and site stock diagnostics must account for escrow; `MarketOfferPosted` cannot overcommit the same bread. Versioning and save compatibility are blockers to runtime mutation, **not blockers to these read-only proofs**.

## Projected version and save impact

Adding a durable contract/escrow/settlement state field changes the serialized world shape; assigning entitlement and interpreting settlement changes event rules. Thus the **proposed runtime implementation requires a new Schema/Rules pair** (candidate **43 / 58**, to confirm after the exact diff) and targeted old-save refusal tests. Never disguise the new contract as `ResourceChanged` or treat a missing field as an empty authorized treasury. Keep 42/57 experiments on their existing branches, refuse old saves on the new prototype until an **explicitly approved** versioned migration exists. Test `SQLiteEventStore.verify`, genesis replay, snapshot, WAL-safe backup/restore in an isolated disposable file, and mid-command crash/duplicate command rejection; P0 migration approval remains separate.

No work in H0 changes the historical event projection, serialized state, SQLite schema, or rules constants.

## Required adversarial matrix before H1 can be accepted

1. Invalid/nonexistent payer, worker, route, market site, or contract ID; unauthorized genesis agreement.
2. Zero/unknown/borrowed/consigned funds or food, oversubscription by two contracts, market sale of reserved food, cargo pickup from reserved food, one party absent.
3. Payment before service, payment for water/cash instead of contracted food delivery, fabricated delivery count, wrong courier/market/site, duplicate delivery proof, duplicate command and deliberate second payout.
4. Simultaneous real customer purchase and settlement in different orders, clock partition parity, worker hunger 89/90/100, stalled courier, expiring/underfunded reserve.
5. Copper sum and all food/escrow allocations conserved through every event; no NPC remote stock knowledge or instant movement; historical world with flag off is unchanged.
6. Full old-save refusal for changed version; genuine 13-NPC **from time zero** treatment against original negative control under **identical initial total supplies and weather**, at least 96h, preferably to seven days; measure independently attributable later deliveries **and** actual later job/sale/meal (not the policy firing only).
7. Targeted and historical full GitHub Actions on **same final commit** for both Python 3.10 and 3.13. Independent technical review disposition; do not declare external review completed.

## Closure and release boundaries

PLAY-48H is not closed merely by accepting this design, a green diagnostic or feeding one courier. PLAY-48 cannot be closed until the chosen **funded actual contract** works end-to-end on a 13-NPC from-genesis comparison, passes physical/custody/replay checks and final exact-SHA regressions; otherwise retain the *measured failure* as an honest open blocker. Seven-day permanent self-sufficiency is not claimed. `main`, production saves and P0 remain **NO-GO**, and no PLAY-49 start is authorized.
