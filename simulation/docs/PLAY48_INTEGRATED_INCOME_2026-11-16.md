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

Run exact-head targeted/full CI Python3.10/3.13; inspect first failed economic
checkpoint and repair demonstrated blockers before extending the horizon.
Review new contracts and negative cases, including partitioning and forged
history. No phase closure, PLAY49, merge, production changes or migration.
