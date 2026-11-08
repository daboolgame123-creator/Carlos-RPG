# PLAY-41 — funds flow from a real sale to a real farmer's wage

**Causal finding:** In PLAY-39, seven physically baked loaves remained idle while nine NPCs starved. PLAY-40 proves a 12-coin closed economy can return **six real customer-paid copper** from the market, physically through bakery, to the actual eastern field via an authenticated courier. This phase establishes an equally physical and traceable **final transfer to the employed worker**, not new money.

## Contract and authority

A production recipe can opt-in to a time-zero `wage_coin` of **1 to 5** copper per genuinely completed production job. The employer must have an already-initialized on-site coin ledger. This signed, trusted time-zero term cannot be added at runtime or claimed by an untrained NPC; regular recipes have no wages and retain their original persisted shape.

The single privileged `ProductionWagePaid` event requires an active session and existing production capability, *no impersonated actor*, the original agreed rate, the actual completed job, the real worker co-located at the workplace (not travelling or double-working), and a sufficiently funded **site-owned copper** balance plus a known worker balance. It atomically debits the real employing site and credits the employee. The completed job stores an immutable one-time `work_wage` receipt (timestamp, worker, workplace, amount and before/after balances) in its event-derived record. Replaying/snapshotting yields precisely the same finances. A second payout to that job, fake job, unknown source, changed price, source overdraw, worker forgery or unauthorized event must fail without changing state.

When a site is **unfunded**, legitimate completed work remains genuinely **unpaid**. This is an adverse-world outcome and MUST NOT be treated as successful job payment. No automatic cash minted, no remote account credit, no hunger override, no charity masquerading as wages.

## Compatibility and next gating

**New optional stored fields** in verified production recipes and jobs mean Schema **41**, Rules **55**. Existing versions need a real migration/compatibility assessment before deploying to an ongoing world; no silent state upgrades. Backward test fixtures and unrelated RPG state remain unchanged; update current-version pins and full historical CI. The code does not make 7-day villages sustainable by itself: farmers must still be able to physically visit and buy at a staffed market; employers need repeatable sales, seeded stocks and solvent budgets; subsequent phases must handle local meal access and full multi-day resilience.

DRAFT stacked on PLAY-40. Only merge after exact-SHA Python 3.10 + 3.13 targeted/full regression success, no `main` changes.
