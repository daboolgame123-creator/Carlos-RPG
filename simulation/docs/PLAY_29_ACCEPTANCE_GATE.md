# PLAY-29 — Technical closure and evidence ledger

**Final decision (2026-11-08): `PLAY29_CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER`.**
**Scope:** frozen per-world *experimental* hunger-time and action-cost calibration, physical resource/replay safety, and a measured seven-day failure-mode observation. **NOT FOOD SELF-SUFFICIENCY.**
**Tested engine source:** `1a4a4021367c670781eea5dee030fe9d93e65f37`; seven-day test-only scenario/workflow source `d67fefc09dddb17175e3799492167e4d4b03196c`; **Schema 39 / Rules 51**. This documentation commit has no engine modifications.

## Final acceptance evidence

- [Full regression CI #42476104910](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42476104910): `completed/success`; 1,670 tests on Python 3.10 and 1,670 on 3.13, total 3,340; no failures. This suite checks prior version compatibility/fail-closed, event/replay behavior and other engine regressions at the specified source SHA.
- [Controlled 72-hour A/B #42475946942](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42475946942): `completed/success` for both Python versions; test SHA `e3d023aa077db3fc544fc6a4271a7575140f4cd7`. Both worlds share the **3,600-seconds-per-hunger-point** opt-in clock; only the activity surcharge differs (100% historical versus 20% experimental). At t=72h, NPCs at hunger=100 fall 7→0; high-risk 7→1; personal provisions 0→5; meals 42→38; matured crops 2 in both. This does **not** change legacy defaults.
- [Seven full logical days #42476455377](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42476455377): `completed/success` on Python 3.10 and 3.13, each with identical day-by-day output. Seven independently acting NPCs; 42 initial personally owned food units (6 each); one soil plot, one seed, two water units, real paths, courier, production and SQLite replay; **no invented rain or replenishment**. The successful assertion is simulation integrity, **not prevention of starvation**.

## Seven-day observed output — both Python versions identical

| Day | NPCs hunger=100 (out of 7) | High risk | Personal food remaining | Meals cumulative | Matured crops | Courier deliveries |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 29 | 13 | 0 | 2 |
| 2 | 0 | 0 | 16 | 26 | 1 | 4 |
| 3 | 0 | 1 | 5 | 38 | 2 | 6 |
| 4 | 1 | 5 | 2 | 41 | 2 | 6 |
| 5 | 5 | 5 | 0 | 43 | 2 | 6 |
| 6 | 6 | 6 | 0 | 43 | 2 | 6 |
| 7 | 7 | 7 | 0 | 43 | 2 | 6 |

One known site-owned food unit remained on days 2–7, but it was **not accessible personal nourishment**. The provenance audit remains balanced: 42 initial food + 2 biologically matured crops = 43 consumed + 1 site stock. The courier stops delivering after day 3 when the finite supply is exhausted; the field stops producing once its two units of water have been consumed.

## Closure conclusion and limits

**PASS**: explicit time-zero-only immutable optional calibration; lower hunger-cost settings measurably affect 72-hour NPC behavior; legacy defaults preserved; full-regression compatibility and SQLite conservation/replay gates pass; seven-day simulation faithfully exposes scarcity. No change to main, original story, or production saves.

**OBSERVED FAILURE OF SUSTAINABILITY (not a failure of this calibration acceptance gate):** all seven NPCs reach maximum hunger by day 7. The new calibration does **not** resolve agricultural capacity, water availability, purchasing/distribution or future death/injury mechanics. No approval for an actual live canonical long-lived world.

**Deferred:** independent external review by owner; production backup/restore P0, Windows recovery and network authentication. Any future production use remains blocked.

**Next independently scoped milestone:** sustainable, land/water/labor/transport-constrained food production plus actually accessible distribution; compare NPC health over long logical horizons. Do not create water, copper, food or instantaneous crops via narration, configuration or untrusted events.
