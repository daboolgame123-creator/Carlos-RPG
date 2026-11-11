# Carlos RPG — newest handoff: PLAY48AB bakery reservation (2026-11-11)

**Read live GitHub runs first.** Phase stays **`PLAY48_OPEN / RELEASE_NO_GO`**. `main` untouched, zero production save migrations, and no actual 168-hour economic survival result. Source code remains experimental **Schema45 / Rules60**; because AB additionally changes freight priority relative to AA, reserve a NEW rules version before release instead of silently interpreting older AA worlds under revised same-number rules. This project requires exact event sourcing, no magic minted bread/coins, and 13 independently controlled villagers.

### Confirmed real causal findings

- [PLAY48AA true 13-NPC 48h #43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266): **SUCCESS technical both Python3.10/3.13 but NEGATIVE economic result.** Huda's real farm grain produced **3 grain-for-bread claims**, yet bakery shipped **0 genuine loaves back to farm** during 48h; bakery food0, market food7, 12 copper conserved, village6 meals. Market-bound couriers took bakery loaves before farm return.
- [PLAY48Y2 true 96h Huda paid farm wages #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939): **SUCCESS both Python3.10/3.13**, paid arm Huda deliveries12 vs3, completed jobs24 vs20, meals7 vs5, but BOTH arms 13/13 hunger100 day4 and **0 new** meals/trades/jobs/deliveries after hour72. This is important proven causal failure of 2 finite loaves, not recovery.
- [PLAY48AA adversarial #43034249899](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43034249899): **7 tests passed each** Python3.10/3.13; cannot seize quoted baker food, double-load freight, or fake delivery.
- [PLAY48AA genuine old 44/59 save gate #43037819648](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037819648): old real save generated under 44/59 rejects byte-identically on new experimental 45/60, both Python versions. NO migration.
- Original new45/60 historical full run [#43033787068](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43033787068) had **1 erroneous 59s→60s test-clock assertion** caused by overbroad version replacement; 1695 passed and 1 failed on Python3.13. Corrected **only** unrelated `mid.time == 59` and launched exact head [#43037819648](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037819648), full 1696 prior tests 3.10/3.13 still pending at last check. Do NOT claim full green until confirmed.

### Work just implemented and now testing

- Source branch `experiment/play48ab-bakery-obligation-physical-priority-20261111`, tested code SHA `8333c9472aff29f437183ce812680a081025053f`. Existing signed farm grain-for-bread claim now **protects ONE existing real bakery loaf** from all market-bound couriers until its physical bakery→farm return, leaving any other bakery loaves marketable. Neither a claim alone nor unpaid bakery inventory creates food. Delivery requires physically carried stock, one cargo per trip and seller customer-offer protection; no false road or worker knowledge.
- [PLAY48AB targeted CI #43037662900](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037662900): signed local booking, cargo/ownership and legacy-off guards **PASS on both Python3.10/3.13**. Actual independent 13-NPC 48h A/B still running: inspect `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD` and especially `actual_bread_returned_to_farm`. Merely green means the tracer passed, NOT >0 arrival.
- Integration branch `integration/play48ab-warehouse-priority-exact-regression-20261111`, code+checks SHA `d2f2f8b82cd5ed2a8ae956921d71765b0fec7cf3` plus documentation-only commits. [Integrated CI #43038336009](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43038336009) FAST combined physical/quote/duplicate-cargo checks **PASS dual Python**; complete historical 1696-test matrix still in progress at last check. This branch incorporates prior explicit Schema45/Rules60 historic version pins; timed foraging partial wait restored to 59.

### Next hard gates

1. Check actual AB run for **physically returned bread >0**, real market/bakery production cost, and all 12 coins. If no delivery again, audit actual bakery stock time, Huda route stage, starvation before index4, and customer food claims rather than introducing magical instant transfer.
2. Only if genuinely returned bread reaches FARM, independently design signed funding of Huda's NEW wage from that true farm-owned bread, attached to her future authenticated fresh farm WATER-delivery. Existing 2 opening wages cap remains; AB does not itself extend payroll.
3. Compare **1 grain : 1 loaf** (currently overly generous to farmer) against a fairer real physically bounded bakery exchange; physical producer wages, finite water, market customer access must remain viable. One real loaf held forever for a missing courier can further starve a market, so treat insolvency and drought as real failure cases.
4. Explicit distinct new RULES_VERSION before loading any persisted AA 45/60 worlds with AB changed dispatch semantics. Full final CI, 96/168h 13-NPC same-genesis A/B, drought/copper bankruptcy/adversarial tests and save migration decision required before `PLAY48_CLOSED`. Do not start PLAY49 or touch `main`.

Detailed design: [PLAY48AB_BAKERY_OBLIGATION_RESERVATION_DECISION.md](PLAY48AB_BAKERY_OBLIGATION_RESERVATION_DECISION.md). Actual work routing: [WORK_QUEUE.md](WORK_QUEUE.md).

---

# Carlos RPG — latest PLAY-48AA integration handoff (2026-11-11)

**Status:** `PLAY48_OPEN / RELEASE_NO_GO`. `main` untouched, no old-world production save migration or 168h recovery acceptance. **Verify GitHub CI status/live SHA before continuing**; this file is a dated record.

Current verified physical facts: 13 genuine NPCs, 12 conserved copper, only 3 real initial loaves, farms grow with finite water and time. [Huda genuine two-farm-wage 48h #43017271741](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43017271741) SUCCESS 3.10/3.13: Huda ate 2 and transported 10 instead of 3 deliveries, hunger86 vs100. [Hana capped market-food 96h #43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657) SUCCESS as a **NEGATIVE economic result**: both A/B worlds 13/13 hunger100 and ZERO new work, food sales, meals or transport after hour72. A 48h positive wage result is not village survival. [PLAY48Z actual road proof #43028314540](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028314540) SUCCESS: existing bakery→farm road returned copper only, without legitimate bread procurement.

**Active new code:** `experiment/play48aa-physical-grain-for-bread-return-20261111`, tested core SHA `4b4c8b663ead5fa5483d23e8b9dee195777d6200` using **experimental Schema45 / Rules60**. Trusted time-zero circuit option `farm_bread_share=True` earns one bread entitlement after actual physical grain delivery to the bakery. It does NOT mint bread. Courier can use existing bakery→farm return leg to carry a genuinely baked, bakery-owned, unquoted/unconsigned loaf (and keep one bakery spare), **OR** copper, never both. Delivery physically credits farm food and settles exactly one claim. Alternating potential cash and bread trips can delay legitimate farm copper wages. Current 1 raw grain : 1 finished bread ratio is an **unreviewed generous experimental price**, not evidence of a profitable local economy; inspect actual bakery and market costs before production.

**Evidence:**
- [PLAY48AA targeted run #43032756266](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43032756266) signed genesis/forgery checks **PASS both Python3.10/3.13**, but **true actual 48h 13-NPC A/B remains pending**. Read `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD` log before claiming positive freight. First run failed overly strict t=0 slot-order check, fixed and rerun.
- [PLAY48AA security CI #43034249899](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43034249899) **SUCCESS 7 tests each Python3.10+3.13** in an independent version-contract integration branch: customer quote protection, alternating copper/food, no duplicate cargo or bakery food rights, tampering blocked.
- [PLAY48AA Schema45/Rules60 complete prior-tests and real old save gate #43033787068](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43033787068) **real old44/59 SQLite save rejection without any byte mutation PASS both 3.10/3.13**. Full historical regression is **pending**; newer source on branch `integration/play48aa-schema45-regression-20261111`, initial workflow SHA `a9001058c18831cad5e7ef73b5deb5bad0b2c930`. 23 historic test files' current-world pin updated 44/59→45/60; explicit old43/58 rejection fixture unchanged; 6 active test-world version pins updated. Do not call full suite green until both jobs finish.
- [Y2 genuine 96h farm wage/13 professions #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) independently running older Schema44/Rules59 scenario; read its per-occupation personally owned cash and after72 jobs/deliveries/meals.

**Next priority:** finish **AA real 48h** and 45/60 exact-SHA full tests; if grain return truly delivers bakery bread, separately implement PRE-SIGNED farm employer procurement and **legitimate wage escrow refill** after physical farm food arrival and only on genuine Huda service, never from worker's consigned food. Assess bakery economic loss from 1:1 barter before deciding permanent ratio. Then authentic 96/168h same-genesis full-village survival, drought/bankruptcy and migrations, without relaxing hunger>=90 safety. The [detailed decision](PLAY48AA_INTEGRATION_SECURITY_AND_RECOVERY.md) and [WORK_QUEUE.md](WORK_QUEUE.md) are linked.

---

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
