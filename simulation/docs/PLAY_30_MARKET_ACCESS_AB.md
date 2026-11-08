# PLAY-30B — real 72h market access and finite-copper experiment (2026-11-08)

**Status: CI_RUNNING / NOT TECHNICALLY CLOSED.**

## Observation that triggered this test

[PLAY-30 72h A/B #42484542698](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42484542698) passed both Python 3.10/3.13: increasing physically harvested grain per ripe crop 1→3 resulted in bakery output 2→4 and courier deliveries 6→12 by day 3, with 1→3 food units stocked in known sites. Yet all seven NPC hunger values, 38 cumulative meals, five personally owned remaining meals and one high-risk NPC were **identical**. Production is not synonymous with nutrition. The seven-day finite-water village remains food-insecure.

## Controlled market-access intervention

Run three real, fully autonomous 72-hour simulations with precisely the same seven NPCs, one real agricultural plot, 1 initial seed, 2 finite water units, physically moving courier, real bakery, offers and on-site purchase rules, 1 initial personal ration per NPC, frozen hunger clock 1/3600s and 20% action surcharge:

1. **Cash concentrated / high yield**: 3 grain per crop; Carlos owns 10 copper, Adel 2; other market residents own none.
2. **Cash redistributed / low yield**: 1 grain per crop; Carlos owns 2 copper, Adel 2, Omar 4, Layla 4.
3. **Cash redistributed / high yield**: 3 grain per crop; same individual wallets as #2.

Across all three, **total copper is exactly 12**; distribution is a trusted time-zero *test-world endowment*, **not minted money, wages, charity, player commands or an automatic economy mechanic**. No person can spend money absent from their private resource balance.

Log daily actual trades, personal food ownership, consumed meals, food in market, real baking and shipping, individual end-state hunger, action activity, SQLite event replay and every physical stock ledger. Do **not** assume that extra coins ensure a purchase: offers, seller availability, buyers' actual positions and appetite must all be respected.

## Gates and limits

- Targeted [PLAY-30B #42485432408](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42485432408) on Python 3.10/3.13, **pending**.
- Exact-SHA full [regression #42485432398](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42485432398) on both Python versions, **pending**.
- If either fails, inspect actual logs and fix only the verified issue, repeat on the final code SHA. Never call this a successful experiment before the logs are collected.
- Original behavior with `market_wallets=False` must be preserved. No Schema/Rules change (39/51), engine code change, extra food, extra coins, phantom routes or artificial rain. No P0 approval or merge to `main`.

**Next interpretation question:** Does physical bread reach hungry NPCs only after the market quote, actual local purchase and ownership transfer? If the answer is still no with funded wallets, look at decision priority, offers, inventory and workforce/social mechanisms **before** making crop yields even larger.
