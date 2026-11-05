# Phase 02-H3 — Local complaint intake and acknowledgment

**Date:** 2026-11-05
**Code branch:** `simulation-engine-phase-02h`
**Code checkpoint:** `f102274c584f26f82d3d54e7eb42d7cad628715a`
**Technical CI:** https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42109843738 — **SUCCESS: 802/802 tests each Python 3.10 and Python 3.13**.
**Status:** `TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN`; Phase 02-H implementation slices H1/H2/H3 done, NOT independently APPROVED or production-ready.

## What exists
- An explicit time-zero trusted `ComplaintDeskConfigured` assignment, binding one unique real NPC officer to an existing site. An arbitrary NPC role string is **not** authority; appointment is persisted in event log, and changing jurisdiction/delegating shifts is NOT implemented.
- `PropertyComplaintReceived` records a known earlier `PropertyClaimFiled` once, by its real claimant physically visiting a desk while its assigned officer is physically present and available. Duplicate intake of the same claim is rejected, and entirely fabricated claims cannot be registered.
- `PropertyComplaintAcknowledged` may be issued only once by that specific assigned officer while actually present at the desk. The complainant need not remain indefinitely after physical intake. Being in transit blocks intake and acknowledgment.
- Receipt and acknowledgment never alter ownership, physical stock, claimant beliefs, the original `unverified` claim status, guilt, warrants, fines, imprisonment, or restitution.
- Private `personal_complaints` engine projection reveals only the complainant's own complaint records, never the entire institutional ledger to the world. The full `WorldState` and event log remain privileged engine data, not player-accessible APIs.
- Separate `complaint_authorized` capability is enforced only in active play sessions and recorded in the SQLite command ledger for deterministic replay. Validation checks desk assignment, exact claim-to-claimant mapping, unique claim intake, legal record shapes, acknowledgment identity/time and status. Schema **24**, Rules **31**. Genuine H2 Schema23/Rules30 worlds are deliberately rejected unchanged, not silently migrated.

## Adversarial regression
`simulation/tests/test_complaints_02h3.py` exercises seven NPCs with an assigned desk:
- False accusation delivered and accepted, but inventory and accusation status remain unchanged, and the accused never becomes guilty.
- A different claimant, remote claimant, unknown claim, and missing desk are all rejected without state mutation.
- A competing officer and any untrusted direct events cannot intake or acknowledge.
- Repeated receipt for one claim, repeated acknowledgment and invalid desk assignment cannot create a second official transaction.
- Unknown/future complaint, stale revision and local officer leaving on NPC movement route fail closed.
- Snapshot, verify, immutable event replay and private complainant perspective agree.
- The full suite, cross-version parity, and multiple genuine-old-world rejection tests are green: **802/802 each on Python 3.10 and 3.13** at CI run 42109843738.

## Known scope boundaries, risks and follow-on work
- **WORLD-GAP-008:** desk replacement, officer shifts, delegation, multiple officers, absent officer queued filing, jurisdiction and how a complaint travels between institutions are not implemented. A vacant office currently simply cannot receive complaints.
- **WORLD-GAP-006/007:** witness visibility and real ownership title remain unsolved; no conviction or legal title can be inferred from co-location, rumors, inventory, or the officer's acknowledgment.
- **WORLD-GAP-001..005:** other world-simulation gaps remain open and unchanged.
- An explicit internal trusted actor ID is **not** end-user authentication or authenticated office access; the simulation service is not a public/API endpoint. Proper authorization, independent review and production recovery safety **P0** remain required.
- Judicial dispute resolution, rights and remedies, confiscation, punishment, appeals, adversarial review of evidence, and institution autonomy require separately scoped future phases; no hidden magic enforcement in this slice.
- Original Carlos narrative files and `main` remain untouched. All tests use disposable worlds.

## Next phase gateway
Treat the **implementation** of H1-H3 as technically validated only. Before labeling Phase 02-H fully approved, obtain an independent adversarial review of the exact code commit (not merely documentation), separately close P0 production backup/recovery certification, then commit a formal closure decision. Until then `EXTERNAL_REVIEW_DEFERRED / P0 OPEN` remains visible.
