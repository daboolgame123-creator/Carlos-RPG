# Phase 01-L — Food consumption changes needs, not just inventory

## Implemented

- Introduced event-sourced `NPCFoodConsumed` and the `WorldState.consumptions` audit ledger.
- Trusted in-process `NPCConsumptionService.eat` spends the NPC's real food and reduces that NPC's hunger in one atomic command. Fixed prototype rule: **1 food = 25 fewer hunger points**, 1–3 units per meal, clamped at 0. Uninitialized/insufficient food is rejected. One meal per NPC per logical tick.
- The opt-in autonomous `consumption_enabled=True` mode lets idle, non-traveling NPCs with hunger at least 50 and food in inventory eat one unit, without consulting another's private inventory or overriding an already-recorded action intention.
- Physical assistance delivery remains separate from food consumption; ownership alone does not relieve hunger. Original social/assistance modes default to unchanged behavior.
- Capability validation, replay hashes, optimistic revisions, snapshot checks, frozen off-session state and a bounded per-advance event budget are preserved.

## Verification

**351/351 locally passing tests after review**, in separate groups due to command timeout limits:

- 134 core tests
- 107 movement/navigation/social tests
- 35 assistance tests
- 37 assistance review + autonomy tests
- 32 original food-consumption tests
- 6 post-review food-consumption regressions

`python -m compileall -q src tests scenarios` passed. The independent test village demo completed and verified deterministic event replay. After Basim fulfilled a three-unit gift, Nora ate twice in distinct ticks: the aid transfer was Basim 10→7, Nora 0→3; after two meals Nora owned 1 food and had hunger 60. The meal log preserved both before/after changes. No GitHub CI was run for these local test results.

## Exploitative borrowers and abandoned promises

A **gift** and a **loan** are different contracts. In the present aid model, receiving food as a gift and leaving cannot automatically produce a repayment debt or accusation of theft. An opportunistic borrower who takes goods and deliberately avoids returning them is a valid **future** scenario: a loan ledger must preserve lender, borrower, quantity, transfer evidence, agreed return date, amounts repaid, overdue/default status, communications and witness knowledge. Absence should not erase the obligation or automatically prove fraudulent intent. Creditor/debtor motives and consequences will be evaluated under explicit rules, and can differ from person to person.

## Explicit limitations

- Hunger reduction is a fixed prototype number; it does not model realistic calories, digestion, disease, time spent eating or gradual daily metabolic consumption. The existing `NPCNeedChanged` event may still represent trusted non-food need changes, and generic resource expenditure still does not provide satiety.
- No automatic loans, credit contracts, theft, remote notifications, deadlines, debt collection, or presumption of honest behavior has been implemented in this phase.
- `consumption_authorized` is a **trusted local capability flag**, not HTTP authentication.
- **Schema 10 / Rules 14** require explicit migration or a fresh experimental DB. No real Carlos story data or `main` files were changed.

## Status

Implemented, reviewed, and ready for closure within the limited experimental scope.

## Post-implementation review — November 4, 2026

**Confirmed defect: the generic NPCNeedChanged event permitted foodless hunger relief** without the trusted NPC adjustment capability. A co-located actor could reduce their hunger from 25 to zero while retaining their entire food inventory, bypassing the meal ledger and its resource-conservation rule. This was reproduced with a failing regression before the fix.

**Correction:** At the SQLite event-store boundary, a generic `NPCNeedChanged` whose `need` is `hunger` and whose new value is lower now requires `npc_authorized=True` and an active session. Normal increases in hunger remain allowed; legitimate scripted/administrative decreases are still possible but must be explicitly authorized and are **not** represented as eating. Physical eating uses `NPCFoodConsumed` with its separate consumption capability. The existing test fixtures that intentionally decrease hunger have been updated to mark the trusted setup adjustment.

**Verification:** 6 new regressions cover unauthorized free satiation, authorized adjustments, natural hunger increase, transaction rollback, off-session rejection, and normal food-backed eating. Final tests passed in five separate batches: **134 core + 107 navigation/social + 41 Phase 01-J + 31 Phase 01-K + 38 consumption/review = 351/351**. Compilation and the independent village scenario passed, including deterministic replay. A monolithic pytest run timed out; only the independently completed batch results are claimed. GitHub CI was not run.

**Versioning:** Schema remains **10**, rules advance **13 → 14** because the accepted event contract changed. Existing experimental worlds under rules 13 require explicit migration or recreation. No changes to Carlos narrative files or to `main`.
