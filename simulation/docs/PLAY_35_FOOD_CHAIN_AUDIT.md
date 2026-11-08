# PLAY-35A — NPC material food-chain bottleneck diagnostics

**Scope:** Private deterministic, test-only observation of actual NPC-owned food, copper, farm production and physical courier delivery. Does not authorize new actions or a new market, and must never be exposed through Carlos player handoff.

## Distinct tasks in one acceptance batch

1. **Pure food-chain audit** in `food_chain_diagnostics.py`: explicit IDs for farm, bakery, market and courier; report individual high-risk needs without turning unknown inventory into zero. Count baked food only from completed real production jobs, market purchases only from durable paid receipts, personal eating only from consumption ledger, and show on-site stock separately from open offers to avoid double counting.
2. **Two autonomous 72-hour physical villages**: same seven NPC roles, 3 initially real market loaves, seed 1, water 2, harvest recipe yield 3, total 12 copper. In one village cash is concentrated in Carlos's wallet; in the other, eight existing coins belong to Omar/Layla from bootstrap. This is **not a wage mechanism**; the world never mints or redistributes money during play. No scripted NPC trade or feeding.
3. **Reproducible checkpoints and adversarial boundaries** at t=0, 300, 86400, 172800, 259200. Reconcile farm/field, outstanding cargo, bakery jobs, market stock, transactions, meals, and NPC hunger; verify SQLite genesis replay, saved snapshots and original inventory conservation after real time advances. Diagnose invalid configuration and purity.

## What success would and would not mean

Passing CI establishes that the measured numbers were produced consistently and that the accounting rules held. It **cannot** establish long-term sustainability; a village can pass all tests while every NPC becomes hungry. The observed problem in PLAY-34 is 7/7 NPC hunger 100 by day one despite stock and real sales. PLAY-35A will identify further stages where supply is held up over days two and three.

Subsequent PLAY-35 tasks must address local ownership and job completion before wages. Any worker remuneration must be financed by a real preexisting employer wallet with authenticated labor and conservation, not an unbacked daily allowance; introduce an explicit reducer and schema version only if the new feature requires durable events.

## Quality boundary

Runs on Python 3.10 and 3.13 on exact final SHA, plus full historical regression. PR is stacked on PLAY-34 until acceptance/merges. `main` and the canonical story untouched. P0, independent review, PLAY-14g and 03-A remain open.
