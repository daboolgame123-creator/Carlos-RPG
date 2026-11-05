# 04-A/J1c2a — voluntary reassignment of registered entitlement claims

**Design and authorized scope, 2026-11-06 Baghdad time.** Under development. Baseline J1c1 Schema27/Rules35, [green 865/865 each Python version](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42128330511).

## Critical limitation: registration is not title

J1a registration is historical testimony of an original entitlement, J1b tracks *physical* custody when knowable, and J1c1 permits a narrow physical collection. None establishes a jurisdiction's enforceable title. Thus **J1c2a transfers a quantified *registered historical claim* by mutual agreement; not the legally adjudicated property right, not stock, and not consent for collection or sale.** A buyer of stolen goods does not become automatically legally entitled. Only later J1c2b plus approved law and evidence could deal with normative title.

## Invariants

- New original registered claim ledger `registered_claim_balances[origin_id] = {original_beneficiary: quantity}`, created by the trusted original J1a event; total across accounts per origin always equals the historical registered quantity, even if a loaf is eaten, stolen, sold or mixed. **This is not a physical inventory or a court verdict.**
- Explicit two-person handshake: `RegisteredClaimTransferOffered` by current claim account/recorded site steward, selecting existing origin, named NPC recipient, bounded quantity, expiration (at most seven simulated days), at a site where both are actually present; reserves the quantity. `RegisteredClaimTransferAccepted` only by the named recipient, when both present and the offer is still open and unexpired, adjusts claim ledger atomically and creates historical transfer receipt. Offer `RegisteredClaimTransferCancelled` by its original issuer, while both are present, releases reservation. Expiration is a deterministic condition (no magical remote message), unaccepted claim never transfers.
- A recipient who has accepted may later explicitly offer their registered claim to someone else; this still does not transmit physical goods, legal title, lawfulness or permission to seize.
- Source owners can be site accounts (represented by their registered steward while acting on behalf of that site) or real NPCs. The site account remains site; no conversion to steward's personal account.
- Cap pending reservations against each account's **registered claim units** rather than physical inventory; prevent double selling a historical claim even when actual bread is missing or uncertain. This differs from J1c1's physical permission stock reservation.
- Preserve event provenance: `offer_id`, `origin_id`, origin beneficiary, giver and recipient, quantity, site, timestamps, status. Cross-check snapshot invariant by reconstructing claim balances deterministically from accepted offers and validating unique receipts/IDs. No plaintiff/narrator receives omniscient data.
- Separate event authorization `claim_transfer_authorized` (trusted + active session, persisted in SQLite `commands`, replayed), distinct from `permission_authorized`, `market_authorized` and `taking_authorized`.
- **Schema28 / Rules36**. Fail closed when loading genuine J1c1 Schema27/Rules35 saved world (byte-identical on rejection), no automated migration. Main/story untouched, P0 and external review open.

## Tests / adversarial examples

1. Adel as bakery's recorded steward offers one of two original bread-claim units to Salma; Salma explicitly accepts at bakery. Claim balances bakery1/Salma1. Bakery and Salma physical inventory do not change; J1b custody stays untouched.
2. An open offer does not transfer anything. Wrong recipient/issuer, forged direct event or distant traveler cannot accept. Duplicate/stale commands don't double-transfer.
3. Multiple open offers exceeding seller's registered quantity rejected; after one acceptance another claim cannot be sold twice, even if actual bread was sold or stolen.
4. Recipient Salma may reassign claim to Huda by an additional local agreement; conservation holds and original J1a beneficiary remains unchanged in historical record.
5. An expired offer can never be accepted; unaccepted expired reservations stop blocking valid offers. Local cancellation releases reservation; remote unilateral magical cancellation is not allowed.
6. Even if Basim physically takes or resells the registered loaf, **recorded claim balances do not change automatically**. This is not adjudication of who owns it.
7. Forged snapshots (altered balances, duplicate receipts, changed offer statuses, fabricated origin) fail structural and cross-collection validation; full replay and snapshots stable; prior-world rejection and feature-off parity green on 3.10/3.13.

## Deferred

No pricing/consideration for claim assignment, no legal-title transfer, no court, no laws, no ownership enforcement, no authority for claim recipient to force entry, take bread, revoke existing permissions or sell it as theirs; this is a narrow voluntary registration operation. J1c2b/J1c3 and all J2–J5 remain deferred. Only a separate future legal system can decide enforceability of competing claims.
