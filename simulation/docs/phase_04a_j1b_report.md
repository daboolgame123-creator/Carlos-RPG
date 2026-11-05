# Phase 04-A/J1b — physical custody trace with explicitly unknown mixing

**Date:** 2026-11-06 Baghdad time (2026-11-05 UTC)
**Branch:** `simulation-engine-phase-04a-j1`
**Code checkpoint:** `82332a7c5f958a113d09d2924ae4fd6bedddcb7a`
**Proven test result:** [GitHub Actions 42121040731](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42121040731), **SUCCESS: 841/841 tests each** on Python **3.10 and 3.13**.
**Status:** **J1b TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN.** Not independently APPROVED or production ready. **J1c NOT IMPLEMENTED.**

## Why the implementation is conservative

Bread is fungible. If someone owns one registered loaf and another unregistered loaf in the same generic inventory account, transferring one loaf does not identify which physical loaf was transferred. Assigning an arbitrary origin would be a fabricated assertion and could later cause a false judicial claim.

This module only tracks **physical provenance/custody**, not whether someone has a legally valid right to keep, sell, or take the item. A person can hold stolen bread, and the old original-entitlement registration does not change into legal title at a sale.

## Actual implementation

- J1a `PropertyTitleOriginRegistered` now creates a separate `property_custody_lots` record at the same trusted, zero-time bootstrap event, tied to the same verified original stock/quantity. No other records or balances are automatically labeled. Any unregistered initial stock stays untraced.
- Each lot maintains `original_quantity`, `known_holders` with concrete certified held quantities, `unresolved_quantity`, and `exited_quantity`. Their sums ALWAYS equal the original registered quantity. `unresolved` is unknown present location/status, possibly later consumed; it is **not** permission to invent a holder.
- `reconcile_lots` runs after **every** world event reducer and compares the before/after physical balances for all currently certified holders. This means registered bread cannot be eaten, baked, given away, sold or taken while leaving a phantom certified amount in an old inventory.
- For physical transfers with known endpoints, including `PropertyTaken`, `MarketTradeExecuted` and `AssistanceFulfilled`, certainty propagates only when the source inventory for that commodity is entirely from one known origin, or the **entire source stock** is transferred. A full transfer may move multiple origins together without guessing.
- `MarketTradeExecuted` considers both commodity movement and a possible second **bartered commodity payment in the reverse direction**; copper remains outside J1a commodity tracking.
- An ambiguous **partial** transfer or stock decrease from mixed/partially registered source downgrades **all** certified units there to `unresolved`. It never invents that a specific registered loaf went to the buyer, nor that one definitely remained. This loses precision intentionally.
- Recognized, provably attributable consumption or conversion (`NPCFoodConsumed`, `ProductionStarted`, `ResourceChanged(source=consumption)`) increments `exited_quantity` and removes known held quantities. Ambiguous source removal downgrades instead. Future unfamiliar stock decreases also downgrade rather than certifying a destruction or destination.
- An internal, append-only `property_custody_moves` history records event revision, logical time, source, optional destination, origin ID, quantity and classification (`transferred`, `exited`, `unresolved`). The event-sourced log remains the provenance source of truth.
- Snapshot and internal projection validators check exact field shapes, origin identity, balance bounds, conservation of known + unresolved + exited, aggregate physical custody limits across all origins, valid transition references, nonnegative amounts and event/time bounds.
- `custody_audit` is **trusted engine-internal only**. It is not injected into NPC knowledge, exposed by player_view, or available to an LLM. No new permission grants, law, judicial decision, restitution or inventory transfer APIs.

## Adversarial test evidence

The new `simulation/tests/test_custody_04a_j1b.py` tests a seven-person village and linked modules:
1. Two original registered bakery loaves: Basim takes one. Bakery1 and Basim1 are certified, and all material stock is conserved.
2. Basim resells the taken loaf to Salma. The custody path is recorded; the original historical entitlement stays unchanged and no transfer of legal title is inferred.
3. One registered and one unregistered bakery loaf: after a one-loaf taking the origin becomes `unresolved`, not magically assigned to Basim or left at bakery.
4. Two distinct origins in the same bakery: partial taking makes both unresolvable, whereas a transfer of the entire known stock moves all origins.
5. Assistance food delivery with real NPCs and material stock moves certified food quantity.
6. Actual NPC consumption certifiably retires tracked food; starting a bakery production job retires its actual grain inputs and does not forge new bread origins.
7. Barter with bread paid by **grain** records both opposite physical transfer legs without mixing up goods/currency.
8. Feature-off world never gains invented lots or move records.
9. Forged snapshot claiming more certified units than held or than the original is rejected.
10. Snapshot/genesis replay and database reopen match. Invalid taking atomic rollback retains both real stock and movement history.
11. CI also checks genuine previous J1a Schema25/Rules33 saved world is rejected unchanged, plus historical semantic parity and all previous project tests.

**Full result: 841 passed on each of Python 3.10 and 3.13 at exact code SHA above.**

## Scope and remaining gates

- **J1c — Current legal rights and permissions NOT IMPLEMENTED.** No explicit grant/revocation, lease, disposal right, third-party bona-fide purchase, reclaiming, or current title transfer. Historical provenance and current physical holding must never be mistaken for judicial entitlement.
- **Fungible physical sorting / identifying one particular mixed loaf NOT IMPLEMENTED.** When provenance has become `unresolved`, it is never reconstructed from mere inventory counts. A future physically identifiable batch/sorting action would need real evidence and a new rules version.
- **Law, jurisdiction, notifications, courts, penalties, custody orders and enforcement NOT IMPLEMENTED.** The actor must not read omniscient WorldState to judge innocence.
- **P0:** backup and production recovery certification remains OPEN; only disposable test worlds are supported. Old Schema25 worlds cannot be opened without an independently designed migration.
- **External independent review:** DEFERRED, not APPROVED. Trusted internal actor IDs are not a network authentication layer.
- **Performance caveat:** current O(lots + movements) validation and capped movement history are suitable for seven-NPC development testing; before any long-lived/large world, profile and design explicit capacity/compaction rules that never discard authoritative events.
- No changes to `main` or the original Carlos narrative files.
