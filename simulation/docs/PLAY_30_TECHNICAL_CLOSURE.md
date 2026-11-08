# PLAY-30 — technical closure (2026-11-08)

**Decision:** `PLAY30_CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER`; experimental seven-NPC fixtures only, `P0_PRODUCTION_NOT_APPROVED` and `main` unchanged.

**Final source under test:** `345741c2639a269309a76be6f419fef16946fcbf` at [consolidated PR #18](https://github.com/daboolgame123-creator/Carlos-RPG/pull/18), squash merge `186c79fc0fe28deead8f052dfc769bb840abcf7c` into `design/play29-seven-day-provisions-20261108`. Schema **39 / Rules 51** unchanged. No migration or canonical story modifications.

## Acceptance evidence

- Exact source SHA [full CI #42486981474](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42486981474) **SUCCESS**: Python **3.10 1,670 passed**, Python **3.13 1,670 passed**, zero failures. Duplicate full run [#42487008993](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42487008993) **SUCCESS** on both.
- [PLAY-30A #42484348893](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42484348893): **52 passing on each Python**; one plot/one seed/two water → two authenticated real crops, 2 vs 6 baked units for frozen per-crop grain yield 1 vs 3; 6 vs 13 courier deliveries, all physically conserved. Opt-in trusted test recipe, historic default unchanged.
- [72h realistic food/hunger #42484542698](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42484542698): **SUCCESS** on both. Despite more baked food and movement, 38 meals and seven individual hunger values unchanged after day 3. **Production alone does not prevent hunger.**
- [Three independent 72h worlds #42485432408](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42485432408): **9/9 pass each version**, consistent 7/7 at hunger 100 by day 3 with scarce opening personal rations; redistributed but conserved twelve copper did not make absent food accessible.
- [Pre-stocked local market #42486816065](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42486816065): **16/16 pass each version**, three declared opening market loaves (physically audited), finite 12 copper; concentrated wallets lead to one real purchase/meal, distributed wallets three; Omar and Layla hunger **81→56**. Food absent → zero sales even with money. No minting, teleportation or unauthorised consumption.
- Replay and snapshot checks, strict fixture controls, rejected invalid endowments, time-locked production and historic compatibility included.

## Scope and remaining risks

PLAY-30 was a **bounded diagnostic experiment**, not a promise of long-term subsistence. **Observed hunger is a real world-design deficiency**; finite water and late/failed courier delivery constrain agriculture, then personal access/ownership constrain eating. An independent robust seven-day food chain remains **unimplemented**. Do not call the village sustainably fed or the engine release-approved.

## Next priority: playable vertical slice

The project owner wants faster progress toward a playable Carlos RPG. Prioritise a **disposable, local, offline, player-controlled seven-NPC village session** with existing gateway actions, movement, conversations, state readouts and read-only handoff, rather than a sequence of ever-larger subsistence experiments. Existing support already includes `PlayerGateway` methods but the old sample CLI exposes only a small subset. Limit first implementation to a trusted offline console; no network, server save, magical resources, unsolicited player actions or changes to canonical story. A genuine forever-sustainable economy may follow once the game can actually be tested by the player.
