# PLAY-48H — real day-four result, bounded wage prototype, release gates

**Evidence date:** 2026-11-10 UTC.  
**Experiment:** `experiment/play48h1-13npc-day4-counterfactual-20261110` at `96010a956a8121df9355f1d254af0a43cce6a0dd`.  
**Proof:** [Actions #42832657469](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42832657469), PASS on both Python 3.10 and 3.13. The green CI means that the comparison and invariants **passed**, NOT that the NPC economy recovered.  
**Version:** prototype Schema 43 / Rules 58, separated from production 42 / 57.

## Genuine controlled 13-NPC facts

Both branches start from the same persisted trusted 13-NPC genesis, with 3 genuine market loaves, 12 copper, real farm/courier infrastructure and exactly matching time and observed rain. The only intervention is a **time-zero signed transfer of two already owned market loaves into on-site employer escrow** for two existing couriers (one reserved loaf each), instead of creating more food or any cash. The worlds evolve using the original independent NPC planners until 96h.

| Causal measure | Control 72h | Treatment 72h | Control 96h | Treatment 96h |
| --- | ---: | ---: | ---: | ---: |
| All real trades | 8 | 8 | 8 | 8 |
| Completed production jobs | 15 | 15 | 15 | 15 |
| Meals actually consumed | 5 | 6 | 5 | 6 |
| Courier Hana deliveries | 25 | 25 | 25 | 25 |
| Courier Huda deliveries | 3 | 3 | 3 | 3 |
| Market saleable food | 5 | 3 | 5 | 3 |
| Paid food-wage receipts | 0 | 1 | 0 | 1 |
| Employer-owned, unredeemed escrow | 0 | 1 | 0 | 1 |
| Hunger exactly 100 / 13 | 12 | 12 | 12 | 12 |
| Copper total | 12 | 12 | 12 | 12 |

The treatment's **one genuinely paid loaf** caused one additional *real meal* before the collapse, but no extra job, sale or physical delivery after 72h. Both economies remain stalled 72→96h and 12 residents remain at maximal hunger. Note that **treatment market stock is three, not five**: one unit moved into a worker's possession and was eaten, while the other unit is still employer escrow; they did not vanish or spawn. All food/grain, crop, rain/water and copper conservation gates, SQLite replay/reopen and split-time day-four parity passed.

**Decision:** `PLAY48_H1_PHYSICAL_PAY_VALID / POST72_RECOVERY_NOT_PROVEN / PLAY48_OPEN / RELEASE_NO_GO`. This is **not** `PLAY48_CLOSED` and does not authorize PLAY-49.

## Why H1 fails as an economy restart

The service-backed payment reaches only a worker who has already finished a *real food delivery physically at market*. The original 13-NPC diagnostic observed eligible market-food deliveries only after the first full day and recorded rain; the wage is too late and too small to protect a two- or three-day hunger spiral. A one-loaf-per-courier contract funded from three original loaves is a **finite compensation policy**, not an independent replenishment, steady income stream or a replacement for market access. Workers with no physical delivery cannot self-award site food. A recovery test must not compensate by ignoring ownership, adding invisible supplies or forcibly moving or feeding NPCs.

## Regression gate diagnosis

H1 full [Actions #42831997022](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42831997022) executed 1,694 historical Python tests on each supported version, with **1,661 passed and 33 failed on each**. The listed failures are current-version **hardcoded 42/57 assertions and current CI pin to 57** after the explicit 43/58 prototype bump. No functional market/courier failure has been established by that run; nonetheless full CI is RED. Do not assert green full CI, and do not paper over a genuine old-save refusal test.

A separate `integration/play48h1-43-58-regression-gates-20261110` branch updates only current-version pin expectations and CI assertions; it deliberately **does not** change authentic old-world historical version snapshots or source reduction rules. The target and full suites must prove correctness on the exact new SHA. The still-separate P0 save migration is not a precondition to testing disposable 43/58 worlds, and any real 42/57 production file continues to be rejected until explicitly migrated.

## Next root-cause engineering experiment — NOT a parameter hack

Study the **real point of hunger and payment failure before 72h**: who physically owns market food, who can spend *personal* rather than entrusted copper, which workers can reach the stall before they are too hungry to travel, which employer can pay for validated labor, and how production receipts translate to buyers' spending and actual eating. Prioritize end-to-end local accessibility and real funded work for both couriers and essential producers, not arbitrary per-tick stipends or multiplying a hardcoded loaf. Any proposed repair requires explicit funded title, locally available inventory, physical road travel, cash/food conservation, event-level causal proof, and a new actual 13-NPC 0→96h controlled fork. Finish final regressions before claims of closure.

**No main merge. No PLAY-49. No production save approval.**
