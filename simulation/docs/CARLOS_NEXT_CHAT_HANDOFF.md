# Carlos RPG — handoff / current technical priority (2026-11-11)

**This file is a pointer, not final truth. VERIFY current GitHub HEAD, CI and pending branches before continuing.** For governing rules read root [AGENTS.md](../../AGENTS.md), [WORK_ROUTING_PROTOCOL.md](WORK_ROUTING_PROTOCOL.md), [WORK_QUEUE.md](WORK_QUEUE.md), [WORLD_FIRST_ECONOMY_PRINCIPLES.md](WORLD_FIRST_ECONOMY_PRINCIPLES.md) and [PLAY48Q causal root diagnosis](PLAY48Q_CAUSAL_FOOD_CAPACITY_DECISION.md).

## Current stage

- Repository: [Carlos-RPG](https://github.com/daboolgame123-creator/Carlos-RPG); `main` must not be changed without authorization.
- Stage: **PLAY-48_OPEN / RELEASE_NO_GO**. Experimental simulation only, P0 production save migration not approved. Historical independent review is deferred by owner. No claim of 7-day 13-NPC economic resilience.
- Persisted world code versions in this experiment: **Schema 43 / Rules 58** (no bump).
- Last proven real 13-person baseline: **PLAY48N code SHA `16b625d31ad7e998802a704dbcba3f59dcc1c7ca`**, genuine 2h personally known wood/charcoal trades and wages; CI 3.10/3.13 green. PLAY48O 96h negative-control verified `066a084b6611c20398e2da6678a59de43f687f6b`, [CI #42907827424](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42907827424). Four-day collapse: 12/13 hunger 100; no new meals, jobs or deliveries after hour 72. A green test is not a green economy.
- PLAY48P forensic logs: two real harvest jobs, 7 genuine grain deliveries and bread baking in 48h, yet bread remains unsold in market while both couriers become hunger-blocked. [CI #42914270367](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42914270367) SUCCESS.
- PLAY48Q necessary 7-day bound: existing 2 fields yield 3+7 (10/day) vs 13/day necessary for 13 NPCs (minimum no effort hunger). With two starting water and six documented future rainfall units, optimistic upper max 55 loaves, while preventing hunger >=90 needs at least 61 meals. A real three-grain opening reserve alone only raises to 58 and is not sufficient. [CI #42916907455](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42916907455), exact source `5ac20345...` SUCCESS.

## Current PLAY-48R experimental work

**Branch** `experiment/play48r-fertile-field-real-harvest-20261111`, forked from analysis `5bd9bd301b271595fee04c886e56b951f46c0c6f`.

- Feature is **opt-in test-world crop yield trial only**, eastern field 7→12 actual grain from one real fully matured, watered and harvested crop at exactly the same 24h growth. No free opening bread, cash, water, seed, workers, roads or time compression; no change to old 3/7 fixture defaults. The soil-productivity assumption is not proof of realistic fertilization, and not a production feature.
- Counterfactual operator-only bound with same water and bounded documented rain: upper seven-day food 55→90, while the no-future-rain case with fertile soil reaches at most 27, still inadequate.
- [48R targeted workflow #42919278865](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42919278865) at exact source `bb86167d43e005f49e942cb5d54cb4a31f7aa650`: bounded genesis/consistency successfully checked on Python 3.10 and 3.13; **48h physical control/treatment A/B still needs final verification**. Never infer it succeeded from successful genesis.
- [48R full pytest #42919617997](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42919617997) on `aa836e46b764a4e4d4d287caf5c43acb51d6c97e` (same simulator/test sources plus workflow): **check both Python 3.10 and 3.13 run results**.
- Technical scope and gates: [PLAY48R_FERTILE_FIELD_TRIAL.md](PLAY48R_FERTILE_FIELD_TRIAL.md).
- Documentation-only commits following the green source SHA are not evidence of independently passing new tests; report true HEAD and exact test SHA separately.

## Next actions (stay within PLAY-48)

1. Verify 48h measured real crops, baking, personal meals, wages and hunger against original at exact SHA, fix any failures before new features.
2. If improved grain quantity does NOT improve actual meals, investigate legitimate physical food access / ownership and verified employer-funded courier meals from H3/K/L without bypassing hunger/safety thresholds.
3. Select a genuinely sustainable soil/water/resource explanation; 12-grain fertile yield is a deliberate *trial parameter*, not a solved medieval resource ecology.
4. Follow with identical 72/96/168h A/B and credible drought/insolvency scenarios; require real post-72 deliveries, jobs, meals and conservation, then full final SHA CI and documented closure decision. Do not start PLAY49 while PLAY48 remains open.
5. ChatGPT leads here; this handoff does not assert any OpenCode agent is currently executing an assigned task.

Do not inflate results or count hypothetical production as inventory. Preserve local NPC knowledge, event-sourced SQLite replay, true copper and food custody, no teleportation, and no `main` merge.
