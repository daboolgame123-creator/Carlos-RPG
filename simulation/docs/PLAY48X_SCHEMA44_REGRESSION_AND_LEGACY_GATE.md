# PLAY-48X — new version contract vs historical save compatibility

**Date:** 2026-11-11. **Status:** `PLAY48_OPEN / RELEASE_NO_GO`. This branch makes *no engine or economy-rule changes*, and is not a migration authorization. The new employer-wage experiment remains behind opt-in flags and persists **Schema 44 / Rules 59**. Production and older independently approved worlds remain **Schema 43 / Rules 58**; no `main` merge.

## Why the first full regression failed

[Original PLAY48V full CI #43007340412](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007340412), base `60f5650bdbbeabc47726f3ca8f12d22a415db7c0`, failed on **33 historical tests, 1,661 passed** for **each Python 3.10/3.13**. The log explicitly identifies old *current-version* expectations `43/58` in 23 test files, plus two `Rules58` current-candidate version pins inside `.github/workflows/simulation-tests.yml`. Do not conflate these failures with a newly observed breach in wage conservation; they are also NOT evidence of successful save migration.

This branch updates ONLY fresh/current-world version checks to `44/59`, preserving tested historical predecessor SHA/Rules pins (for example Rules18), deliberate old-version SQLite corruption values, the original 43/58 frozen checkout, and all domain/game rules. The patch comprises **23 test files**, **two current candidate workflow pins**, one new negative save-safety test file, and a dedicated exact-head CI. The version check remains **explicit** and can detect a future unreviewed bump; assertions are not deleted or made tautologically dynamic.

## Verified negative compatibility behavior

[Current PLAY48X run #43014260381](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43014260381) at source `b939992d9d342175d042cb206e4c545fc4ea2a15`:

- Python **3.10** and **3.13** dual green short jobs: checkout frozen old source `aa836e46b764a4e4d4d287caf5c43acb51d6c97e`, create and verify an **actual old 43/58 SQLite save**, then try to verify it under the new 44/59 code. Both must get `UnsupportedVersion`, and the old SQLite file must remain byte-for-byte unchanged. This is a verified *rejection gate*, **not** a migration or ability to play old worlds in new rules.
- Two additional synthetic current-world/version gate tests passed each Python, checking clean 44/59 replay and rejection of a hash-consistent older header.
- Full historical + newer current-world pytest on this exact head was **still running at the time of writing**. Do not claim the prior 33 failures are closed until the new Python 3.10/3.13 full-suite jobs report success and counts are recorded.

## Independent genuine economy evidence

- [PLAY48U real 48h #42999941836](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42999941836) SUCCESS 3.10/3.13: authentic market salaries funded 2 new personally owned Hana meals; total meals 6→8, Hana hunger100→60, village hunger100 5→4; **no increase in 35 true deliveries** over control, Huda still hunger100.
- [PLAY48W actual two-market-courier 48h #43007695830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007695830) SUCCESS 3.10/3.13: both real existing workers pre-signed with *different* genuine initial allocation of exactly the original 3 loaves; W control and W treatment identical initially. Hana gained two more funded meals and hunger improvement, **Huda collected zero wages** at market, stayed hungry100 and completed only 3 deliveries, because her physically reached worksite/service trajectory did not make her eligible for that market payout.
- [PLAY48V 96h experiment #43007291657](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43007291657) on source `37cd8fb5a1d5fed140a3c5d9ec19b4cac164e0a3` was **in progress**. It separately measures whether Hana's real new wages produce post72 work, deliveries and meals; a green diagnostic job can still show failed economic recovery.

## Next admissible work

1. Confirm full exact-head historical regression 3.10/3.13 before integrating this version-contract maintenance into an eventual reviewed code branch.
2. Preserve an **explicit, independently reviewed** future migration policy for user saves; old-world rejection is necessary but not sufficient.
3. Repair **actual worker-site food access**, especially Huda's legitimate farm-water service, rather than signing unreachable market pay contracts or teleporting owned goods. No arbitrary food, wages or lowered hunger values.
4. Require 96/168h authentic physical simulation and non-minted multi-profession earnings before PLAY48 closure. Preserve true scarcity, injury, rainfall and insolvency failure cases.
