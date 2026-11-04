# Phase 01-L — Food consumption changes needs, not just inventory

## Implemented

- Introduced event-sourced `NPCFoodConsumed` and the `WorldState.consumptions` audit ledger.
- Trusted in-process `NPCConsumptionService.eat` spends the NPC's real food and reduces that NPC's hunger in one atomic command. Fixed prototype rule: **1 food = 25 fewer hunger points**, 1–3 units per meal, clamped at 0. Uninitialized/insufficient food is rejected. One meal per NPC per logical tick.
- The opt-in autonomous `consumption_enabled=True` mode lets idle, non-traveling NPCs with hunger at least 50 and food in inventory eat one unit, without consulting another's private inventory or overriding an already-recorded action intention.
- Physical assistance delivery remains separate from food consumption; ownership alone does not relieve hunger. Original social/assistance modes default to unchanged behavior.
- Capability validation, replay hashes, optimistic revisions, snapshot checks, frozen off-session state and a bounded per-advance event budget are preserved.

## Verification

**345/345 locally passing tests**, in separate groups due to command timeout limits:

- 134 core tests
- 107 movement/navigation/social tests
- 35 assistance tests
- 37 assistance review + autonomy tests
- 32 new food-consumption tests

`python -m compileall -q src tests scenarios` passed. The independent test village demo completed and verified deterministic event replay. After Basim fulfilled a three-unit gift, Nora ate twice in distinct ticks: the aid transfer was Basim 10→7, Nora 0→3; after two meals Nora owned 1 food and had hunger 60. The meal log preserved both before/after changes. No GitHub CI was run for these local test results.

## Exploitative borrowers and abandoned promises

A **gift** and a **loan** are different contracts. In the present aid model, receiving food as a gift and leaving cannot automatically produce a repayment debt or accusation of theft. An opportunistic borrower who takes goods and deliberately avoids returning them is a valid **future** scenario: a loan ledger must preserve lender, borrower, quantity, transfer evidence, agreed return date, amounts repaid, overdue/default status, communications and witness knowledge. Absence should not erase the obligation or automatically prove fraudulent intent. Creditor/debtor motives and consequences will be evaluated under explicit rules, and can differ from person to person.

## Explicit limitations

- Hunger reduction is a fixed prototype number; it does not model realistic calories, digestion, disease, time spent eating or gradual daily metabolic consumption. The existing `NPCNeedChanged` event may still represent trusted non-food need changes, and generic resource expenditure still does not provide satiety.
- No automatic loans, credit contracts, theft, remote notifications, deadlines, debt collection, or presumption of honest behavior has been implemented in this phase.
- `consumption_authorized` is a **trusted local capability flag**, not HTTP authentication.
- **Schema 10 / Rules 13** require explicit migration or a fresh experimental DB. No real Carlos story data or `main` files were changed.

## Status

Implemented and locally tested; independent review remains pending.
