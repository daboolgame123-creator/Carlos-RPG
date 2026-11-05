# Phase 04-A/J1b — Conservative custody provenance for fungible stock (design)

Date: 2026-11-06 Baghdad. **Design for J1b only**, implementation follows on isolated `simulation-engine-phase-04a-j1` branch.
Base: J1a Schema25 Rules33, CI 42117706287, 826/826 on Python 3.10 and 3.13.

## Core epistemic constraint

Two bread units look alike; a bare "bread -1" does NOT identify which registered origin supplied that loaf. Even if a market event proves a real physical transfer, it does NOT prove the legal title moved. Never assign an arbitrary historical origin to a buyer when different origins or unknown food were mixed at the source.

## Chosen implementation

- Bootstrap registration from J1a creates one **initial physical custody** record per explicitly documented original quantity, with source holder and original origin reference. Unregistered starting stock remains untraced; no retroactive creation.
- Engine-local, append-only movement audit and bounded per-origin `known_holders`, `unresolved_quantity` and `exited_quantity`. Every original unit always belongs to exactly one of these quantity categories; an `unresolved` unit has no currently certified holder.
- Reconcile **every reducer's actual stock delta**, not just market/taking, so consuming, cooking, helping, producing and future stock mutations cannot leave phantom certified units.
- For actual transfers between known holders (market sales, taking, assistance gift), custody is certified only if all source stock of this commodity came from **one documented origin**, OR the transaction took the source's **entire** stock (then all known origins move with it). Unknown units may accompany full transfer, but no origin is manufactured for them.
- For partial removal from a mixed or partly unregistered stock, downgrade **all currently certified units at that source** to `unresolved` rather than pretend to know which physical unit departed. Their historical source remains in the event log; their *current* location is unknown.
- For physically consumed/converted material (NPC food consumption, production input, ResourceChanged consumption), record `exited_quantity` only if provenance is unambiguous; otherwise downgrade to unresolved. For any unsupported future decrease, downgrade, never invent a consumption or a transfer.
- Incoming new units without registered origin never receive a fabricated origin. When they mix with certified stock, existing known quantities remain known to be somewhere at the holder, but partial outgoing amounts become ambiguous.
- This tracks **physical custody evidence**, NOT current legal ownership, individual item serial numbers, consent, adjudication or owner rights. No new NPC knowledge or player views.
- Snapshot validator checks each lot's origin/commodity/quantity, sum of certified+unresolved+exited units, holder balances, per-holder aggregate across origins, movement record shapes/time/revisions and bounded IDs. The full event log's replay is the source of provenance truth; a standalone snapshot cannot cryptographically establish who moved it.
- Schema **26** / Rules **34**. Real J1a Schema25 Rules33 saved worlds rejected untouched; no migration. Feature-off semantic parity retains identical choices and physical stock.

## Acceptance probes (seven NPCs)
1. Bakery has exactly 2 registered bread: Basim takes 1. Certified location bakery1, Basim1; source physical bakery1. Both source and target quantities conserve.
2. Basim sells his registered loaf after listing it and a buyer receives it: exact physical lineage continues. Neither sale nor possession proves legal title.
3. Mixed bakery (2 registered + 1 unregistered): Basim takes 1, provenance of bakery's original 2 becomes *unresolved*, never assigned automatically to Basim or falsely retained at bakery.
4. Two distinct origin lots at one holder: a partial sale/taking makes each lot's provenance unresolved. Full sale of entire holding transports all known origins without guesses.
5. Registered food eaten or recipe input consumed: unambiguous quantity becomes exited; mixed food is unresolved. No currently certified food remains after eating.
6. Assistance/gift between NPCs moves traced quantity when unambiguous. Invalid remote/duplicate IDs/revision/missing balances still reject atomically.
7. Forged snapshot adding phantom custody, exceeding original lot total, or pointing to nonexistent origin rejected. Replay/restore/snapshot coincide.
8. Historical 02-H/04-A/J1a feature-off events preserve same semantic state besides new empty collections; Python 3.10 and 3.13 full green CI.

## Explicit future gaps
- Tracing identifiable *individual* loaves or recording physical sorting/separation of mixed stock requires a new validated action. Unresolved lineage is deliberately not later re-certified by guessing.
- Current civil title and grants/permissions belong to J1c, not J1b. Legal guilt, courts, confiscation and sanctions remain out of scope.
- Independent review and P0 production-recovery certification remain open.
