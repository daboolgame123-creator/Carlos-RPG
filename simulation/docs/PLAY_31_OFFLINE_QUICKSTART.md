# PLAY-31 — Seven-NPC playable offline village: quick start

**Status:** PLAYER VERTICAL SLICE, experimental/disposable. Not a canonical story, not a permanent world or network game. Main and original narrative files stay untouched.

## Run from Windows PowerShell

```powershell
git clone --single-branch --branch feature/play31-seven-npc-offline-vertical-slice-20261108 https://github.com/daboolgame123-creator/Carlos-RPG.git Carlos-RPG-PLAY31
cd Carlos-RPG-PLAY31\simulation
$env:PYTHONPATH = "src"
python scenarios/test_village/play_village_local.py
```

Python 3.10+ is required. No API key, LLM connection, PostgreSQL or server is needed.

## First real game actions

```text
scene
status
supplies
move home-market
wait 90
scene
look
offers
talk salma greeting Hello
needs
handoff
quit
```

The player starts in the test house and must walk along the **real 90-second home-to-market road**. The village has **7 autonomous NPCs** (Basim, Salma, Adel, Nora, Huda, Omar and Layla), plus Carlos, five locations, finite well water, seed, tools, a bakery, market and courier. Waiting advances all characters within physically constrained systems; `scene`, `status`, `supplies` and `handoff` do **not** advance time.

Additional commands: `food`, `forage`, `askfood <npc> <site>`, `buy <offer-id> <quantity> <unit-price>`, `eat`, `give <npc> <resource> <quantity>`, `remember`, `purchases`, `meals`, `gifts`, `conversations`. `help` prints exact syntax.

A sale succeeds **only if** a local real offer exists, the seller and Carlo are present and the quoted stock and player copper suffice. `forage` can fail naturally if no known collectable local resource exists. Conversations never let the player take over NPC decision-making. To simulate more time, use `wait <seconds>` repeatedly (1–21600 seconds per command).

`handoff` prints a **player-scoped, read-only** JSON summary suitable for copying into ChatGPT to narrate actual observations without revealing invisible knowledge, private NPC inventories or event authority.

## Current hard limits

- This is a **temporary SQLite test world**: all state disappears on exit, by design, until production recovery P0 is approved.
- Sample HP/ST are fictional fixtures and **not** the canonical Carlos character statistics.
- The 7-NPC village is **not self-sustaining for a full week**, due to finite water/food/transport and purchasing constraints established in PLAY-29/30.
- No GUI, mobile client, server authentication, freeform AI conversation or permanent save exists in this slice.
- Schema 39 / Rules 51; no migration or network listener.

## Verification

Targeted Python 3.10/3.13 tests cover actual CLI subprocess, player-only projection, finite supplies, seven independent NPCs, elapsed-time walking, SQLite replay and rejected unauthorized remote actions. Full-historical CI on the final commit is a **separate required gate**; do not describe the slice as closed until it finishes successfully.
