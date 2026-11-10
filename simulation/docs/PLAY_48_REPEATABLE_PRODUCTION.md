# PLAY-48 — Bounded repeatable physical production and real demand boundaries

**Date:** 2026-11-10 UTC  
**Phase status:** `PLAY48_OPEN / RELEASE_NO_GO`. These are **disposable test worlds**, not production-save migration or a self-sufficient village. No engine rules, Schema 42 / Rules 57, `main`, or player story changed.

## Baseline and scope

Branch `feature/play48-repeatable-physical-loops-20261110` starts at verified PLAY-47 integration `1dd038d731c5072edb9eea43d29e5b3e70436d79`. PLAY-47 was technically closed (external review deferred) on `38ef0049478e4d62fd465dadc7c1eaf406b9b4d2`. Finite scarcity, including a food shortage and 13/13 hunger-cap residents at day seven, is the historical measured outcome, **not** proof of economic recovery.

PLAY-48's objective is two or more real, authorized, locally traded and physically timed material cycles if finance, labor and demand permit, **without inventing supply, wages, buyers or routes**. Existing `ProductionStarted`, `MarketTradeExecuted`, `ProductionWagePaid` and physical movement reducers remain authoritative.

## Verified scope: 48-A, two independent raw-material loops

[GitHub Actions 42808944705](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42808944705) **SUCCESS** on Python 3.10 and 3.13; exact test SHA `8aa03adc41a6e69f24eea6307aa9141c2bb343fa`. Extended compound test at SHA `8ab782de656f26a87b11eadf24b299467b8b4d57` passed [CI 42809457769](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42809457769), **51 passed and 1 expected skipped** on each Python.

Authentic 6-NPC PLAY-45 physical world; no NPC is moved or told to shop after time-zero initialization. Finite tested inputs and wallets are explicit:

| Initial supply | Saw-board / wood bought | Smelting / ore bought | Built frames | Repaired gear | Total copper |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 wood + 1 ore, 6 copper | 1 | 1 | 1 | 1 | 6 |
| 2 wood + 2 ore, 12 copper | 2 | 2 | 1 | 1 | 12 |
| 0 wood + 0 ore, 12 copper | 0 | 0 | 0 | 0 | 12 |

With two source units, **two separately scheduled real lumber/carpentry cycles and two actual ore/forge cycles** occur. Two site-paid wages per upstream workshop are backed by physical receipts. Finite downstream builder and repair demand only consumes **one** plank and one fitting: remaining plank/fitting stay in the real workshop site inventory; frame and repaired gear remain at their actual sites. This is an honest **demand ceiling**, not a scheduler failure.

Adversarial guards: zero starting worker cash in (0/0), (0/2), (2/0) configurations forbids corresponding production, even if supplier stock is positive; no free credit. Replaying the final high-level clock command raises DuplicateCommand and does not add a receipt. Full SQLite `verify`, `snapshot`, `integrity_check` and `foreign_key_check` pass; source materials conserved against all started jobs.

## Verified scope: 48-B, real compound ore + charcoal

Initial **2 ore + 2 charcoal + 8 copper** across an autonomous 5-actor professional world. The blacksmith makes four personally routed, local purchases (ore twice and charcoal twice) and finishes **two distinct compound smelts**. Each job debits 1 ore + 1 charcoal atomically and uses the one real anvil, with correct per-input receipts. One finished fitting is locally purchased and repaired at the actual repair shop; one remains unsold at the forge. The real two-copper fitting sale funds **two separate one-copper wages**, leaving zero in the forge till; there is no duplicated receipt or unfunded salary. No direct NPC commands after genesis.

Result: [GitHub Actions 42809457769](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42809457769), Python 3.10 + 3.13, **SUCCESS**; 51 tests passed, 1 deliberately skipped (external predecessor fixture) on each. An initial experimental assertion wrongly assumed that one sale can fund only one wage; the actual two-copper proceeds legitimately funded two wages. [Failed probe 42809272354](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42809272354) was corrected by checking both source and destination copper receipts, not weakening the ledger.

## Third strand: 48-C, real 96h systemic blocker

A separate negative-control test `test_play48_post72_blockers.py` runs the *actual PLAY-47 13-resident* world to 96 simulated hours, daily SQLite close/reopen/full-replay, with only documented 2+2+2 bounded units of rain. It compares days three and four, courier health, deliveries, food stocks, sales, wages, job output, and copper conservation. **The 96h job is not yet a verified success at the time of this report**: [GitHub Actions run 42808714301](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42808714301). Its exact SHA is `20170febecc72657293c9fd8b4f3e9ef4e0fa119`.

Even a green negative-control run would not be a fix. PLAY-47 already demonstrated that hunger and lack of locally owned affordable food halt couriers despite unsold food; reserved consignment copper cannot be used as an NPC wallet. A valid next **gameplay implementation** needs a documented, funded and uniquely receipted food-access/transport contract and/or a genuine locally backed construction/repair buyer. It cannot inject food at t>0, let the courier spend entrusted copper or create free sales merely to show activity.

## Remaining gates before PLAY-48 technical closure

1. Close/check the real 96h run and any failing assertions on its exact source; document whether day-four recovery exists (do **not** assume yes).
2. Develop and test at least one **legitimate downstream demand/consumption or contracted funding** path that allows a second *full* builder/repair cycle, if physical resources and finance permit. Terminal goods must be used/sold for a real reason, not deleted by a test.
3. A true post-72h recovery claim needs at least **one real delivery after hour 72 plus attributable later work, sale or meal**, independently compared against the unrecovered control; if not physically feasible, document quantified blocker instead.
4. Run targeted + full historical suites, including authentic old-world refusal, replay, aliasing and 7-day endurance as relevant, Python 3.10 + 3.13 on final exact HEAD. Follow branch's work queue, review and protection gates.
5. External independent review, real Windows/power-loss production saves and `P0_PRODUCTION_NOT_APPROVED` remain separate release restrictions. No auto merge into `main`.

**Decision now:** 48-A/B bounded physical-production evidence verified on earlier exact SHAs; **whole PLAY-48 remains OPEN** and no sustained seven-day or P0 approval is claimed.
