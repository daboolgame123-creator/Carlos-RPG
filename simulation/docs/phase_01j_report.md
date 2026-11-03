# Phase 01-J — Resource-backed assistance and explicit obligations

## Implemented

A trusted-local, event-sourced `NPCAssistanceService` adds four distinct transitions: `AssistanceRequested`, `AssistanceResponded` (promise/refusal), `AssistanceFulfilled`, and `AssistanceCancelled`. Each transition is an atomic SQLite command, requires an active play session and a separate `assistance_authorized` capability, and is replayed deterministically.

- Only two physically co-located, currently idle NPCs can request and respond. Player-controlled Carlos is excluded from automatic assistance. A reply to a local request must occur at its original location; an accepted promise may be physically fulfilled wherever both NPCs reunite.
- Only **food** and **water** with explicitly initialized integer balances are supported. Quantity: 1–1000 units. Unknown inventory is never treated as zero. An open same-pair/same-resource request and duplicate same-tick requests are rejected.
- Speech and promises do not move resources. The separate `AssistanceFulfilled` event requires an existing accepted promise, the real provider as actor, co-location and sufficient goods. It atomically reduces the provider balance and raises the recipient balance by the same quantity, records before/after balance evidence and grants the recipient **+5 directed trust** (clamped at +100). A delivered promise cannot be fulfilled again.
- Refusal and authorized cancellation produce no goods or free trust. If the provider spends their stock after promising, fulfillment fails without partial writes; the provider may withdraw the promise.
- Obligations and their resolution history are retained, validated and included in snapshots/full replay. Existing player view does not expose hidden balances or obligations.

## Verification

Local test runs performed **separately** due to execution time limits: **35/35 Phase 01-J tests passed** and **241/241 previous-stage tests passed**, a combined **276 passing tests**. `python -m compileall -q src tests scenarios` passed. The isolated village demo passed and produced food balances Nora **1→4**, Basim **8→5**, with a preserved total of **9**. A prior spoken offer changed neither balance. The final trust was **+8**, comprising +3 for the spoken offer and +5 for fulfilled help.

The regressions cover conservation, real stock shortages, idempotency, wrong actor, co-location/travel/busy guards, no Carlos automation, immutable ledgers, request duplication, valid refusal and cancellation, command atomicity, active session, revision conflicts, snapshots, restart, cross-world determinism and non-disclosure in player view.

No hosted GitHub CI run is claimed. Git blob SHA comparisons confirm published code/tests/demo match the locally executed files.

## Boundaries and compatibility

This phase exposes **explicit assistance commands**, not automatic acceptance or delivery triggered by a `request_help`/`offer_help` speech act. Automatic NPC assistance decisions, production of goods, trading, timed fulfillment, expiry, debt, debt enforcement, combat, and interactive dialogue require later phases. In this prototype, an actual hand-to-hand resource exchange is instantaneous at the current *logical* time. The resource conservation invariant applies to each transfer; separate authorized consumption may reduce world stock.

**Schema v9 / Rules v11**. This is not an in-place migration of previous experimental SQLite worlds; use a new test database or an explicit future migration. Internal trusted flags are not network authentication. No canonical Carlos RPG story files have been modified, and do not merge into `main` before independent review.

## Status

Initial implementation and verification complete; Phase 01-J awaits independent review.
