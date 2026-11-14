# PLAY-48 — Causal recovery, not isolated starvation patches
Status: EXPERIMENT_OPEN / ECONOMIC_NO_GO / NO_MERGE
Decision date: 2026-11-14

## Verified diagnosis (original 13 NPCs, no runtime grants)
PR #107 / CI run 43525811446 reproduced at simulation hour 72:
- 8/13 original NPCs at hunger 100, all eight owned zero copper and no personal food.
- Market still physically held 10 food units; not all starving people were at the market.
- Work and wage/sales continuation, not only food output, must be restored.
- PR #106's two-employer trial did NOT prove a second true market delivery wage for Huda; that targeted check failed. Overall test suites passing does not override this acceptance failure.

## Two causal candidate mechanisms, no arbitrary resources
A. **Immediate paid-shift precedence** (experiment in PR #115): a still-capable worker at hunger 75–89 may start a real local on-duty production job ONLY when exact materials/tools and a real wage source are available. Existing 36-hour food-wage cooldown, owed cash, injury, fatigue, danger and the hunger 90 hard stop continue to apply. Production/food-pay reducers authorize and conserve all transfers. The feature is off by default.
B. **Employer-funded access to essentials** (NOT implemented): if A does not restore the loop, consider a world-local, pre-agreed service job that pays an eligible worker from unpromised employer stock or existing copper after an independently verifiable completed shift/delivery. An unemployed worker must first find legitimate employment through known roads and personal/local knowledge; no free universal ration or invented pay event. Build only after current measured gate, not as a speculative feature.

## Experiment and release gates
1. Fast pure-selector checks: original 13-person source, funded wage, missing input, missing cash, fatigue, hunger >=90, default opt-out.
2. Fast 3-hour A/B: same authentic genesis, one explicitly recorded test-world hunger precondition, real timed work, earned food receipt, actual meal and SQLite replay. This is only a causal probe, **not** economy recovery.
3. If A demonstrates benefit, 24/48/72/96/168-hour authentic original 13-person tests with unchanged initial resources, known roads, real employers, no runtime grants, 12 conserved copper, bounded ecological food, reproducible event history and SQLite integrity.
4. For PLAY-48 closure, show repeatable genuine jobs, wages/deliveries, sales and meals **after hour 72**, nonzero economic circulation and absence of the starvation/deadlock pattern at hour 96 and 168. Never downgrade existing phase requirements.
5. If targeted or long-run tests fail, log why, discard the faulty mechanism, pivot to B if justified. Do not turn a cosmetic 3-hour improvement into RELEASE_GO.

All code and tests remain in a draft PR. No change to main or original story.
