# J1c2a adversarial follow-up — analysis and pending evidence

Date: 2026-11-06 (Baghdad)
Branch: `simulation-engine-phase-04a-j1`
Initial validated code baseline: `ac0eed8b0e34036cae14c302f2b6dcadb8df6b62`
Original CI evidence: [42131594796](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42131594796) (889/889 each Python 3.10/3.13).
This is **self-review and new unverified test source**, NOT an independent external approval.

## Analysis BEFORE changes

Reviewed `registered_claims.py`, `rights.py`, `store.py`, the J1c2a implementation tests and review request. Invariants: quantity conserved per historical origin; open proposals only reserve; acceptance requires named recipient and local proposer; neither assignment nor physical sales confer legal title; replay must be authoritative over a snapshot. Trust boundary: internal actor identifiers and the `claim_transfer_authorized` capability are privileged and are not network-level authentication.

The five commits from original validated code SHA to reported `e239638cc1fa` were documentation changes only, confirmed with GitHub compare. No proof of a new code regression in those commits.

## Added targeted probes

`simulation/tests/test_adversarial_registered_claims_04a_j1c2.py`:
1. Two valid reserved offers, accepted in reverse lexicographic ID order, conserve original quantity.
2. Recipient cannot transfer a claim while an offer is still pending and unaccepted.
3. Acceptance exactly at expiry is rejected while the expired reservation no longer blocks a new offer.
4. A rehashed forged snapshot containing an unbalanced beneficiary fails validation and cannot be loaded.
5. An internally coherent forged snapshot that replaces Salma with Nora across offers, receipts and balances may pass structural validation, but `SQLiteEventStore.verify()` must reject it by comparing against genesis replay.

These are regression probes, not evidence of successful execution. Tests need `pytest` against exact HEAD on Python 3.10 and 3.13; inspect failure traces and fix any actual regression before marking J1c2a reviewed.

## Verification blockers

- Connector lookup of commit-specific workflow runs returned no runs; this endpoint is documented as filtering to pull-request-triggered runs, so **an empty result is NOT proof that GitHub Actions did not run**.
- Direct local git clone failed due to unavailable DNS/network access to github.com.
- No independent reviewer has signed off; production backup/recovery P0 remains open.

## Decision gate

J1c2a stays **TECHNICALLY_VALIDATED (on historical code SHA) / NEW ADVERSARIAL PROBES UNEXECUTED / EXTERNAL_REVIEW_DEFERRED / P0 OPEN**.

Do not implement J1c2b until new probes and required independent review have recorded passing evidence. The next task begins with analysis, not code.
