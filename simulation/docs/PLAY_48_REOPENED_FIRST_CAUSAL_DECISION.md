# PLAY-48 reopened — first causal decision (2026-11-11)

Status: **DIAGNOSIS_RECORDED / ENGINE_CHANGE_NOT_YET_PROVEN / ACCEPTANCE_NO_GO**.

## Baseline evidence cross-check

- Genuine 13-NPC 96h Y2 A/B: both arms 13/13 at hunger cap; 72–96h zero new jobs, deliveries, meals, or market trades. Finite farm wages improved cumulative deliveries 3→12, jobs 20→24 and meals 5→7, but did not restart circulation. See `PLAY_48_PHASE_TERMINAL_DISPOSITION_2026-11-11.md`.
- H2 72h read-only access audit: personal affordability collapsed (>=2 spendable copper: 2 residents at day1, zero at day2/day3), while 12 copper remained conserved globally; market held 3 saleable loaves plus one reserved employer loaf, couriers reached hunger 100 and movement guard rejects >=90. See PR #74 and `PLAY_48H2_FOOD_ACCESS_DIAGNOSIS.md`.
- AC Rules61: physical bakery→farm return delivered 2 real loaves, from 3 earned grain claims; bakery shop stock 7→5; 12 copper conserved. Farm ownership is **not** worker ownership and no new earned farm wage is implied. See `PLAY_48_PHASE_TERMINAL_DISPOSITION_2026-11-11.md`.

## Causal constraint chain

Physical food production and transport are possible; that alone is insufficient. Employer inventory must become **authorized, earned, personally accessible** worker food before the hunger travel guard prevents employment. Other residents require their own real means of exchange or legitimate work. Money held by an employer, market, or courier in custody is not personally spendable by an insolvent NPC. Do not 'fix' this by lifting the guard or transferring the farm loaves without service.

## First implementation target

**Inspect existing real farm wage contract and AC delivered bakery bread state**. At the first physically arrived FARM loaf, determine whether a *new* well→farm water service can be signed against one unreserved FARM-owned loaf, accepted by a genuinely eligible worker, then paid exactly once upon an authoritative delivery receipt. Only if this works and improves the first genuine 96h causal cut-off should the intervention be extended to other professions; do not create a new occupation or currency source.

Required negative tests: loaf already promised, no physical arrival, unsigned/duplicate/old receipt, service not completed, worker not at site, courier cargo still entrusted, employer no longer owns loaf, worker >=90 hunger and no legitimate recovery route, duplicate payment after replay. Distinguish inability to start a job from wage settlement.

## Experiment contract

One unchanged original genesis/weather 13-NPC control and one opt-in candidate; record actual 24/48/72/96 and 120/144/168h checkpoints, per-NPC food, spendable copper, hunger, location and route knowledge, all stock ownership/custody, new post72 jobs/food consumption/trades/courier movements, conservation and deterministic SQLite replay. A green pytest job with all residents starving is **economic FAIL**.

No code changes or tests are claimed by this diagnosis. Next step is targeted source inspection and isolated runtime implementation, then exact-head CI on Python 3.10 and 3.13. PLAY49 and main remain blocked.
