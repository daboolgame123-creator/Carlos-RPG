# PLAY-48H1 — Versioned, real-food courier wage prototype

**Status:** `H1_PROTOTYPE_UNVERIFIED / PLAY48_RELEASE_NO_GO`  
**Branch:** `feature/play48h1-funded-courier-provisions-20261110` from H0 `23729ca3b42fbd21eec855278fe3deeda614c0d3`.
**Experimental versions:** Schema **43** / Rules **58** (not production-supported; no migration implementation). `main` unchanged.

A trusted operator signs a one-time employer contract at **t=0**, reserving 1–3 actual market loaves per physical courier, rejecting oversubscription and duplicate workers. Reservation DEBITS the ordinary market food balance into employer-owned escrow, preserving total food and barring all subsequent ordinary sale/collection of reserved units. The counterparty has no pre-existing entitlement before configuration. Each real `SupplyCargoDelivered(food)` at the market may earn at most one personal loaf, only if the exact same SQLite command contains the immediate subsequent `CourierProvisionPaid` event, all with trusted supply capability, real courier route and current delivery count. Receipt permanently records service count, time and recipient balance. Unpaid escrow remains site-owned; no copper, fictional wage, debt, remote transfer or food creation.

The engine's ordinary courier planner may emit the payment **only directly after a real delivery**. Post-delivery consumption remains the independent existing `NPCFoodConsumed` event. Historical defaults have no contracts; with this newer version legacy 42/57 worlds are refused until a separate, reviewed migration is explicitly authorized.

## Proof limits

Targeted CI aims to verify the actual 13-person genesis with **three market loaves**, reserve one for Huda and one for Hana, then observe **real early physical services** and recorded wages through day one. This reduces immediately saleable bread to one, potentially displacing legitimate buyer demand; that externality must be measured. Additional hostile tests require denial of four-unit obligations, duplicate/unknown workers, counterfeit service proofs, and genuine 42/57 saves. A green early test **does NOT establish post-72h work or sustainable wages**.

The next gate is an identical-input (three original market loaves, twelve copper, bounded rain) controlled 0→96h or seven-day comparison against the original. Audit stock+escrow+consumption+grain transformations; retain an explicit negative conclusion if activity still stops. Before any PLAY-48 closure, exact-final-head Python 3.10/3.13 targeted and historical full suites, replay, compatibility, independent review disposition and documented risks are mandatory. P0, real-world long-lived saves and `main` remain NO-GO.
