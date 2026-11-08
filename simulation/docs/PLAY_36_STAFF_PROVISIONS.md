# PLAY-36 — test-only, zero-sum emergency staff food allocation

**Not a runtime feeding feature** and not evidence of a sustainable food economy.

This is the first hypothesis trial responding to [Issue #24](https://github.com/daboolgame123-creator/Carlos-RPG/issues/24). Physical seven-NPC village tests show that hunger can immobilize the farmer, baker and water courier even when a physical crop eventually matures. To evaluate the *importance of initial food ownership*, run two independent 72-hour worlds with **exactly the same** total food and cash.

- **Market-first control:** three physically predeclared bread units at the market, zero personal starting food among NPCs.
- **Staff-prepositioned alternative:** three *existing, time-zero* bread units, one in the owned stock of Nora (farmer), Basim (baker) and Huda (courier), zero at the market. This is the same three-unit starting endowment, **not three additional loaves**.
- All seven NPCs, their initial hunger, seed, physical farm, water, crop-yield recipe, initial 12 total copper, travel routes and autonomous decision policies are otherwise identical.
- These opening stocks are declared before the first simulated second. **We are not modelling a physical meal-delivery contract, salary, emergency logistics action or magical teleportation**. The allocation is a strict trusted bootstrap-only fixture; a real in-world implementation would require local transfer of owned food and event provenance.
- The option defaults to False and requires exactly 3 initial market loaves and no other NPC personal stock. Invalid type, stacking, time mismatches, insufficient stock and conservation regressions are rejected.

Checkpoints: 0s, 300s, 3600s, 1 day, 2 days and 3 days. Record all individual worker meals and hunger, market food and cash, crop and bread outcomes, courier deliveries and route blocking, and all-NPC hunger. Verify every live world state against genesis replay and snapshot on each checkpoint. **No assumption that rations solve famine**, or that 72 hours prove long-run survival.

**Quality gates:** Python 3.10 + 3.13 targeted run, then full historical regression on exact final SHA. Draft PR is stacked on PLAY-35; do not update `main`, alter the original Carlos roleplay story, or claim external review/P0 acceptance.
