# PLAY-48 — final 168 h causal acceptance: `PLAY48_ECONOMIC_NO_GO`

**Date:** 2026-11-12 (UTC). **Status:** `PLAY48_ECONOMIC_NO_GO`; no merge, no save migration, no claim of seven-day recovery. This is a measured engineering disposition, not a simulation rule.

## 1. What was tested

| Item | Value |
|---|---|
| Candidate | PR #90 head `cf92768` (`experiment/play48-preserve-first-market-sale-split-food-wages-20261112`) |
| Engine change in PR #90 | None; the PR adds only the 72 h A/B scenario and workflow |
| Genesis | 13 NPCs; 12 conserved copper; 3 original loaves (1 saleable at market, 1 Huda farm escrow, 1 Hana market escrow) |
| Physical world | East yield 12, West yield 3, growth 86 400 s, well capacity 8, initial water 2, rain 2/day on days 1–3 only |
| Runner | `scenarios/test_village/play48_final_168h_acceptance.py`, six-hour slices, 24/48/72/96/168 h |
| Checks | `_conserve` every slice; `db.verify`; `PRAGMA integrity_check`; `PRAGMA foreign_key_check`; every food-wage payment has an earlier real delivery; per-NPC hunger, personal food, copper scope and affordability |
| Python | 3.13.18 and 3.10.22 |

The run reproduces PR #90's own 72 h candidate row exactly: **jobs 25, Hana 33 deliveries, Huda 7, food sales 7, meals 9, hunger-100 11**. It is the same world, not a divergent fixture.

## 2. Measured curve (Python 3.13)

| h | hunger 100 | food in sites | escrow food | grain | copper | meals (cum.) | food sales | jobs | wages | Hana/Huda deliveries | bread made in interval | grain harvested | affordable now |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 24 | 3 | 0 | 0 | 0 | 12 | 3 | 1 | 6 | 2 | 3/3 | 0 | 0 | 0 |
| 48 | 5 | 8 | 1 | 2 | 12 | 6 | 4 | 21 | 6 | 33/7 | 12 | 15 | 0 |
| 72 | 11 | 6 | 1 | 2 | 12 | 9 | 7 | 25 | 7 | 33/7 | 1 | 0 | 0 |
| 96 | 12 | 6 | 1 | 2 | 12 | 9 | 7 | 25 | 7 | 33/7 | 0 | 0 | 0 |
| 168 | 13 | 6 | 1 | 2 | 12 | 9 | 7 | 25 | 7 | 33/7 | 0 | 0 | 0 |

At 168 h the SQLite state is at revision 15 675; `PRAGMA integrity_check` = `ok`, `PRAGMA foreign_key_check` = 0 rows, `_conserve` passes, and all 12 copper remain. The 168 h row is loaded from the same lineage as the 24–96 h run (102 h snapshot advanced to 168 h); it is not a counterfactual.

Python 3.10 reproduces the 24 h, 48 h and 72 h rows exactly (3/0/0/0/12/3/1/6/2/3/3; 5/8/1/2/12/6/4/21/6/33/7/12/15; 11/6/1/2/12/9/7/25/7/33/7/1/0). The 3.10 process was stopped after 72 h because the terminal state was already established; 96 h and 168 h are 3.13 measurements. This is a cross-version limitation of the evidence, not a disagreement between versions.

The 24 h zero is a timing artifact, not a capacity verdict: the first crop matures at 24.03 h. Day 2 is genuinely productive — **15 grain harvested and 12 bread baked** — yet 5 residents are already at hunger 100. From 72 h onward there is **no production, delivery, sale, wage or meal at all**.

## 3. Why PR #90 fails

### 3.1 Physical food is not the binding constraint at 48 h

At 48 h the village owns **8 loaves at market + 1 escrow + 2 grain**, has just baked 12 loaves, and still has **5 residents at hunger 100**. At 96–168 h it owns **6 loaves + 1 escrow + 2 grain + 2 ripe crops**, 4 water at the well, and **12–13 residents at hunger 100**. Starvation coexists with physical surplus.

### 3.2 Zero-income residents cannot clear the market

