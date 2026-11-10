# PLAY-48H1 genuine 13-NPC A/B, day-four causal comparison

**Status:** `EXPERIMENT_DEFINED / REAL_CI_PENDING / PLAY48_OPEN`  
**Branch:** `experiment/play48h1-13npc-day4-counterfactual-20261110`, based on H1 experimental version **43/58** at `74a18f212ecdc09c4e4ebb7c5e196bc010a90853`.

A real SQLite copy of the **identical authenticated 13-NPC genesis** is split before one first action. The control retains the exact original PLAY-47 economy. Only the treatment signs two genuine market-funded **one-loaf each** courier contracts at t=0. The market starts with three loaves in both; treatment transfers two existing loaves from saleable stock to site-owned escrow (now one saleable loaf), and spends no new copper. Both run the same finite rain (two units at 24h/48h/72h) and same full-life NPC decisions. No driver commands buy, move or pay anyone after trusted genesis.

Measure 24/48/72/96h hunger, production, real trades and wages, meals, market food, real courier deliveries and recorded escrow settlements. Verify all food/grain/water/coin conservation, daily SQLite reopen/full genesis replay, and partitioned day-four tick parity. The 72→96h delta is compared independently in each world; a green test can honestly report *no recovery*. Do not declare independent causality from aggregate counters alone: a genuinely attributable delivery→job/sale/meal chain needs separate event-level proof.

Targeted GitHub Actions across Python 3.10 and 3.13 are required before considering the measurement verified. This is **not** P0 approval, old-world migration, automatic merging or PLAY-48 closure.
