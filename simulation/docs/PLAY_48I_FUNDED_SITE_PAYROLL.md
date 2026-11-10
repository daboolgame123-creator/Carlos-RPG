# PLAY-48I: already-implemented job wages made real for the main field and bakery

**Status: PROTOTYPE — PLAY48_OPEN / RELEASE_NO_GO**. No merge or migration. Schema43 / Rules58 unchanged.

## Why this test exists
The real 13-NPC settlement already pays the second-field farmer, but the first-field farmer **Nora** and baker **Basim** have never signed wage-bearing production contracts. Their job participation cannot replenish personal purchasing money. Meanwhile the two real couriers bring cash back to bakery and the farms, but unfunded worker wages mean this money accumulates in site wallets while employees starve.

## Minimal explicit causal intervention
The engine's existing `ProductionWagePaid` event and strict conservation checks can already pay a *completed* job exactly once. We enable `site_payroll_enabled=True` **only in an isolated original world seed**:
- At authoritative time-zero genesis, transfer the already owned **two copper of player Carlos** into the actual **farm till (1)** and **bakery till (1)**. No new copper and no runtime handout.
- Sign one-copper-per-completed-job contracts on existing `finite-harvest` and `grain-to-bread` recipes. Nora and Basim have initialized zero personal wallets.
- Every payment is contingent on a genuine completed job, local presence and an employer treasury with enough real copper. If site cash runs out, a valid job stays unpaid — no debt or rescue income is automatically invented.
- Existing physical routes, crop duration, market offers, coin-return courier plans, guards, food consumption and original metabolism remain unchanged.

## Falsifiable controls
Compare the genuine original 13-NPC village and payroll variant at 24/48h and 96h with same initial food, roads, tools, farming weather and **12 total opening copper**. Events and conservation laws must prove individual site→worker transfers and consumption, rather than mere intended wage offers. A negative attempt to forge salaries before any job is completed must fail atomically.

A positive receipt at 48h is not enough: **the target is repeatable wage→food shopping→market income→worksite replenishment**, ultimately a finite 7-day NPC simulation. If cash stays locked in wrong site, courier declines due hunger or the labor force cannot afford the market, DO NOT alter hunger numbers to fake economic success.

**Known limitation:** this batch uses existing production wages and H3 food-backed courier wage. It is NOT yet a general coin salary to couriers; that requires an independent anti-forgery/custody design. Avoid double-counting courier consignment money.

No final PLAY48 closure or sustained-recovery assertion before actual independent CI and 7-day evidence.
