# PLAY-47 closure execution evidence

Status: **OPEN / RELEASE NO-GO / VERIFICATION_PENDING**. Schema **42** /
Rules **57**. No PLAY-48 work, `main` update, story change or production approval.

## Analysis and scope

The checkout initially opened on `main` at `25059fa`. The integration branch
was fetched from `origin` and verified at `b326c5ea2f685697c04ed24f6bc961043bee15ab`.
The stacked heads were still #57 `51cdc3b02fb1d891398a5258b954b554d61a4a4d`,
#58 `21e8b0236a952d6dd038bf3a076c354b4e4fbbd2`, and
#59 `77ddb54b82038075c2d9ec642b8d0dcd3b75c43d`.
Integration must remain a verified fast-forward; the new candidate branch is
`feature/play47-closure-verification-20261109`.

This batch checks five related tasks: stack provenance/CI, existing courier
funding boundaries, incoming-custody rejection, seven-day scarcity with a dry
control, and SQLite/reopen plus post-stall time partition equivalence. All are
`CHAT_EXECUTABLE`; pending checks are `READY_FOR_VERIFICATION`. No OpenCode task
or independent review is claimed.

## Funding result and contract boundary

The narrow one-coin quote reproducer now tests hunger **80** as well as **90**.
At 80 the actual contracted next road is eligible, but the held coin is still
reserved and cannot purchase even a one-coin loaf. This is a reducer/selector
boundary probe, using an explicitly constructed local state, **not** a claim
of an autonomous trip or a funded meal.

The separate real 96-hour provision control moves one existing opening loaf
from the market to Hana, rather than creating food. It delays hunger but does
not increase deliveries; it is not recurring compensation. The real funded
harvest/shopping tests continue to prove Farid's two purchases from actual
harvest wages. They do not give the courier a personal copper wallet.

Existing market settlement pays goods to its buyer and copper to the stock
owner. It cannot buy a loaf on behalf of another NPC. Existing gifts require
the actual **player** as donor and are not an NPC payroll mechanism. Supply
cash pickup requires zero copper, delivery requires exactly one consigned
coin, and durable validation rejects any personal copper remainder. Thus
neither existing market receipts nor the player's gift capability proves an
autonomous, recurrent funded courier meal under current rules.

If a later recovery experiment requires a new contract, its minimum terms are:

- Payer: the market's initialized, unreserved copper, earned from recorded
  physical sales; no advances from customer cargo, credit or money creation.
- Entitlement: a named courier's completed food delivery at the staffed market,
  while the courier can still travel; a fee is not earned by starting a trip.
- Settlement: an explicit local seller/beneficiary contract or a separate
  personal account. Paying the current consignment slot is invalid. A food
  transfer must debit actually owned, unreserved food at the same site.
- Idempotency: persist a unique delivery receipt and one settlement per receipt;
  current delivery counters alone are not a new payroll receipt contract.
- Refusal: absent seller, exhausted payer, missing road, reserved food, late
  food delivery and duplicate settlement must fail without partial writes.

This is a bounded design requirement, **not implemented gameplay**. The closure
plan permits a measured finite-resource failure; it does not require inventing
a payroll system to claim a sustainable village.

## Reproduced integrity defect and repair

The #59 regression accepted the extra-personal-loaf quote, but executing it
credited copper to a cash courier's exact-custody slot. Calling the real supply
validator then failed with `courier inventory and cargo reservations disagree`.
The local reproducer failed before the repair. An extra personal loaf is
saleable only when settlement also respects the owner's resource contract.

Market settlement now rejects incoming water, grain or copper into a configured
courier's custody-only slots **before writes**. Food still allows personal stock
alongside a reserved parcel. Local food purchase and local return-route quote
checks reject sellers who cannot receive the quoted payment. Existing offers
remain loadable; no history, schema, route or supply contract is rewritten.
The regression checks rejection, unchanged raw ledgers and valid supply custody.
This is author self-review, not independent approval.

The same failure was reproduced in the single-material profession selector:
it returned a personal courier ore quote whose copper settlement was invalid.
Grain, single-material and compound-material selectors now check both receipt
owners as well. Two local probes verify that personal courier ore is skipped,
but the same courier can steward site-owned ore: the real trade credits the
site's copper, preserves the courier's zero balance and conserves twelve coins.
The new probes plus PLAY-44/45 regressions passed **29 tests on each local
Python 3.10.22 and 3.13.17**. These synthetic local quote probes do not claim
autonomous ore delivery or courier wages.

