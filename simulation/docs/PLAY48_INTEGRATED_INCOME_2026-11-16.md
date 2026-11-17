# PLAY48 integrated income — reopened by owner, 2026-11-16

Status: **IN_PROGRESS / PLAY48_NO_GO**, branch
`integration/play48-sustainable-income-20261116`, base
`1e04e84e180b7ff6fa597aaed6e2605a3ca1dfd3` (PR135).
The new owner instruction explicitly reopens the terminated economic scope.

## Verified baseline and cause

Live GitHub review: PR133 targeted run 43847692517 passed; PR134 targeted
43848484478 passed (Salma actually eats two wages, hunger100 residents 5→4 at
h60). General regressions 43847765210, 43848570441 and PR135 43864385138 failed.
PR135 is instrumentation, not an economic repair. Main is untouched.

Source inspection confirms Nora's `finite-harvest` has no cash agreement;
site cash is not her wallet. Freight food contracts have lifetime limits;
unlimited real delivery does not renew them. The coordinator dispatches
couriers and production before its owned-food consumption pass. These are
separate missing income and consumption edges, not a shortage dashboard.

## Implemented candidate

1. Prospective `ProductionCashWageSigned`: only at time zero, known employer
   ledger, no existing terms/jobs. Actual old `ProductionWagePaid` debits the
   local employer only after authentic completed harvest and worker presence.
2. A distinct recurring freight contract: an actual grain/bread arrival at
   the receiving employer records service, at most one outstanding claim,
   signed interval, local available food, once-only conserved settlement.
   Existing capped provision contracts cannot overlap or be silently renewed.
3. Opt-in early eating before new freight/work; bounded local payroll wait;
   shopping yields to the existing fatigue70 rest boundary. No hunger relief
   without `NPCFoodConsumed` from personally owned food.
4. Integrated scenario signs the above plus Salma's existing two-sales wage.
   Opening resources, ownership, NPCs, roads, needs and metabolism match the
   control exactly. No new coins, food, characters, sites or rain advantage.

## Version contract

Schema45 / Rules70: Rules69 exists on a separate rejected experiment; it is
not reused. New event meanings are not silently applied to old saves.
Repeated assertions in historical tests were inspected as **current writer**
oracles (fresh world/backup creation), then centralized in an independent
`tests/release_contract.py` pin. Historical SHAs, legacy rejection fixtures,
clock constants and behavior assertions remain unchanged.

The new independent compatibility test creates nonempty actual saves with
frozen Rules63 (`b397f40d01a314197f2e22f26f1d27bf64eeed3f`) and Rules68
(`1e04e84e180b7ff6fa597aaed6e2605a3ca1dfd3`). It asserts their original versions,
current-reader refusal with byte-identical source, and exact replay again by
each original reader. No migration is implemented or claimed.

## Verification and acceptance

Local Windows Python3.13: 16 focused tests passed before the bounded-wait
clock-expiry follow-up. Final-SHA CI and long A/B are pending.
The initial broad local baseline was stopped after confirming failures;
its partial output is not a passing full regression.

The runner saves both physical SQLite worlds and numeric JSON checkpoints.
It stops at the first failed gate: after h60 requires fewer starvation cases,
additional genuine cash wages and Nora's additional purchase AND meal,
without reducing bread/meals/sales. Later gates additionally require no
deterioration from h60 and continuing bread, sales, meals and both couriers.
No 96/168h success is inferred from a shorter run.

## Remaining work

### Verified follow-up — 17 November

On `f6b124d74e422824df829a458be81e7519454ef9`, full regression run
[43878111956](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43878111956)
is **SUCCESS on both Python versions**; integrated acceptance
[43878104653](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/43878104653)
is **FAILED**. The Python3.13 artifact gives this unchanged h60 gate result:

| h60 metric | Control | Candidate |
| --- | ---: | ---: |
| Completed bakery batches | 17 | 27 |
| Meals | 22 | 22 |
| Food sales | 8 | 7 |
| Hunger100 residents | 5 | 3 |
| Cash wages (copper paid) | 3 | 3 |
| Nora purchases / meals | 0 / 0 | 0 / 0 |
| Hana / Huda deliveries | 44 / 8 | 73 / 7 |
| Conserved copper | 12 | 12 |

The gate correctly stops at h60: Nora gained no food; no 72/96/168 claim.
Downloaded original candidate SQLite confirms Nora's completed harvest is
unpaid, farm owns only1 against the agreed2 copper, east owns5. Huda's grain
arrivals at approximately24.114/30.031/36.031h produce only one18h-qualified
claim, paid at24.139h. Generic courier work occurs25 times for Hana and17
for Huda; all completed generic actions (including rest) cost85/77 hunger.
These are observed ledgers, not authority to confiscate east funds or change
wage intervals retroactively.

The remaining reviewer P2 was reproduced: second meal at660 seconds for a
whole600 advance versus61 for1+599. The deterministic next-tick wake fixes
it; **20 focused tests passed locally on Python3.10 and3.13**. The conserved
two-loaf player gift exists ONLY in the tiny scheduler regression fixture,
never in original-village acceptance. Reviewer session
`ses_e1b73d1e4ffenpMwbP5Ehm2RnG` confirmed the narrow fix by source inspection,
not independent test execution or production approval.

Focused reviewer session `ses_e1b73d1e4ffenpMwbP5Ehm2RnG` identified two
coordinator defects: new bakery wages were checked after the next pickup,
and the payroll wait did not wake at fatigue/hunger boundaries. Both were
reproduced by failing tests, then fixed. The new tests prove a sole bakery
loaf pays its real grain courier before shipment, visible owned-food eating,
second-interval genuine delivery payment, and whole/split equality across
fatigue69→70. **19 focused tests pass on local Python3.13**. This is a focused
agent review, not external production approval. Superseded CI runs
43876289116 / 43876347501 were cancelled, not passed.

Run exact-head targeted/full CI Python3.10/3.13; inspect first failed economic
checkpoint and repair demonstrated blockers before extending the horizon.
Review new contracts and negative cases, including partitioning and forged
history. No phase closure, PLAY49, merge, production changes or migration.
