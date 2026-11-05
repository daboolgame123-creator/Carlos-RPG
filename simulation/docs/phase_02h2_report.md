# Phase 02-H2 — Witnesses and unproven property claims (technical report)

**Date:** 2026-11-05
**Branch:** `simulation-engine-phase-02h`
**Code checkpoint:** `ff2d9b87f91004a1155397debe8fc74b8cc38c52`
**Evidence:** [CI 42108021281](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42108021281) **SUCCESS — 787/787** on both Python 3.10 and Python 3.13.
**Status:** `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN`. **Phase 02-H is not closed**: 02-H3 complaints are pending.

## Implemented
- `PropertyTaken` can optionally carry a **trusted, explicit** set of witness IDs, captured inside the **same atomic event** as the physical transfer. Witnesses must be distinct real NPCs, physically present at the taking site, not traveling, and not the actor. Presence alone NEVER implies noticing the act; only an explicit captured witness receives a persistent first-hand `property_sightings` record.
- The witness record links to a real taking ID and stores the exact actor, source holder, commodity, quantity, site and logical time. It cannot be backfilled through a new event later. The global engine event store remains privileged internal truth, not a shared NPC belief.
- `PropertyClaimFiled` records a claimant's explicit `loss`, `ownership` or `accusation` assertion as `unverified`, with **no** stock movement, guilt finding, penalty or restitution. False or mutually contradictory accusations coexist.
- An actor may cite a real taking ID ONLY when they were the taking actor or have that taking in their own persisted witness sightings. A claimant can report an apparent loss without knowing the taking ID. Rumor and other NPCs' private evidence do not become the claimant's own firsthand observation.
- The optional `personal_property_evidence` projection returns only an actor's **own** sightings and claims. Future player gateway / institution interfaces must enforce their own authenticated access controls; the internal `WorldState` is **not** public.
- New `property_sightings` and `property_claims` persisted projections, independently trusted `claim_authorized` capability in SQLite command provenance, Schema **23** / Rules **30**. Reject prior Schema22/Rules29 worlds without mutation; no automatic migration.

## Verification
- Seven-person disposable village: unseen taking leaves all bystanders uninformed; one explicitly nominated real witness alone receives evidence; remote, fake, duplicate and self-witness attempts roll back; false allegation against an innocent character coexists with a separate first-hand witnessed account; no accusation mutates inventory.
- Loss without culprit/taking ID works; an unwitting claimant cannot cite a secret taking; unprivileged direct event is rejected; duplicate claim ID cannot refile.
- `simulation/tests/test_property_02h2.py` adds **14 tests** (including parameterized adversarial cases); combined **787/787 per Python** with historical regression and parity checks.
- CI also creates a genuine H1 Schema22/Rules29 world, confirms H2 refuses it and leaves the file unchanged, and retains older compatibility gates. Historical semantic comparisons exclude only the new empty opt-in projections.
- No free-text semantic interpretation, auto-detection, stealth, testimony confrontation, judicial conviction or NPC autonomous theft.

## Limits and risks
- A signed local `witness_ids` set is an **explicit trusted simulation input**, not a real vision/hearing/detection engine. `WORLD-GAP-006` tracks attention, visibility and stealth, with tests before advanced danger simulation.
- Existing inventory reflects **physical holding** and source history, not conclusive legal title. `WORLD-GAP-007` tracks custody versus property rights before restitution/enforcement.
- The snapshot validator checks consistency; **event provenance and original presence** require trusted append/replay/verify, not blind trust in a detached snapshot. P0 independent protection remains open.
- `WORLD-GAP-001..007` remain registered and open. 02-H3 complaint intake is next. No changes to main or original Carlos story files. The independent reviewer must assess this exact code checkpoint before formal APPROVED/CLOSED.
