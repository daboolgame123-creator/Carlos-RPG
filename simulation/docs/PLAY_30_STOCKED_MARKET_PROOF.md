# PLAY-30C — finite local-market proof and supply failure (2026-11-08)

**Gate:** targeted proof SUCCESS on Python 3.10 and 3.13; exact-final-SHA full regression **PENDING**. **Do not merge or close pending gates.** Disposable seven-NPC village, Schema **39** / Rules **51**, `main` untouched.

## What the previous trials established

- [Real 72h grain A/B #42484542698](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42484542698): fully passed on Python 3.10 and 3.13. Frozen 1→3 grain per ripe crop **increased bakery output and courier deliveries**, but at 72h did not change any of seven individual hunger levels or the 38 meals consumed. Food remaining in sites rose 1→3.
- [Three real villages / 72h / wallets A/B #42485432408](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42485432408): completed/success for both Python versions. Only 1 actual purchase and 8 consumed meals per world. All seven NPC reached hunger 100 by day 3 whether their wealth was concentrated or distributed, despite a fixed total of 12 copper; the courier had only 5 deliveries by day 2 and **none additional by day 3**. This shows that funding households **cannot substitute for bread arriving before workers become too hungry to transport it**. Two real water units remain a fundamental crop limit.

## Controlled stocked-market intervention

To distinguish broken purchase logic from lack of accessible food, compare two otherwise identical, **economy-only** isolated real markets at t=0:

- Seller Salma and 3 physically initialized, pre-existing site-owned loaves in the market; 7 independent NPCs, actual buyers Adel, Omar, Layla each hungry (80), same coin total **12**, same time, place, consumption/market authorization, seed=1, water=2, crop yield=3. The 3 loaves are explicitly declared as **test-world opening inventory** and included in the physical food conservation equation. **No mid-world or untrusted stock injection.**
- **Concentrated wallets:** Carlos10 / Adel2 / Layla0 / Omar0 copper → Adel purchases and eats **1**, market retains **2** loaves. Layla and Omar hunger becomes **81**.
- **Redistributed wallets:** Carlos2 / Adel2 / Layla4 / Omar4 copper → each of the three buys and eats **1**, market empties, Layla and Omar hunger becomes **56**.

[PLAY-30C targeted CI #42486816065](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42486816065) is **SUCCESS: 16/16 tests on each Python 3.10/3.13**. Both observed outcomes are identical across Python versions. An empty market with all three funded buyers yields **zero** purchases. Local presence, seller offers, buyer's own funds, ownership transfer, actual consumption and SQLite replay are audited.

**Conclusion:** the authenticated local market and eating mechanism work when the goods and funds are both present. In the natural three-day scarcity trials, distribution arrives too late and courier/wider labor becomes unable to operate. Neither crops alone nor wallets alone restore the food chain. Future intervention should be physically supported, conserve initial allocations and explicitly distinguish early distribution from long-term water and food shortages.

## Safety and version boundary

Optional test-only `initial_market_food` (0–3) and `hungry_market_buyers` (strict boolean) are trusted bootstrap parameters; defaults preserve all prior worlds. No additional runtime resource-creation ability, general wages, teleportation, hunger policy alterations or persisted contract change.

**Remaining:** exact SHA full historical regression on both Python versions, independent external review and P0 production gates. **No canonical world release.**
