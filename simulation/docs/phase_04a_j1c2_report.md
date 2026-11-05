# Phase 04-A/J1c2a — Voluntary assignment of registered historical claims

Date: 2026-11-06 Baghdad time (2026-11-05 UTC)
Branch: `simulation-engine-phase-04a-j1`
Base: J1c1 Schema27 Rules35, CI 42128330511, 865/865 each Python 3.10 and 3.13.

**Status at writing:** CODE IMPLEMENTED / FULL TEST VALIDATION PENDING / INDEPENDENT REVIEW DEFERRED / P0 OPEN. Record exact newest CI SHA and counts ONLY after verified green on BOTH Python 3.10 and 3.13.

## Actual implemented scope, not legal title

- A historical J1a entitlement record receives a separately conserved `registered_claim_balances` ledger. Each registered origin's claims start with its original beneficiary, and total claim quantity always remains the original registered quantity. **No current lawful ownership is asserted.** The physical custody lot, material resource account and any J1c1 collection permissions remain independent.
- Explicit two-party handshake: `RegisteredClaimTransferOffered` by a present current registered-claim account holder (or the permanent registered steward for site-held origin), addressed to a present named recipient, quantity and finite expiry. The open offer only reserves the claim quantity and moves NOTHING.
- `RegisteredClaimTransferAccepted` only by the named recipient when both parties are genuinely present, when the offer is open, unexpired and backed by remaining recorded claim quantity. Only **then** the registered claim balances change atomically and a durable historical transfer receipt is recorded. The recipient can subsequently make a second genuine offer to another NPC.
- `RegisteredClaimTransferCancelled` by the original local issuer when recipient is also present, releasing reserved recorded quantity. Expired unaccepted offers release their reservations automatically at the current logical time, without inventing a remote message.
- An existing physical purchase, non-consensual taking, food consumption, gift or robbery does NOT automatically alter these registered historical claims. No owner can legally seize bread from this record alone; the judiciary and adopted law are deferred.
- All three new events require an independent trusted `claim_transfer_authorized` capability and active session, stored with the command and checked on full replay; no new public endpoint. Snapshot validators prove conservation and compare final balances to actual accepted receipts. Malformed issuer/recipient, remote travel, duplicate/expired IDs, over-reservation and forgery are rejected atomically.
- Schema **28** / Rules **36**. A real J1c1 Schema27 Rules35 predecessor is refused unchanged; no automatic migration. `main` and narrative scene unchanged.
- Seven-NPC new tests in `simulation/tests/test_registered_claims_04a_j1c2.py`: offer without transfer, acceptance, replay/backup, resell of claim, real sale/taking without auto-title, overbooking, fake issuer/recipient, traveling recipient, cancellation, expiry, malformed snapshot, untrusted append, stale and duplicate command, bad batch rollback.

## Deferred

- **J1c2b:** *legal enforceability* of current title, priority of conflicting title claims, title defects and good-faith buyer, consideration/payment for rights assignments, mistaken identity, and physical allocation of fungible bread after mixing. Neither this phase nor J1c1 proves valid current property title.
- **J1c3:** scoped rights for holding/selling/delegation, communication beyond physical co-location; independent entitlement adjudication.
- **J2–J5:** courts, laws, jurisdiction, sanctions, restitution and police power.
- **P0 and external independent review remain OPEN**. Proven CI alone cannot close them. No production live world imported.

## CI evidence

Pending verified HEAD run: https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42131594796, code checkpoint ac0eed8b0e34036cae14c302f2b6dcadb8df6b62. If failed, document actual failed probes and fix them instead of marking success.
