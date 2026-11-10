# PLAY-47 closure execution evidence

Status is governed by the [gated technical decision](PLAY_47_TECHNICAL_CLOSURE_DECISION.md):
**OPEN / RELEASE NO-GO** on an unverified candidate; **CLOSED_TECHNICALLY /
EXTERNAL_REVIEW_DEFERRED_BY_OWNER** only after the exact decision commit passes
all required checks and is fast-forwarded to the integration branch. Schema
**42** / Rules **57**. No PLAY-48 work, `main` update or production approval.

## Analysis and scope

The checkout initially opened on `main` at `25059fa`. The integration branch
was fetched from `origin` and verified at `b326c5ea2f685697c04ed24f6bc961043bee15ab`.
The stacked heads were still #57 `51cdc3b02fb1d891398a5258b954b554d61a4a4d`,
#58 `21e8b0236a952d6dd038bf3a076c354b4e4fbbd2`, and
#59 `77ddb54b82038075c2d9ec642b8d0dcd3b75c43d`.
Integration must remain a verified fast-forward. The runtime repair branch is
`feature/play47-closure-verification-20261109`; the final documentation decision
branch is `feature/play47-technical-closure-20261110`.

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

## Verified runtime baseline and final acceptance matrix

The table records the observed runtime baseline `0f8c31f` while this
documentation-only closure proposal is prepared. It does not substitute for
the final proposal commit's own full/targeted checks. That exact SHA and its
run links must be recorded in the closure review before gated promotion.

| Gate | Evidence / state |
| --- | --- |
| Stack full CI, #57 | [42707752554](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42707752554), both Python jobs success |
| Stack full CI, #58 | [42708580882](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42708580882), both Python jobs success |
| Stack full CI, #59 | [42712961446](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42712961446), both Python jobs success |
| Stack targeted, #57 | [42707745153](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42707745153), 72 passed on each Python; source `51cdc3b` confirmed in logs |
| Stack targeted, #58 | [42715541830](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42715541830), 76 passed on each Python at exact source `21e8b02` |
| Stack targeted, #59 | [42715548910](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42715548910), 77 passed on each Python; source `77ddb54` confirmed in logs |
| Finite seven-day wet/dry worlds | `test_play47_closure_endurance.py`, 2 passed on each Python at source `0f8c31f`; complete reports identical across versions |
| Depleted treasury / duplicate wages | `test_play41_funded_wage.py`, included in final targeted workflow |
| Physical road / reserved cargo / absent seller | supply, cash-courier and market suites, included in final targeted workflow |
| SQLite close/reopen, replay, snapshot, PRAGMA and time partitions | Passed for both wet/dry 7d cases on each Python in exact-source runtime CI |
| Old saves / default-off compatibility | Genuine 41/56 rejection, historical compatibility and scenario opt-out controls all passed on both at runtime `0f8c31f` |
| Final full 3.10/3.13 | [42719791538](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42719791538), SUCCESS, 1,694 per Python at exact checked-out `0f8c31f15e065cdc2d101bdfa6ca9b67d3331bdf` |
| Runtime targeted 3.10/3.13 | [42719785455](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42719785455), SUCCESS: audit 176 + genuine old save 1 + endurance 2 = 179 on each Python at exact source `0f8c31f` |
| Final decision commit | Its own exact-SHA full/targeted checks and verified integration are still required; baseline results above do not enact this proposal |

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

## Supplementary local reproduction

Both seven-day cases completed locally on CPython 3.13.17, including final
full replay after connection close, snapshot equality, integrity/foreign-key
checks and the complete 96-hour semantic partition comparison. Every reported
checkpoint matches the exact-source 3.13 CI reports. Local 3.10 independently
passed the dry seven-day case and 96-hour gate. The authoritative runtime CI
subsequently passed both cases on both Pythons. These local observations do
not replace the final decision commit's own CI.

At dry hour 168, twelve copper remain conserved, seven loaves have been baked,
four meals have been eaten, six food units and three grain remain, and all
thirteen residents are at hunger 100. Both initial water units were consumed
by real crop growth; there are no rain receipts or stored water. Hana has 24
deliveries and Huda three. From hour 72 to 168 there are no new deliveries,
market trades, completed production jobs or wage receipts. The two wage receipts
in the global audit include the smith; they are not two Farid harvest wages.
This is measured finite-world failure, with no post-stall recovery claim.

### Specific adverse-case coverage

