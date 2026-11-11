# PLAY-48 — Final bounded acceptance decision for physical farm food transport

**Date:** 2026-11-11. **Scope: finish the extended farm grain→bread transport task without stretching it into infinite unrelated experiments.**

## Decision

**Farm grain-for-bread physical transport: ACCEPTED AS A SUCCESSFUL 48-HOUR EXPERIMENT on Python 3.13**, conditional on completing exact-head dual-Python acceptance. **Village 7-day self-sufficiency: NOT ACHIEVED / RELEASE_NO_GO.** Do NOT describe this as PLAY48_RELEASE_GO or merge `main`. The prior technical investigation may be stopped with a recorded negative endurance finding; there is no mandate to keep opening experimental wage tweaks indefinitely.

### Real proof, not a synthetic fixture

[PLAY48AC real 13-NPC 48h run #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878), source SHA `c9577d9870799d2f8b57db73416f663bb1b796cc`; job Python3.13 `130596161746` **SUCCESS**. The logged `PLAY48AA_GENUINE_13NPC_BAKERY_TO_FARM_GRAIN_FOR_BREAD` reports:

| After physical time | Baseline (no signed return) | Signed farm bakery return |
| --- | ---: | ---: |
| 24h bakery→farm delivered bread | 0 | 0 |
| 48h authentic farm-grain-related bread claims | — | 3 |
| 48h physically delivered fresh bread to farm | 0 | **2** |
| 48h farm-owned fresh food | 0 | **2** |
| 48h market food | 7 | **5** |
| 48h genuine bakery batches | 10 | 10 |
| 48h total personally consumed village meals | 6 | 6 |
| 48h real Huda deliveries | 10 | 10 |
| 48h real Hana deliveries | 25 | 25 |
| 48h total copper, including all owners | **12** | **12** |

**Interpretation:** The new signed freight policy genuinely moves **two already produced and bakery-owned loaves across a recorded real road**, not to thin air. The cost is equally real: **2 fewer loaves available in the market**. The transfer does **NOT** automatically pay Huda a new wage or increase her meals. The same village is still economically vulnerable. Claims3 vs arrivals2 means one unfulfilled entitlement remains at hour48 and is NOT interpreted as an inventory item.

The preceding [PLAY48AB run #43037662900](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037662900) FAILED dual Python because a stale fixed-index event encoded COPPER for a signed FOOD return. `choose_cargo_manifest` in PLAY48AC fixes the controller/reducer disagreement without weakening the reducer.

### Independent compatibility/security proof

- [PLAY48AC targeted short Python3.10+3.13 #43041990878](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43041990878) SUCCESS both.
- [PLAY48AC integration exact-head Rules61 #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485) confirms initial short provenance and cargo/property tests SUCCESS both Python3.10/3.13, and genuine frozen Rules60 SQLite saves **refused by Rules61 without changing any bytes** on both. Genuine 48h and full historic regression jobs were still **RUNNING at this dated observation**. Check job conclusions before promoting the full Rules61 source.
- [Prior Schema45/Rules60 history #43037819648](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43037819648) SUCCESS 1,696/1,696 tests **on both** Pythons but is NOT a substitute for newer Rules61 exact-head regression.
- Original **Schema43 / Rules58** saves are not migrated; later **44/59, 45/60** rejected deliberately. `main` remains unchanged. The code is experimental Schema45/Rules61 and requires migration review before deployment.

### Explicit unavoidable negative economic result

[PLAY48Y2 genuine 96h A/B #43028088939](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43028088939) verified on both Pythons that two genuinely funded farm-worker loaves help Huda transport 12 rather than 3 deliveries (and cumulative village meals7 vs5), **but BOTH villages end day4 with 13/13 hunger100, and zero new work, shipping, consumption or trading after hour72**. More grain production or one-off loaf delivery alone does not establish a real multi-day self-funding economy. There is **no genuine verified seven-day self-sufficiency result** and zero justification for release.

## STOP RULE — no more endless experiments inside this handoff

1. **Finish only live acceptance checks** on [Rules61 run #43043085485](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43043085485): exact-head Python3.10/3.13 historical and actual 48h A/B. On any real failure, fix only that demonstrated defect. No new unrelated projects or open-ended tuning.
2. Once dual-Python positive real arrivals and full regression are green, record **`PLAY48_TRANSPORT_CLOSED_TECHNICALLY`** and freeze the exploratory transport branch. Do NOT imply `PLAY48_ECONOMY_RECOVERED` or release availability.
3. If the remaining CI fails or remains unavailable, retain **`PLAY48_TRANSPORT_READY_FOR_ACCEPTANCE`** with explicit failed/pending checks; never invent an all-green CI claim.
4. Treat future *legitimate funded recurrent wages, bread-for-grain business viability, social incomes, insolvency/drought and true 168h endurance* as a **separately approved next bounded project decision**, rather than quietly appending endless sub-stages to this same transport task. Do not start PLAY49 automatically or violate user's rule on unclosed phases.
5. Keep true bread/copper conservation, confirmed owner consent, actual routes and protected consumer offers. No wage creation, cargo consumption, hunger/safety bypass, speculative production save migration, or unreviewed merging.

**Release assessment:** `PLAY48_ENDURANCE_NO_GO / PRODUCTION_MERGE_NO_GO`. A truthful bounded engineering success can coexist with economic failure; the latter must not be concealed to declare phase-wide success.
