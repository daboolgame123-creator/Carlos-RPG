# Phase 04-A/J1a — Historical original-entitlement provenance (implementation report)

Date: 2026-11-06 Baghdad time (2026-11-05 UTC)
Branch: `simulation-engine-phase-04a-j1`
Baseline: `5b37787dadd226279ed81513efd59ffcca7ade4c` on 02-H Schema24 Rules32; original base CI [42114734174](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42114734174) success, 808/808 each Python 3.10 and 3.13.

**Status pending final CI:** J1a implementation done; schema/rules and new tests added; NOT yet technically validated until the latest code SHA passes CI on both Python versions. External independent review deferred and P0 production backup/recovery OPEN.

## Precise completed scope

- A new event `PropertyTitleOriginRegistered`, allowed only at trusted bootstrap at time zero, records an explicitly accounted original entitlement to a quantity of a commodity **from known stock**. It records a site steward for site-held goods, a same-account NPC holder for personal goods, registration site/time, source balance at registration and fixed `record_kind=historical_origin_only`.
- All registration is **historical provenance**, not definitive present legal ownership, court-approved title, permission to take, theft, present ownership after transfer, or a demand for recovery. It does NOT change physical stock and cannot invent a balance.
- Registrations for the same original source and commodity may not sum to more than its known starting stock; both event-time and detached-snapshot validators check this (with original balance snapshot). Unknown, negative/boolean, forbidden counter, currency, missing steward, forged owner, duplicate event IDs and out-of-session/untrusted events fail closed.
- Existing H1–H3 inventory, witness, claim, complaint and market reducers remain unchanged. After a theft-like taking or a sale the original entitlement record stays **unchanged** as a historical record; the engine does NOT silently claim that contemporary title moved with stock. This is deliberately conservative for fungible goods.
- New `property_title_origins` world collection; Schema **25**, Rules **33**, previous Schema24 Rules32 world intentionally rejected unchanged (no migration).
- CI feature-off historical parity scripts exclude ONLY the new empty collection. Separate tests verify seven-NPC physical taking, market sale, failure rollback, forged snapshots, double-registration, depletion after historical registration, and event-store full replay.

## Open items — still essential for real property-rights J1

- **J1b (NOT IMPLEMENTED):** tracing fungible lots, custody allocation on ALL commodity movements (market sale, taking, help transfers, food consumption/production). Without this, cannot identify a particular loaf after mixing or track CURRENT title.
- **J1c (NOT IMPLEMENTED):** title transfers, permissions/grants/revocations, bailment and leases, positive evidence of authorization, honest third-party buyers, loss and restoration of rights.
- No laws, court, culpability, judicial verdict, fine, seizure or autonomous legal decisions; 04-A/J2–J5 remain proposals.
- Internal command-capability is not user authentication; AI/player requests never receive free access to world state. Independent review and P0 backup/recovery OPEN. Do not import Carlos's real fictional state or modify main.

## Technical check

The CI code SHA and final `passed` count must be added only after inspecting the actual latest green run. Never mark this stage APPROVED from CI alone.
