# WORLD-01b Player Workshop Supply Analysis — 2026-11-27

## Verified starting point

- Development branch: `feature/carlos-world01b-player-supply-20261127`, based on `feature/carlos-world01-20261127` at `8ac95422f73949ff917ac9c0889adcbb78a67929`.
- PR #185 was checked before edits: still open, draft, unmerged, mergeable; head `feature/carlos-engine-needs-20261126` at `416e26b6c037b2fc504c8454d9b607aadeee7eba`.
- The current worktree is separate from `main` and PR #185. No story or production-save files are in scope.

## Finding

WORLD-01a proves a time-zero, explicitly funded player blacksmith contract, but initializes recipe inputs at the forge. PLAY-46 proves that an NPC can physically buy ore and charcoal, carry them over timed routes, deposit them, and produce an iron fitting. It does not provide the human player with that material-delivery path: `PlayerGateway.buy` adds goods to the player's owned resource ledger, while `NPCWorkshopService.deposit` and `deposit_workshop_material` currently accept NPC workers only. Giving the player the same NPC service would cross the command boundary.

## Proposed bounded change

Extend the existing `WorkshopMaterialDeposited` event/reducer to accept either its current qualified NPC worker or the exact player named by a time-zero player work contract. Add one `PlayerGateway.deposit_material` action bound to that signed recipe. Reuse the existing protected production+market capability, event ledger, inventory-conservation checks, reservation check, and replay behavior. Keep `NPCWorkshopService` NPC-only. Do not add a new event kind, database field/schema version, save migration, resource generator, market AI, autonomy policy, or UI flow.

The test-only world will explicitly initialize one ore at the mine, one charcoal at the kiln, one anvil and one fully funded wage at the smithy, and a finite player wallet. Real posted local offers, player travel/wait, purchases, return travel, material deposits, and production must move those balances through existing reducers. Test genesis is the documented source for the finite opening stock; no runtime command may initialize it.

## Contracts to preserve

1. A player may deposit only a known owned resource that is an input to a recipe naming that player, at that recipe's site, while physically present and not travelling/busy.
2. An NPC may continue depositing only for a local recipe matching its configured role.
3. A deposit atomically debits the worker's owned balance and credits the worksite's known balance; invalid, unowned, reserved, unrelated, or overflowing stock is rejected without state mutation.
4. Player travel, market quote/purchase, timed production, and wage remain explicit and finite. Market payment and all resource totals remain conserved.
5. The same recorded events replay and snapshot to the identical state. No change touches the original story or turns the experiment into an original-world bootstrap.

## Acceptance criteria

- A focused integration test proves that Carlos travels from the forge to the mine and kiln, buys each locally posted input at its exact price, and returns with it; the workshop stays at zero until each material is deposited.
- Deposits reduce Carlos's own holdings by exactly the credited site quantity, and the site cannot be funded by a remote purchase or invented stock.
- The player can then start the signed local recipe and, after its due time, receives the scheduled fitting and funded wage.
- Rejection checks cover a player without the named contract, missing personal stock, unrelated resources, and travel/busy or wrong-site deposit attempts; each leaves the verified state unchanged.
- Existing NPC workshop-deposit and production tests remain unchanged in outcome.
- Focused tests and the complete simulation test suite pass on the supported local Python interpreter; replay/snapshot verification is part of the focused scenario.

## Planned files

- `simulation/src/carlos_sim/workshop_transfers.py`: event reducer authorization for contracted players while preserving NPC authorization and conservation.
- `simulation/src/carlos_sim/player_gateway.py`: player-bound material deposit command.
- `simulation/tests/test_world01b_player_workshop_supply.py`: isolated disposable mine/kiln/forge integration and rejection checks.
- `simulation/docs/WORK_QUEUE.md`, `simulation/docs/CARLOS_NEXT_CHAT_HANDOFF.md`, and the WORLD-01 analysis record: milestone and next-step evidence.

## Explicitly out of scope

Autonomous buying by the player or NPCs, general-purpose occupations, inventory/equipment redesign, customer sales beyond the existing wage contract, new story content, save migration, release approval, merge, or changes to PR #185.

## Result

Implemented on `feature/carlos-world01b-player-supply-20261127`. The existing
`WorkshopMaterialDeposited` event now accepts a worker only when it is either the
existing role-qualified NPC or the exact player named by a signed recipe. The new
`PlayerGateway.deposit_material` command binds this action to the real player identity,
checks the signed recipe/site/input, and appends through the existing active production
and market capabilities. The NPC service remains NPC-only. No event type, schema field,
or migration was added.

The disposable test-world integration buys the ore and charcoal from finite local stock,
records each trip and exact-price purchase, leaves the worksite stock at zero until the
player returns and deposits the goods, then completes the funded iron-fitting job. It
also checks wrong-site/in-transit, unowned stock, unrelated input, contract identity,
busy action, duplicate command, conservation, replay, snapshot, and reopen behavior.

Verification: **2/2** new focused tests; **23/23** focused WORLD-01/PLAY-43/PLAY-46
regressions; full simulation suite **1949 passed, 1 skipped** on Python 3.12 in 19:11.
PR #185 was rechecked before modification and remained open/draft at its recorded head;
no PR, `main`, story, UI, schema, or production save was changed.

WORLD-01b is locally verified; WORLD-01 remains in progress. Next: analyze WORLD-01c,
finite causal iron extraction and charcoal production, before adding more source stock.