The long seven-day cases run in separate Python-matrix jobs in the targeted
workflow, alongside the audit/adversarial jobs. All four jobs must succeed;
moving the long cases to parallel jobs does not omit any acceptance check.

## Final acceptance matrix

| Gate | Evidence / state |
| --- | --- |
| Stack full CI, #57 | [42707752554](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42707752554), both Python jobs success |
| Stack full CI, #58 | [42708580882](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42708580882), both Python jobs success |
| Stack full CI, #59 | [42712961446](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42712961446), both Python jobs success |
| Stack targeted, #57 | [42707745153](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42707745153), pending final observation |
| Stack targeted, #58 | [42715541830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42715541830), dispatched on exact head |
| Stack targeted, #59 | [42715548910](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42715548910), dispatched on exact head |
| Finite seven-day wet/dry worlds | `test_play47_closure_endurance.py`, pending |
| Depleted treasury / duplicate wages | `test_play41_funded_wage.py`, included in final targeted workflow |
| Physical road / reserved cargo / absent seller | supply, cash-courier and market suites, included in final targeted workflow |
| SQLite close/reopen, replay, snapshot, PRAGMA and time partitions | seven-day test, pending |
| Old saves / default-off compatibility | genuine 41/56 fixture rejection in targeted workflow; historical compatibility in full workflow |
| Final exact-SHA targeted + full 3.10/3.13 | pending; blocks technical closure |

The seven-day experiment records daily food/water/cash and wage receipts in the
same real thirteen-resident joined world. Only the wet case receives six finite
rain units at the existing day-one/two/three boundaries. Each daily connection
is closed and reopened, including the final checkpoint. A closed day-three
database is copied, then continued using three-hour instead of six-hour waits
to the 96-hour gate; **the entire semantic state**, excluding revision metadata
only, must match. The original world continues to day seven. Each advance
creates a checked snapshot to bound incremental replay cost; after each daily
close/reopen the full genesis replay is still independently verified. No
post-stall delivery or recovery is presumed.

External review remains `EXTERNAL_REVIEW_DEFERRED_BY_OWNER` and production
remains `P0_PRODUCTION_NOT_APPROVED`.

## Audited historical run identities

The full PR runs checked out GitHub's temporary merge commits, rather than the
head commits themselves. Both Python logs report **1,694 passed** for each PR.
The three merge objects were fetched and `git diff --exit-code HEAD MERGE`
confirmed identical trees for each pair:

| PR | Head | Actual checked-out merge | Full run |
| --- | --- | --- | --- |
| #57 | `51cdc3b02fb1d891398a5258b954b554d61a4a4d` | `7b093b0a41198ace76f5a8fa12968c33f7b038e7` | `42707752554` |
| #58 | `21e8b0236a952d6dd038bf3a076c354b4e4fbbd2` | `9a9f8e8d62ab261c155373fce6c49901b0d7ef3b` | `42708580882` |
| #59 | `77ddb54b82038075c2d9ec642b8d0dcd3b75c43d` | `e5ef7cd8f01e64d8485c6a46538be95bdd12f4bb` | `42712961446` |

The candidate workflows now explicitly check out the PR head (or push SHA) and
assert `git rev-parse HEAD` equals that source SHA. This avoids calling a merge
object an exact head. At `caa76a1c88e9ad23a34d498a1a3d00148fe5a5f7`, targeted
[42717339117](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42717339117)
and full [42717347582](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42717347582)
were launched; their overall results remain pending at this documentation update.
The authentic old-save gate passed locally on both Python versions and in both
candidate targeted jobs; this alone is not completion of the full targeted run.

The original plan's #53–55 gates were also rechecked: both Python jobs succeeded
in targeted/full pairs [42701787041](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42701787041)
/ [42707543170](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42707543170),
[42703695310](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42703695310)
/ [42703704217](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42703704217),
and [42705193034](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42705193034)
/ [42705198691](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42705198691).
Their current heads `7c0876b`, `8068f91`, and `7845491` are ancestors of `b326c5e`.
