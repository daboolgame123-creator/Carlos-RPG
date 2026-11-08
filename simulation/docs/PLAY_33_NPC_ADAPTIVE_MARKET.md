# PLAY-33 — bounded, opt-in NPC local-market adaptation

**Status:** IMPLEMENTED_FOR_CI / NOT_YET_ACCEPTED. Independent review and production P0 remain open.

## Intended gameplay and ownership

The village's bakery, traders, hungry customers and finite wallets remain autonomous. Carlos does not trigger prices, production or NPC purchases. No special player economy is introduced.

- `adaptive_market_enabled=True` requires `economic_enabled=True`, and defaults to **False**. With the flag off, previously tested quote price (2 copper), buyer behavior and event reason strings stay unchanged.
- Sellers quote from **their own actual stall inventory**: one loaf → 3 copper; two or three → 2 copper; four or more → 1 copper. Zero means **no offer**. The offer remains a fixed agreement after posting; the algorithm never silently re-prices an outstanding contract.
- Buyers evaluate **only colocated, physically available** posted food offers, their own cash balance and their own hunger; deterministic cheapest affordable selection. At hunger 70–79 willingness is 2 copper, at 80–94 it is 3 copper, at 95+ it is 4. They cannot see other NPCs' private hunger or remotely inspect markets.
- A registered keeper can retire an underfunded physical food listing (remaining offer quantity exceeds actual **local** stock) via the pre-existing authorized `MarketOfferClosed` reducer. It creates neither stock nor cash and does not compensate or unilaterally revise an accepted trade.
- The state/event format is unchanged for this feature (no schema migration). All mutations still pass through existing market reducers, local-presence checks, event budget and atomic event-store commits.

## Acceptance gates

- CI: `.github/workflows/play33-npc-market.yml` checks Python 3.10/3.13, new policy/integration tests, existing PLAY-24 NPC economy, 02-C trade authorization and PLAY-30C stocked local market.
- Validate exact final commit SHA; then run/check historical full regression for the same SHA before changing PR status or merging.
- Scenarios: no inventory, one-loaf shortage, financed/underfinanced buyers, competitor, stale offer, buyer near vs far, price tier, best local quote, invalid option types, double-trade protection, deterministic independent worlds, SQLite snapshot/replay and conserved physical food/copper.
- Pure-policy synthetic snapshots are **tests only**; they are not substitutes for the durable village event trials.
- **Do not claim** long-term food sustainability, equilibrium prices, wages, remote commerce, or absence of every economic failure. Those need further seven-day trials.

## Merge boundaries

Feature branch `feature/play33-npc-market-adaptation-20261108` targets the development branch `design/play29-seven-day-provisions-20261108`, **never** `main`. PLAY-32 is a separate integration change; verify GitHub merge compatibility and exact HEAD before accepting this PR.