- 12 copper total, bread price 2, wage 2. Seven of 13 residents start with zero coins; only three start at the market and only two of those have coins.
- At 78 h the market holds **5 loaves and 6 coins** with an open 5-unit offer at 2 coins. Twelve residents hold **zero personally spendable copper**; the only solvent resident (Basim, 2 coins, hunger 54) is not hungry enough to buy and cannot buy for others.
- The market has no payroll. Its coins accumulate from sales and cannot become resident income; the seven residents whose roles have no complete buyer/income chain (guard, merchant, explorer, miner, smith, repairer, burner, woodcutter) never earn a bread claim. Terminal `repaired_gear` has no buyer.

### 3.3 Couriers starve on the intentional guard

Hana and Huda each receive one opening loaf and eat it around 12 h. There is no standing delivery food wage. By 72 h both are at hunger 100 at the well; the existing `hunger >= 90` courier guard blocks new cargo, so **all deliveries stop after 48 h**. One food unit remains in escrow but cannot be earned because the couriers cannot travel. The guard must not be disabled to fake recovery.

### 3.4 The chain then freezes

At 78 h both farms have ripe crops, but the farmers are at hunger 100; 4 water sits at the well and the fields have none. At 96 h and again at 168 h the cumulative counters are identical to 72 h: **0 meals, 0 sales, 0 jobs, 0 wages, 0 deliveries, 0 production**. At 168 h all 13 residents are at hunger 100 while 6 loaves, 1 escrow loaf, 2 grain and 2 ripe crops remain. This is the same post-72 terminal state previously recorded, now reproduced on the latest candidate through the full seven days.

## 4. Exact design decision required

The current market-only institution cannot convert a physical bread surplus into meals for zero-income residents. A code patch that preserves ownership, price, no minting and the hunger guard cannot close that gap. One of these must be authorized before another engine candidate is meaningful:

| Option | Decision | Physical basis |
|---|---|---|
| **A. Funded food entitlement / food-for-work (recommended)** | A village granary or public-works program pays **1 loaf per completed real task** (water haul, harvest, courier delivery) from **existing** market/bakery stock, capped at about 1 loaf per person per 1.5 days. Physical presence, ownership, hunger/fatigue and event logs unchanged. | Day-2 measured output is 12 bread/day; the capacity note's minimum is 61 meals over seven days (~8.7/day), so the existing fertile field can fund it. |
| **B. Income redistribution / market payroll** | Give the market a real payroll funded by sales (e.g. 1–2 coins per real delivery/water haul), and/or set bread price 1 and wage 1 so 12 coins can clear 12 loaves/day. | 12 conserved copper; requires explicit approval to change price, wage and initial coin custody. |
| **C. Population/role reduction** | Reduce the 13-NPC fixture to the residents with a complete income chain (about 4–5 today), or add external buyers for fittings/repaired gear. | Avoids inventing demand; changes the accepted 13-NPC baseline. |
| **D. New physical food source / water** | Only if A/B are rejected. Add a real fishery/ecology or inter-village import with finite stock, labor, routes and provenance. | Not the first blocker: the fertile East field already produced 12 bread/day; water and labor, not grain yield, stopped day 3. |

Without A, B or C, the 13-NPC world will keep reproducing the same 72 h freeze: physical food remains, zero-income residents starve, and the couriers who could move it are blocked by the hunger guard.

## 5. What would count as GO

Repeated post-72 bread/grain production, real deliveries, wages, sales and meals at 96 h and 168 h; zero residents at hunger 100 (or a pre-agreed threshold); at least one personally affordable buyer at each checkpoint; 12 copper conserved; SQLite reopen/replay and integrity checks green on Python 3.10 and 3.13. A one-time opening rescue or a green CI run is not GO.

## 6. Artifacts

| Artifact | Location |
|---|---|
| Acceptance runner | `simulation/scenarios/test_village/play48_final_168h_acceptance.py` |
| 3.13 log | `final168_p313_wal.log` + `final168_row.log` (operator artifacts, not committed) |
| 3.10 log | `final168_p310_wal.log` (operator artifact, not committed) |
| 168 h row | `final168_row.log`: `INTEG ('ok',) FK 0`, revision 15 675, 13/13 hunger 100 |
| Branch/commit | `experiment/play48-final-168h-no-go-20261112` @ `469f5d9` (pushed) |
| PR | Not opened: this runner has no authenticated GitHub session. Create/compare: `https://github.com/daboolgame123-creator/Carlos-RPG/compare/main...experiment/play48-final-168h-no-go-20261112?expand=1` |

No merge, no release, no save migration. `PLAY48_ECONOMIC_NO_GO` remains in force until the design decision in §4 is made and a new candidate is measured through 168 h.
