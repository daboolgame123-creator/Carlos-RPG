# PLAY-32 — Quest acceptance, verified progress and conserved reward

Status: **DRAFT / UNVERIFIED** until targeted and full CI succeed. Branch is
based on PR #20's exact head, not merged into the main development branch.

## Scope

One deliberately bounded scenario quest: `market_first_loaf`.

1. The player explicitly uses `accept market_first_loaf` (no auto-player AI).
2. A **new, verified, actual** `MarketTradeExecuted` receipt from Salma's
   market-site-owned bread, paid with at least two existing copper coins,
   completes the accepted objective. Past purchases do **not** count.
3. `quests` reveals only the player's own accepted/completed/claimed state,
   one receipt ID from their own trade and an advertised public objective.
4. `claim market_first_loaf` requires the keeper present at the market and
   transfers exactly **one existing coin** from the market's known receipts
   to Carlos's own initialized balance, atomically and at most once.
5. The read-only `handoff` exposes this player-only projection with a
   consistent world/time/revision, never the entire NPC state.

No XP, magic, automatic healing, gifts, world-wide omniscience or fabricated
resource initialization. The reward is explicitly a **market-funded cashback**
on a completed verified transaction, not a magically minted coin.

## Data and compatibility decision

- Source **Schema 39 / Rules 51** → **Schema 40 / Rules 52**.
- The new `player_quests` durable `WorldState` collection is necessary
  to protect acceptance order, evidence, completion, idempotent rewards and
  replay without piggybacking on an NPC diary or unrelated RPG inventory.
- The existing `rpg_authorized` command capability persists the new quest
  commands; no new SQLite authorization column is required.
- Old worlds must reject the changed schema/rules. No silent migration,
  retroactive quest completion, or conversion of old saves. This branch
  targets a **disposable test village** only.
- This does NOT close long-lived world backup/restore P0, authorise a
  canonical story import, or substitute an independent security review.

## Acceptance gates

Targeted Python 3.10/3.13: acceptance, delayed merchant, factual purchase,
post-accept evidence only, one-funded-reward policy, conservation, local
presence, forged event/privilege rejection, stale revision, pure reads,
snapshot, close/reopen and SQLite event replay.

Full historical suite: must pass on the **final PR SHA**, and PR #20 must
first close on its own final green full suite. Merge **only** to
`design/play29-seven-day-provisions-20261108` after the dependency and
all relevant CI gates pass. `main` remains untouched.
