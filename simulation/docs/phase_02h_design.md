# Phase 02-H — Theft, ownership disputes, complaints (design only)

Date: 2026-11-05
Branch: `simulation-engine-phase-02h`
Base: `c20b1a3d35a8eb5ca173880c28d24d45b7ea1bcd` (02-G docs green, CI 42103103814).
Status: PROPOSED DESIGN — NOT IMPLEMENTED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN.

## Purpose and non-negotiable invariants
Introduce a minimal, event-sourced **physical taking**, **claims**, and **local complaint intake**, without magical detection, forced guilt or invented justice. Only the simulation's authorized events alter resources or legal/administrative status. Existing economic ownership/stock and 02-G hearsay remain separate from objective evidence. This phase is a *small institution prototype*, not a court simulation.

1. The owner/keeper, actual holder, claimant and reporting witness are separate concepts. Mere allegation never changes true stock ownership, location, debt, or legal guilt.
2. A theft-like taking is a physically executed, atomic, source-account to destination-account transfer. Both accounts must exist, be specific, and contain sufficient actual stock. Do not manufacture goods, copper, an owner or a receipt.
3. A taking can succeed unseen. Observation requires independently checked physical co-location and a contemporaneous event / explicit perception rule, not global access to the event log or later gossip. A witness can misinterpret what happened; source/event provenance is preserved.
4. Claims and complaints are assertions of identifiable actors; they are not rulings. Rumors, absent witnesses, mismatched times, anonymous invented evidence, and untrusted player text cannot establish guilt.
5. Any institutional response is limited to authorized local **recording/acknowledgment/requesting information** only. No fines, restitution, confiscation, arrest, forced testimony, property title adjudication or imprisonment in this slice.
6. Persist and replay deterministically in logical time; transaction rollback must leave every balance and record unchanged on failure. Explicit opt-in / feature-off parity against real 02-G checkpoint. Incompatible saved worlds rejected unchanged; no silent migration.
7. No edits to `main`, original story files or long-lived worlds. P0 and independent approval remain open.

## Proposed minimal domain and authorization

- `TakingAttempted` is NOT necessary as a mutation by itself; denied actions return a rejection with no event or balance changes. An accepted `PropertyTaken` records immutable `taking_id`, actor, source-holder, destination-holder, item kind, quantity, physical site, logical time, before/after ledgers, and a declared `permission_basis` (e.g. none, express grant). Calling an act theft is a **character/institution interpretation**, not a reducer verdict.
- Permission is evaluated against recorded owner/keeper/explicit grants where represented; if the required entitlement is unknown, reject with an explicit reason rather than treating unknown as no consent. A permitted transfer should use existing market/gift pathways; this action is reserved for `no_grant_recorded` and must not imply any adjudicated crime.
- A physical taking requires the actor's real presence at the exact source site, not in transit or acting elsewhere; item balance must be sufficient. Recipient of taken stock is the acting character's account; no taking directly into arbitrary third-party accounts.
- `TakingObserved` is a separately generated, provenance-linked local observation for an actual available witness present **at the moment of execution** under the existing perception constraints. Start with explicit, conservative witness assignment; do not assume that all bystanders notice. No witness can observe remotely, while traveling, or retrospectively.
- `PropertyClaimFiled`: actor identity, referenced item/holder/optional taking, claimed basis, stated narrative (typed, bounded), timestamp and site; claim is **unverified**. Support mutually contradictory claims without changing authoritative ledger.
- `ComplaintFiled`: complainant, named subject if known (may be unknown), referenced claim/taking and optional personally obtained observation, local intake location and receiving office/agent, complaint state `received`. It must be possible to lodge a complaint without knowing the culprit, while knowing that a loss occurred. Explicit locality, identity, and capability checks. No automatic public disclosure of private complaint.
- `ComplaintAcknowledged` (optional small institutional step): a configured agent acting on behalf of an actual registered institution confirms receipt; state `acknowledged`, **not proven/closed/resolved**. No auto-conviction, automatic recovery or penalty.
- Keep viewpoint-specific accessors: private claim/complaint details for parties and authorized intake, witnessed takings for actual witnesses, public claims only through lawful local communication. An event in global audit history is not knowledge available to every NPC.

Exact event shapes, reducer guards and existing inventory/account APIs MUST be inspected in the source before implementation. Field names above are conceptual, not claims of current code.

## Delivery slices

1. **02-H1 — Physical taking only:** inspect stock + location + capability guards, implement one atomic unauthorized-taking path and proof of conservation, fail-closed on unknown owner/entitlement. No NPC autonomous stealing.
2. **02-H2 — Evidence/claims:** witnessed/not-witnessed distinction, witness-source provenance, conflicting actor assertions, no inference of guilt.
3. **02-H3 — Complaint intake:** an explicitly configured local office/agent acknowledges a filed complaint but cannot order seizures or punishments. Keep workflow minimal.
4. Phase report, adversarial review request, roadmap and changelog only after the respective code/CI checkpoints. Do not label any slice APPROVED without independent review.

## Adversarial acceptance tests (7-person disposable village)
- A worker takes one owned loaf at a physically reachable site: source -1, worker +1, total unchanged; a later legitimate sale cannot sell that same unit again.
- Attempt to take 2 when only 1 exists, wrong account, invented owner, untrusted capability, in-transit actor or remote source: rejected with unchanged snapshot/event digest/stock.
- No witness at location: actual physical taking persists, but no bystander learns it. Witness at site who explicitly notices gets only their own attributed observation.
- Complaint naming an innocent person does not prove guilt; two contradictory claims coexist without moving inventory.
- A rumor of theft (02-G) may reach one listener and not another; neither hearsay nor a complaint creates a `PropertyTaken` or a guilty verdict.
- A local officer can acknowledge a genuine filed complaint, but a remote actor/unauthorized official cannot; filing/acknowledgment does not award restitution.
- Save/reopen/replay/rollback/duplicate-id tests, deterministic event ordering, legacy 02-G feature-off parity and real Schema21/Rules28 saved-world rejection without mutation (if persistence versions change).
- Python 3.10 and 3.13 CI pass; report exact SHA and verified test count before technical validation.

## Open dependencies and bounds

WORLD-GAP-001 (emergency action interruption), 002 (employment and wages), 003 (housing property/tenancy), 004 (natural-language interpretation), and 005 (reputation-sensitive trade) remain OPEN. Housing titles and rent are explicitly out of scope; current stock/keeper relationships must not masquerade as land titles. Any newly discovered essential gap gets a stable WORLD-GAP identifier, priority, dependencies, target phase, and acceptance criteria immediately.

Before coding confirm existing market `keeper_id` semantics, entity control and physical-presence checks, balances for location stock vs NPC personal stock, capabilities/session boundaries, event scheduling, invariant validator and persistence version gates. Do not synthesize a new law-enforcement framework to fill missing data.
