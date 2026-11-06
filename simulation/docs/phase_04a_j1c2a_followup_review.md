# Phase 04-A/J1c2a — follow-up adversarial code review

**Date:** 2026-11-06 (Baghdad). **Reviewed code base:** previous head `b437ea73ca7fca3da60d9b4cd21824d23304203a`, plus independently authored extra probes at `be66bb0d4a5ad04d2badbe6eefce26ce630e0b91`.

**Outcome: INTERNAL ADDITIONAL TECHNICAL REVIEW PASSED / EXTERNAL INDEPENDENT SIGN-OFF STILL DEFERRED / P0 OPEN.**
This is an assistant-authored additional adversarial review, not a claim of external organizational independence or a production readiness approval.

## Independently verified CI evidence
- [Main full simulation CI, run 42137905742](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42137905742) — Python **3.10: 897 passed** (job 127630609863); Python **3.13: 897 passed** (job 127630610099).
- [Adversarial + full regression CI, run 42137905809](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42137905809) — **SUCCESS** on both Python versions.
- Prior adversarial run [42136054992](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42136054992) showed 5/5 specialized probes and 894/894 complete tests on both interpreters.
- New test file: `simulation/tests/test_j1c2a_independent_probe.py`, 3 additional probes, no change to the production claim algorithm.

## Specific adversarial results
1. Three-hop registered historical claim from bakery → Salma → Huda → Nora with offer IDs intentionally out of alphabetical chronology. Final recorded original quantity conserved; no physical bread moved, no J1a entitlement history rewritten, no J1b custody history changed; durable full event replay consistent.
2. Only the designated actual recipient can accept an offer, and only its actual proposer can cancel. Wrong actor cannot transform balances or the pending agreement; failed attempts leave world state unchanged.
3. Bakery bread fully physically taken away, then a separate registered historical claim can still be assigned by agreement. Physical stock remains depleted and its custody history remains unchanged. This proves **claim record is not proof of present possession or power to seize goods**.
4. Previously independently authored J1c2a specialized probes verify two simultaneous offers with reverse acceptance identifier order, rejection of premature resale by unaccepted grantee, exact expiry, corrupted snapshot with recomputed hash rejection, and full event replay catching an internally consistent forged snapshot.
5. The full existing simulation suite, old-rule version rejection and established parity workflows continue green.

## Reviewed boundaries
- `registered_claims.py` requires source account representation, named recipient, real co-location, bounded quantities, unexpired accepted terms, separate `claim_transfer_authorized` and an active session. No stock mutation in offer/accept/cancel reducers. Reserved open offers and final claim balances are checked; accepted receipts must correlate with offers. SQLite store transactionally rolls back invalid batches; deterministic replay re-checks authorization flags.
- No legal title, court-enforceable right, judicial guilt, court, police power, or collection permission is granted merely by claim assignment.
- A caller already inside the trusted Python engine can supply actor IDs and capability flags. **No externally authenticated caller boundary exists**, so this review cannot certify secure public RPC/API use.
- Snapshot shape validation does not prove historical consent by itself; the immutable event replay and check against snapshots are necessary. The engine is a trusted local prototype, not a cryptographically authenticated multi-party ledger.

## Open observations and gates
- **REVIEW-J1C2A-01 / HIGH before exposing network or untrusted player commands:** add independent actor authentication and capability issuance, prohibiting arbitrary actor-ID submissions. Known architectural trust boundary; not a new failing regression in current trusted in-process tests.
- **REVIEW-J1C2A-02 / MEDIUM before long-lived scale:** quantify O(number-of-offers + claims + event replay) projection costs and define safe archive/compaction if the 1000-offer bound is reached, without losing authoritative events.
- **REVIEW-J1C2A-03 / LAW GATE:** binding current legal title, good-faith purchases, restitution, conflict-of-rights law and priority are NOT modeled. Transfer is a *recorded historical claim assignment*, not an enforceable title.
- **P0 OPEN:** independently verified production backup/recovery and version migration not approved. Genuine previous version refusal is explicitly tested; no migration.
- **EXTERNAL REVIEW OPEN:** a genuinely separate reviewer still needs to sign a report before this can be called independently APPROVED. Do not change project status solely on the strength of this assistant's review.

## Decision
Accept **internal technical validation** of J1c2a for further *design research*. Do **not** mark J1c2a externally APPROVED and do not start J1c2b executable court/title rules until its own feasibility and law gates. No main branch or Carlos original narrative files changed.
