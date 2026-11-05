# Phase 02-C — technical implementation report: local title and conserved trades

**Status:** **TECHNICALLY_TESTED CANDIDATE / FINAL-SHA CI PENDING / EXTERNAL_REVIEW_DEFERRED / P0 OPEN**. **NOT APPROVED/CLOSED.**
**Branch:** `simulation-engine-phase-02c`, based on 02-B `6dbee22a4b6b167a5b5ca5ece1c51612016b9e5d` ([green CI 42069605497](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42069605497), 673 tests per Python version).
**Schema 17 / Rules 24** from 16/23. No migration. The original story and `main` remain unchanged. Only disposable-test worlds.

## What is implemented

- **Ownership by resource owner:** 02-B produces actual bread at a workshop **site**. The bread legally remains in the site ledger. `MarketStallConfigured` at trusted world bootstrap registers an NPC keeper for one site. Only this keeper can offer that site's goods. The price paid for the goods goes into the site's existing `coin_copper` balance, **not** the keeper's private balance. NPCs may also offer their own actual personal resources; other NPCs' resources may not be claimed.
- **Local posted price and barter:** `MarketOfferPosted` records seller, owner, site, commodity, quantity, payment resource, integer units per commodity and the price/posted time. `coin_copper` is a finite, explicitly initialized currency resource; using another initialized exchangeable commodity provides **barter**. These prices are explicit local *asks*, not automatically computed supply-demand equilibrium or secret global market quotes. No re-pricing or algorithmic arbitrage. Listings are not escrow: the actual sale checks stock again.
- **One atomic trade:** `MarketTradeExecuted` is a trusted buyer-initiated acceptance, checking quote ID, exact agreed unit price, positive quantity and remaining offer units; the real buyer and actual seller/keeper must be present at the location and not traveling or physically occupied. Seller goods **decrease** exactly as buyer goods **increase**; buyer currency/barter decreases exactly as the seller owner gains. Unknown/absent balances are rejected, not made zero; insufficient stock/funds and any destination overflow reject the entire command.
- **Permanent trade evidence:** `market_trades` retains seller, buyer, stock owner, site, commodity/payment resource, units, price, total payment and all **eight before/after resource balances**. `market_offers` retains current units and terminal reason (`filled` or seller `closed`); it cannot sell beyond its remaining quantity.
- **Local privacy:** `NPCMarketService.local_quotes` returns currently deliverable on-site offers only to an NPC who is actually there; it does not tell remote NPCs about available prices. This is a trusted local coordinator, not a public player/API service. No remote money transfer, shipping or anonymous purchases.
- **Persistence:** new strictly validated `market_stalls`, `market_offers` and `market_trades` state projections. SQLite commands record their own `market_authorized` provenance and use it on full event replay. No arbitrary `ResourceChanged` transfer source was added. The trade is one reducer event inside an atomic SQLite command. Every snapshot is fully validated.

## Demonstration and evidence

`simulation/scenarios/test_village/demo_market_02c.py` starts **seven NPCs**, two bakers, two ovens, four units grain and zero site-owned bread; after **90 explicit simulated seconds**, two site-owned bread units exist. A named site steward posts an offer of two bread at three copper each. Two separate buyers each pay three of their ten initialized copper and each receive one bread. The bakery's bread falls to 0 and its copper rises from 0 to 6; the steward's own copper remains 0. Replay checks exact equality.

Added **24 tests** beyond 02-B's **673** (= **697** total) for bakery-to-market transfers, barter, price/quantity protection, no hidden title transfer, competing buyers, local visibility, off-site spoofing and travel, missing goods/currency, copper and goods overflow, wrong seller, closed listing, session pause, old market offer replay, atomic rollback, immutable snapshot validation, database restart and independently verified backup/restoration. Inherited security/parity tests remain.

**Source validation:** [CI 42074780496](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42074780496) has both 697-test Python 3.10 and 3.13 matrix jobs green, including the 02-C bakery-to-market demo, genuine old 02-B refusal and multi-generation event/semantic parity. After the latest focused test replacement and this report, **final HEAD must be confirmed green separately**; never claim final approval based on an earlier SHA.

## Deferred, not claimed

- This is a **first bounded market slice**, not a fully responsive economy: prices are seller-posted and fixed per offer, not supply/demand-calculated; no autonomous merchant decisions, bargaining, taxation, banking, interest, contracts, default, price statistics, dynamic local inflation, worker wages or trust-based fraud resolution.
- Goods posted for sale are not escrowed; actual physical ownership/funds are verified at each sale. No automatic cart, shipping or long-distance trading. The script cannot authorize actions of an untrusted player or external software.
- Resource-ledger ownership is not a court-enforceable land/property-title system. Site keepers are explicit trusted bootstrap delegates; title and proceeds remain with the site owner. Later property disputes and theft belong to future phases.
- Schema/Rules change means genuine 02-B **16/23** SQLite saves must be refused unchanged, not silently interpreted as 17/24. Production sites and market examples are disposable; original story never imported.
- **P0 OPEN** (backup operational recovery not independently approved) and **EXTERNAL_REVIEW_DEFERRED**; this report records implementer tests, not external sign-off. [Independent audit request](phase_02c_independent_review_request.md).

**Next roadmap step:** 02-D — debt contracts, due dates, overdue/default and repayment. Do not quietly count unpaid promises as coin or completed trade.
