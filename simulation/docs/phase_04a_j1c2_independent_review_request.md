# Independent adversarial review request — 04-A/J1c2a historical claim assignments

**Candidate exact code SHA:** `ac0eed8b0e34036cae14c302f2b6dcadb8df6b62`
**CI evidence:** [42131594796](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42131594796) — 889/889 SUCCESS each Python 3.10 and 3.13.
**Status:** TECHNICALLY_VALIDATED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN. The present document is a request, **not a signoff**.

Please review `simulation/src/carlos_sim/registered_claims.py`, `rights.py`, `domain.py`, `store.py`, test `test_registered_claims_04a_j1c2.py`, and the exact changes in the CI workflow. Reviewers should write their own reproducible probes, not only repeat the implementer's assertions.

1. Can a random NPC, a wrong site steward, traveler, absent recipient, non-owner or player-controlled entity offer/accept/withdraw another person's registered claim? What is the actual authenticated boundary (not just in-process actor ID)?
2. Can two pending agreements double-reserve one original registered quantity? Can expiration/cancel/accept events race in the same logical second and create an overdraw or duplicate receipt?
3. Can a recipient refuse a deal and still have their claim balance changed? Does a pending, revoked or expired offer have any effect other than reserving a bounded registered claim?
4. Once a claim has transferred, can the recipient reassign only its actual registered quantity while the seller can no longer double-assign it? Test several transfers among different NPCs, with offer IDs ordered differently from event chronological IDs.
5. Does a real physical sale, taking, gift, usage, food consumption or J1c1 collection-permission redemption ever silently transfer registered claim units or generate legal title? It MUST NOT.
6. Can a malicious snapshot alter balances, claim provenance, accepted receipt quantities/timestamps, or statuses to invent a beneficiary or hide double-reservation? Require `WorldState.from_dict()` to reject internal contradictions and full `SQLiteEventStore.verify()` to reject forged replay/snapshots. Consider how the snapshot validator reconstructs balances using ordered accepted receipts.
7. Does a batch with a valid offer followed by a forged acceptance roll back all state? Test duplicate command IDs, stale revisions, bool quantities, overflow, expired proposals, absent origin.
8. Does a genuine Schema27 Rules35 prior world refuse under Schema28 Rules36 without changing its SQLite bytes? No auto-migration, and feature-off parity unchanged.
9. Audit all new in-process API and event capability paths. A caller who controls `claim_transfer_authorized` or engine-private WorldState is already privileged; do not claim public authentication or secure network access.
10. Test long-lived world capacity (MAX_OFFERS), replay scaling, rollback under max constraint, and initial claim balance creation during J1a authenticated bootstrap.
11. **Legal priority not modeled:** a recorded claim transfer is neither current legal title nor authorized collection, coercion or judgment. A forged/fraudulent physical sale and a buyer in good faith remain legally unresolved, and the real world law has not been approved. No courts or sanctions introduced.
12. P0 recovery and independent review remain open; label actual blocker/fix/evidence in a separately authored report. Do not mark APPROVED solely from CI.

Review status must remain **EXTERNAL_REVIEW_DEFERRED** until a genuinely independent reviewer completes and records test evidence.
