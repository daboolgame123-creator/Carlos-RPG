# PLAY-24 — autonomous local production and buying (implementation plan)

**Status:** CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER (verified 2026-11-07). **Base:** PLAY-23 `aea55e50`.
**Validated source SHA:** `3772434491259610a373907db3acdae5bc36bb36`. Targeted CI: [42413896793](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42413896793) — 89 passed each Python; full CI: [42413896808](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42413896808) — 1,527 passed each Python.
**Closure report:** [PLAY_24_ECONOMIC_AUTONOMY_REPORT.md](PLAY_24_ECONOMIC_AUTONOMY_REPORT.md). P0 and external review remain open.
**Branch:** `simulation-engine-phase-play-24-economic-autonomy`. No changes to `main` or canonical story.

## Baseline / architecture
- PLAY-23's `ProductionStarted` consumes site-owned grain and schedules a real product due in 90 logical seconds. The `ScheduledEventFired` reducer completes production.
- `MarketOfferPosted` and `MarketTradeExecuted` check present actors, stock ownership, a registered keeper, exact quote, real copper and local inventory. Eating is already autonomous, after ownership.
- `LivingWorldEngine` simulates decisions and time in one all-or-nothing event command. Add the economic policy here only by explicit opt-in; no changes to event schemas or economic reducers.
- Buyer knowledge for this first stage is **on-site inspection of an actual open quote**; no remote knowledge of stock or prices. Do not invent a knowledge-delivery event.

## Work packages / priorities
1. Create **pure** economic-intent selectors. Baker chooses one eligible finite recipe when physically at the workshop, on an explicitly configured work shift, not already committed, safe enough to work, with known input/tool/output and local supply shortage. A market keeper posts a fixed, documented test-price offer against actual on-site food only when available and no overlapping open offer. A hungry, idle buyer with an initialized cash/food balance buys one unit of a genuinely locally visible quote if affordable and stock exists.
2. Integrate an `economic_enabled=False` gate with `LivingWorldEngine`. Resolve due production before planning; run separate production, posting, buying and eating passes in stable order, using the same authorized `DomainEvent` reducers and final atomic commit. Recheck state after each event; no special shortcuts for the test player.
3. Disposable scenario/test coverage: real time progression with several autonomous NPCs; no grain, no money, absent seller, busy/traveling buyer, off-shift worker, occupied tool, competing buyers, duplicate/stale commands, SQLite verify/reopen and deterministic replay. Preserve PLAY-23 opt-out semantics.
4. Matrix CI on Python 3.10 and 3.13: targeted scenarios **and full regression suite**, then report exact run URLs, pass counts and technical closure only if successful. Update `WORK_QUEUE.md`, `ROADMAP.md`, and a PLAY-24 report **after** successful verification.

## Scope boundaries
- Fixed test fixture price is not supply/demand pricing. No wages, external funding, spontaneous grain regrowth, free NPC restocking, starvation death or proven multiday sustainability.
- Inventory and money must be conserved under every trade. `main` and original RPG story stay untouched. Independent review and P0 remain open.
- A failure or unavailable CI keeps PLAY-24 open with explicit blockers.
