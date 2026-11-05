# Independent adversarial review request — 04-A/J1b custody provenance

**Exact code checkpoint:** `82332a7c5f958a113d09d2924ae4fd6bedddcb7a` on `simulation-engine-phase-04a-j1`
**CI:** [42121040731](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42121040731) **SUCCESS 841/841 each** Python 3.10 and 3.13.
**Status:** Review REQUESTED/DEFERRED, NOT independently performed or APPROVED. P0 still OPEN; no production save guarantees.

Review actual diffs to `custody.py`, `rights.py`, `domain.py`, workflow and `test_custody_04a_j1b.py` **independently of implementer's report**. Preserve original Carlos story and main. Report APPROVED/BLOCKED with reproducible findings and concrete tests.

## Mandatory adversarial challenges

1. A full registered bakery stock of two loaves: take one, sell one, give one; prove each certified custody ledger never exceeds physical stock; sums by origin always equal recorded J1a initial quantity.
2. Mixed unregistered and certified loaves: attempt partial transfers of 1, full transfer of stock, successive transfers through three NPCs, and mixing differently sourced origins. No arbitrary FIFO allocation or false permanent assignment allowed. Unresolved quantities must not silently reappear as certified.
3. Two registered origins of same commodity at same holder: take/sell only part. Verify BOTH origins become unresolved when identities cannot be determined, and a full entire-stock transfer can safely carry all origins.
4. Test commodity barter with two separately registered goods being exchanged in opposite directions. Both legs must be audited without mixing origin/target or inventing balances.
5. Test an NPC with registered food eating it, and production consuming registered grain. No phantom holding of physically removed goods. If mixed origin, do not incorrectly mark a specific origin as definitely consumed.
6. Test assistance delivery, market sale, taking, generic `ResourceChanged(source=consumption)`, scheduled production completion, and any other existing stock-mutating reducer. Verify the reconciliation hook cannot be skipped through direct trusted append or replay.
7. Try to forge a detached snapshot's lot holder, original quantity, unresolved/exited amounts, movement event reference/revision, or origin mapping. Test that `WorldState.from_dict()` refuses internally contradictory states. `verify()` must reconstruct movement provenance from immutable events and reject inconsistent snapshots.
8. Inject stale revisions, duplicate command IDs, invalid quantity and an event batch whose last event fails after an earlier physical transfer. No partial transfers, lot movement, or history may commit.
9. Verify schema/rules **26/34** rejects genuine **25/33** persisted J1a world byte-for-byte without implicit migration; confirm old 02-H and older cases and semantic feature-off parity remain identical.
10. Examine the trusted internal audit accessor: no player, NPC or language-model route may retrieve arbitrary custody history. Confirm no new actor-based permission grant or current legal-title inference.
11. Evaluate algorithmic cost: full-scan lot reconciliation and full validation on every world event can be O(lots + transitions) per event. Identify practical scaling thresholds and whether capped movement history could ever silently drop events (must fail closed).
12. Can historical origins be forged with inconsistent original site balances, or does the J1a trusted bootstrap plus J1b lot initialization and event replay protect against it? Consider untrusted `bootstrap=True` beyond authenticated engine boundary.
13. Clarify when known per-origin *quantities* are not distinguishable individually: even when a deterministic aggregate source is provably complete, a certificate of provenance is NOT a legally enforceable title or observation accessible to nearby NPCs.
14. P0 (durable backups, independent recovery tests) and authenticated access to internal actors remain unapproved. Do not label J1b CLOSED or legal rights solved from CI alone.

A separate reviewer should run its own probes and cite commit SHAs and CI, and create regression tests for any blocker. This review-request document is not proof that an independent review occurred.
