# PLAY-22 — Finite-food endurance, replay and bounded cost

Date: 2026-11-07. Status: CLOSED_TECHNICALLY / EXTERNAL_REVIEW_DEFERRED_BY_OWNER.
Base: PLAY-21 technical documentation HEAD `5f84b72da6c52eaa429b832468dd53dac49a5728`.
Branch: `simulation-engine-phase-play-22-ecology-endurance`.
This is a disposable-test-only branch, not a canonical story import or production approval.

## Analysis before implementation
- PLAY-21 demonstrates actual local NPC forage, hunger, food knowledge, travel and assistance with 7 independent NPCs for **360 seconds**, conserving 8 seeded units of food.
- The engine schedules bounded NPC events. A long single wait may hit the 1,000-event atomic limit. Replaying an ever-growing SQLite ledger can cost more than the logical simulation itself; the PLAY-20/21 snapshot technique accelerates reads but must never substitute for genesis verification.
- Bread/crop production exists through `NPCProductionService`, but output is site-owned and not automatically transferred into a hungry NPC's personal `food` inventory. Do **not** call these separate mechanics an integrated sustainable food economy. Do not invent wages, goods, deaths, or player health effects.
- Villagers whose hunger saturates at 100 do not die under existing rules. Retaining 7/7 NPC at the end of a long run does not demonstrate survival in the medical sense.

## Bounded implementation batch
| Item | Work | Evidence gate |
|---|---|---|
| 22a | New resumable long-duration (600..7,200 seconds) seven-NPC disposable ecology runner with two explicit Carlos decisions. Keep the PLAY-21 short runner unchanged. | Real separate SQLite sessions, exact logical time and autonomous travel/food behavior |
| 22b | Record immutable private checkpoint samples at 600, 1,800, 3,600, 7,200 seconds (up to requested horizon); verify original 8 food units across wild deposits, NPC ownership, meals and player. | No invented food, no negative stock, same money/bread; account for concurrent failed forage |
| 22c | Snapshot after bounded commands, then compare full genesis replay, load projection and reopened state; explicit resume command advances exactly 10 seconds. | No wall-clock advance, private NPC data excluded from player handoff; duplicate/stale commands reject atomically |
| 22d | Add focused tests on 600..1,800s, deterministic behavior, mode invalidation and privacy, and full real 3,600s CLI scenario for both player choices; print operational wall time separately, never bake timing into deterministic state. | Dual-Python targeted CI and full regression on the exact code SHA |
| 22e | Record findings, actual run duration and throughput limits, and mark status only if all CI jobs pass. | Verified report, updated ROADMAP/WORK_QUEUE with open production/starvation gaps |

## Safety and scope
No extra starting food beyond PLAY-21; no new schema/rules, engine policy changes, NPC personality or medical mechanics. Each wait is <=120 world seconds, local snapshots are replay accelerators only. For a longer horizon, test the actual number before describing it as successful. PLAY-14g, 03-A7c, 03-A, P0 and external review all remain OPEN until independently addressed.

## Verified closure evidence (2026-11-07)

- **Final code/test SHA:** `2639d61437e7086a9ac1223a17789f43b29d2fee`. Schema 34 / Rules 46 unchanged.
- **Full [run 42405841422](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42405841422):** `completed/success`, 1,493 passed in Python 3.10 (755.98s) and 1,493 passed in Python 3.13 (666.15s).
- **Targeted [run 42405841495](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42405841495):** `completed/success`, 34 passed per Python version, plus **two genuine 3,600-second worlds** on each version, with identical deterministic private audit results.
- At t=600 all **8** starting natural/personal food units were consumed or held by Carlos. At t=1,800 all seven NPC hunger values were >=90 in both worlds; there is NO NPC starvation-death mechanic. Under observation NPCs ate 8 meals, compared with 7 when Carlos foraged one unit first. There was no generated stock.
- The complete report is [PLAY_22_ENDURANCE_REPORT.md](PLAY_22_ENDURANCE_REPORT.md). The closest next milestone is a separately designed bounded production/market/ownership-to-meal chain, not an assumption of sustainability. All earlier open health, P0 and review gates remain OPEN.