| Gate | Executed test / final verification route |
| --- | --- |
| Empty treasury and no invented pay | `test_harvest_wages_remain_unpaid_if_employer_has_no_copper`, PLAY-41 targeted |
| Duplicate, forged or wrong-price wage | `test_harvest_worker_earns_only_after_completed_work_and_real_copper`, PLAY-41 targeted |
| Unknown road and travel authorization | `test_target_cannot_be_set_without_road_knowledge` and `test_direct_low_level_travel_start_cannot_bypass_known_roads`, full + targeted navigation suite |
| Seller walks away | `test_smith_does_not_conjure_sold_out_material_or_distant_price`, PLAY-46 physical-chain targeted |
| Reserved food/copper and incoming custody | PLAY-40 cash suite, PLAY-47 market-custody probes, PLAY-27 physical-supply suite |
| Opt-out parity | `test_disabled_market_journey_preserves_exact_legacy_event_replay`, `test_multi_compound_flag_is_strict_default_off` and PLAY-44/45 controls |
| Genuine old save refusal | `test_genuine_41_56_sqlite_world_is_refused_without_any_mutation`, generated by actual predecessor `a6c20e3` |
| Reopen/replay/PRAGMA and clock partitions | `test_thirteen_residents_seven_days_and_post_stall_clock_partitions`, separate targeted endurance matrix |

Coverage entries identify the acceptance cases; pending targeted jobs are not
reported as successful merely because their tests are listed here.

## Exact-source seven-day CI evidence (both Pythons verified)

Job `129510623967` in [targeted run 42719785455](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42719785455)
completed SUCCESS: **2 passed in 2,039.79 seconds**. Its checkout log explicitly
records `0f8c31f15e065cdc2d101bdfa6ca9b67d3331bdf`. These two tests include daily
full-genesis replay after actual connection close/reopen, final day-seven replay,
snapshot equality, both SQLite PRAGMAs and the full semantic 96-hour comparison
of three-hour versus six-hour waits from the same verified day-three database.
Job `129510624455` also completed SUCCESS on Python 3.10: **2 passed in
4,428.70 seconds**, with the same exact checkout SHA. Its complete wet/dry
checkpoint reports are identical to the Python 3.13 reports. The audit jobs
passed **176** each plus the separate genuine old-save refusal **1** each;
the entire runtime targeted run concluded SUCCESS. This is runtime-baseline
proof; the final documentation decision must pass its own exact-head checks.

| Measured at hour 168 | Dry | Six finite rain units |
| --- | --- | --- |
| Residents at hunger 100 | 13 / 13 | 13 / 13 |
| Conserved copper | 12 | 12 |
| Food remaining | 6 | 5 |
| Grain remaining | 3 | 10 |
| Known remaining water, including cargo | 0 | 5 |
| Water used for crop growth | 2 | 3 |
| Mature crop lots (original / east field) | 1 / 1 | 1 / 2 |
| Completed bakes | 7 | 7 |
| Meals eaten | 4 | 5 |
| Completed deliveries (Huda / Hana) | 3 / 24 | 3 / 25 |
| All market trades, including materials | 7 | 8 |
| All funded wage receipts, including smith | 2 | 3 |
| Additional deliveries after hour 72 | 0 | 0 |
| Additional bakes, crop growth, trades or wages after hour 72 | 0 | 0 |

The rain is credited only through the three finite receipts at hours 24, 48
and 72; the original two water units remain the sole dry source. Unused water
includes physically held stocks, so five remaining units must not be described
as five units all located in the well. The rainy case reproduces the existing
two paid harvests and Farid's two real meals; it does not restore the stopped
courier cycle. This is a valid measured capacity/distribution limit under the
approved plan. Both Python and audit gates are verified for runtime `0f8c31f`.
The final documentation decision remains subject to its own activation gates.

## Verified stack integration — 2026-11-10 UTC

After #58's last Python job succeeded (76 passed in 4,034.90 seconds on 3.10),
the entire #57–59 stack had targeted/full success on both supported Pythons.
The #58 log confirms source `21e8b0236a952d6dd038bf3a076c354b4e4fbbd2`.
The integration ref was advanced **without force**, with expected old SHA
`b326c5ea2f685697c04ed24f6bc961043bee15ab`, to
`77ddb54b82038075c2d9ec642b8d0dcd3b75c43d` after the ancestry check.
The remote ref and local tracking ref were then fetched and checked.

After all four targeted jobs and both full jobs passed at exact source
`0f8c31f15e065cdc2d101bdfa6ca9b67d3331bdf`, the integration branch was advanced
again without force, with expected old SHA `77ddb54`, to `0f8c31f`. Remote and
local tracking refs were fetched and checked. This adopts the tested receipt
custody repair. The final documentation-only decision is a separate gated
candidate; PLAY-47 stays OPEN until that exact decision commit is verified and
promoted. No `main` ref was changed.

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
were launched and later superseded/cancelled when the runtime source advanced.
They are historical run identities, not the final acceptance evidence.
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
