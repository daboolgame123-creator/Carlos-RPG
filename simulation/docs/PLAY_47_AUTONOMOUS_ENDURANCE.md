# PLAY-47 — NPC economy: multi-day endurance and root-cause measurement

**Status: OPEN / FIRST INSTRUMENTATION PILOT.** Depends on PLAY-46's **technical** closure at `a346d8b5f3fe4b736e420bfa3e470a8afa089313` (Python 3.10/3.13 full CI green, review deferred by owner). No external approval, P0 signoff, `main` merge or durable save support.

## Objective

Measure independently acting NPC economies over increasing in-world horizons, distinguishing **valid economic shortage** from **software integrity regression**. Never issue Carlos commands to drive NPC shopping, add free stock or mint copper to make a scenario pass.

This stage *cannot* claim a seven-day sustainable medieval village merely because a one-hour smith chain survives. A 7+ actor joined world integrating hunger, food/water, wood and ore production, local shops, courier routes, bounded resources and cash must be tested independently before full closure.

## Phased implementation and honest evidence gates

1. **47-A — accounting-only pilot (this commit):** read-only `audit_npc_economy()` projection with known-copper amount, explicit unknown ledger owners, stock counts, authentic trade/job/wage receipts, journeys and NPC needs. This is trusted operator-only diagnostics, **never NPC/player omniscience**. No changes to Schema 42 / Rules 57 or events.
2. **47-B — real short-world evidence (this commit):** reuse a verified unscripted PLAY-46 smith→repairer world; observe t=0, 700 and 3600. Require constant six initialized copper coins within the same known ledger scope; no unsourced jobs/trades, correct replay, physical travel. A one-hour test is **not** long-run evidence.
3. **47-C — genuine integrated world:** build a 7–10 NPC shared world (not two disconnected test villages) with food/water, physical hauling, market needs and nonfood workshops. Analyze mode-flag coexistence; `economy_only_enabled=True` disables ordinary survival dynamics, so do not use it as a hunger/endurance proof. Treat unimplemented mechanisms as blockers, not pretend they exist.
4. **47-D — 24h and 72h tests, then 7d where feasible:** checkpoint hunger, inventory, demand, cash distribution, funded/unpaid work, route timing, shortages and breakdown. Use segmented advances bounded by event budget. Treat starvation or bankruptcy due to finite real resources as a valid measured outcome, not a CI failure.
5. **47-E — isolate and repair root causes:** only patch reproducible software failures and misprioritized decisions. For resource infeasibility, document the economic constraint and propose a separate audited supply mechanism; do not inject stock mid-run.
6. **47-F — adversarial and closure:** invalid/unknown financial entries, seller absence, no known road, zero funds, job/wage duplication, real predecessors' save refusal, SQLite replay/snapshot/PRAGMA, time-step partitions and default-off equivalence. Run targeted and full Python 3.10/3.13 CI on **final exact HEAD**. Write decision report.

## Pilot constraints

The pilot provides no general economic solvency, demand model, resource regeneration, institutional investment, employer liquidity guarantees or player UI. The report's `copper_known_total` explicitly excludes owners whose copper ledger has not been initialized; an unchanged value is **not proof** of a complete-world monetary balance when `copper_scope_complete=False`.

## Rollback, trust and tracking

- The audit is read-only: no event/DB writes or new gameplay authority; unknown balances are never silently equated with zero.
- Reusing existing trusted test-world genesis does not authorize migration of PLAY-45 saved worlds to Schema 42.
- Playable Carlos input and untrusted network/API remain isolated; P0 production and external review stay open.
- Last SHA, genuine CI links, actual NPC/economy outcomes, observed bottlenecks and open gates belong in the next report.

## 47-C baseline experiment (separate from compound production)

- Adds a **single real seven-NPC food/water village**, with `economy_only_enabled=False`, enabled survival, paid food purchases, actual farm→bakery→market physical distribution, hunger and bounded cash. Read-only audit checkpoints through **24 hours**, matching event replay and SQLite integrity.
- Independent **zero-water counterfactual** measures no free harvest over six hours. A shortage is not treated as a software failure; the opening three loaves may still be eaten.
- This is an **intermediate baseline**, not the final *joined* NPC world: the compound/professional planner currently requires `economy_only_enabled=True` and its coexistence with full survival needs explicit design and independent testing. **Do not claim 7 NPC full compound-professional autonomy or 72h/7d sustainable survival from this batch.**
- No schema/rules/event changes, no new privileges, no player-visible omniscient diagnostics.
