# Carlos RPG — confirmed newest tasks (2026-11-11, PLAY-48)

**Source of truth remains exact GitHub CI and git SHA, not this static handoff.**

## Official status

- **PLAY48_OPEN / RELEASE_NO_GO**. Do not touch `main` or begin PLAY49. No production migration of old SQLite saves, no claim that the village has survived a true 168-hour recovery.
- Current experimental code **Schema 44 / Rules 59**, new market service salary events/contract ceiling. Old validated saves remain Schema43 / Rules58; latest code rejects them safely rather than automatically migrating.
- Carlos world sim operates on actually tracked 13 residents, 12 copper, 3 opening loaves, bounded seed/water/rain, true crop maturity, physical roads, no magical transfers.

## Completed verified runs

| Scope | Run / exact SHA | Result |
| --- | --- | --- |
| PLAY48W — two actually signed market employee contracts | [#43007695830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007695830), `c9f7c4309e392996da19a361fb1dbebe0c0cffb3` | **SUCCESS both Python 3.10/3.13 real 48h**. Hana eats two extra employer-funded loaves and hunger improves; Huda earns **zero** market wages because her physically actual farm-water work doesn't satisfy the market food-delivery condition. |
| PLAY48U — Hana market contract, real new salaries | [#42999941836](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42999941836), `81b8446a` | **SUCCESS both**. Genuine 2 extra Hana wages, 6→8 village meals, hungry100 5→4, Hana hunger100→60, **no increase in 35 actual deliveries**, 12 copper conserved. |
| PLAY48X — current-version historic regression and save rejection | [#43014260381](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43014260381), tested source `b939992d9d342175d042cb206e4c545fc4ea2a15` | **SUCCESS Python3.10 and 3.13: 1696/1696 pytest each**, after explicitly updating 23 current-version test files and two current Rules59 pins. Genuine old 43/58 save verified with frozen old SHA `aa836e46...`, then rejected by 44/59 **byte-for-byte untouched**. This proves rejection, NOT migration. |
| PLAY48S3 — prior 96h one-off wages | [#42926808427](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42926808427) | **SUCCESS dual-Python negative economic finding**: 13/13 starvation and zero post72 jobs, deliveries and meals. |

## Current pending genuine experiments

- **PLAY48V — real 96-hour renewable-but-capped Hana market wages**: [#43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657), tested source `37cd8fb5a1d5fed140a3c5d9ec19b4cac164e0a3`, *two long jobs in progress at last check*. Need inspect `PLAY48V_TRUE_FOUR_DAY_MARKET_WAGES_CAUSAL_PROOF` before claiming post72 recovery or negative.
- **PLAY48Y — bounded Huda farm-worksite wage trial**, current branch `experiment/play48y-farm-worksite-paid-courier-20261111`. [#43017271741](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741), tested source SHA `81cddebbc738832c2409f603f38d2fb6f805eca4`. **Both Python genesis checks PASSED**, true 24/48h independent A/B still in progress. Genuine same 13NPC worlds: only 3 opening real loaves, but time-zero ownership is now **2 FARM + 1 MARKET** rather than historical **1 FARM + 2 MARKET**; Huda's farm employer escrows 2 of its originally owned bread for physically delivered water, control vs early pay identical at genesis. This tests finite actual worksite nutrition without inventing wages, food, routes or resources. First attempt failed because bootstrap was incorrectly treated as an event-transformer; corrected by adding bounded `farm_initial_food_loaves=2` to the existing test-world initializer, which defaults to 1 on all original scenarios. **Do not claim the extra wages are paid/eaten before checking actual long tests**.
- More details: [PLAY48Y_FARM_HUDA_PAID_WORKSITE_TRIAL.md](PLAY48Y_FARM_HUDA_PAID_WORKSITE_TRIAL.md).

## Next

1. Check actual live results of V and Y, compare Huda hunger, real deliveries, Hana wages, personal food consumption, market bread rights, all 12 copper, and SQLite replay.
2. If Y provides a benefit, **do not mistake preexisting extra farm bread for renewable supply**. A genuine long-term worksite wage requires physically procured bread delivered to FARM by a valid courier, with explicit farm ownership (purchase/barter), real site arrival, and no consumption of customer-quoted or entrusted food. New transport policy may demand new version/migration and full review.
3. Need actual non-courier income and food access for 11 other villagers; later genuine 96/168h A/B under bounded rain, drought, insolvency, with post72 work/delivery/meals documented.
4. Full CI and save rejection at exact final integrated source, independent review. Do not merge or claim closure in this chat without those proofs.
