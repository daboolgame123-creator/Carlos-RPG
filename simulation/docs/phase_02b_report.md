# Phase 02-B — technical implementation report

**Status: IN_PROGRESS — final CI evidence pending; NOT APPROVED/CLOSED.**
**Branch:** `simulation-engine-phase-02b`.
**Baseline:** Phase 02-A verified commit `fdf6162c65d6947507d1b4e4516c17d851873c29` and [CI 42064429357](https://github.com/daboolgame123-creator/Carlos-RPG/actions/runs/42064429357), 657/657 tests on Python 3.10 and 3.13.
**Versions:** Schema **16**, Rules **23** (from 15/22).
**P0 OPEN / EXTERNAL_REVIEW_DEFERRED.** All worlds disposable, no canon Carlos imports.

## Implemented capability

A trusted NPC production service starts a finite recipe job for one actual co-located NPC with the required configured profession and a real workshop site. Time-zero bootstrap must explicitly initialize site-owned stocks for the recipe's **one input**, **one output**, and **reusable tool**. The sample recipe turns exactly **two units of grain** into **one unit of bread**, after **90 simulated seconds**, using an existing oven, by a worker with `role=baker`.

- `ProductionRecipeConfigured`: trusted bootstrap only, fixed recipe (site, profession, input/quantity, output/quantity, tool and simulated duration).
- `ProductionStarted`: trusted explicit local service only; checks actual NPC profession/presence/availability, source quantities, existing output and tool stock. Immediately reserves/debits input and persists the material/worker/tool provenance in `production_jobs`; creates one noninterrupting **protected** due-time schedule.
- A real trusted `ScheduledEventFired` at the exact due logical time creates the declared output at the worksite and marks the job completed, recording output before/after. No output appears before the due event; no created matter from unknown resource balances. No physical tool consumption.
- Active jobs occupy their NPC's time and use **one tool unit at their site**. A site with one oven cannot run two concurrent oven jobs. Existing NPC movement, action execution, autonomous planners and assistance reservation skip or block those workers. No teleporting a baker or simultaneous second craft.
- Production capability is separate and recorded in the SQLite command ledger as `production_authorized`; full replay re-uses it, never assumes it from an event name. These flags are trusted **internal conventions**, not HTTP authentication.
- `production_recipes` and `production_jobs` are validated in every projected WorldState and snapshot. Direct generic schedule creation or cancellation cannot forge production completion. All changes remain atomic, event sourced and bounded.
- When not configured, **no production** occurs, preserving the existing autonomous behavior and resources exactly.

## Test plan and acceptance

Add 16 targeted tests: a 7-NPC bakery with real inputs and two ovens, 89/90-second timing, scarcity/unknown, invalid profession, two workers competing for tools, duplicate work, travel while working, honest cancellation/early-firing rejection, active-session and capability enforcement, stale/duplicate commands, batch rollback, clock-event budget abort, snapshot/reopen, separate SQLite backup/restore, split versus lumped time, and strict corruption rejection. Run all historic parity/legacy saved-world checks on Python 3.10/3.13. The CI workflow creates an **actual** Phase 02-A 15/22 SQLite file with frozen code and verifies its 16/23 refusal without modifying worlds/events/commands/snapshots.

A disposable `simulation/scenarios/test_village/demo_production_02b.py` fixture shows **7 NPCs, 2 bakers, 2 ovens, 4 grain → 2 bread at 90 seconds**, verified by full replay. This is manually initiated; it is **not yet an autonomous vocational/economic planning engine**.

**Final CI / commit:** Pending verification. Earlier red intermediate commits are construction steps, not the final result. Once CI is green on the actual documentation HEAD, record exact run, tests per Python, demo status and source SHA.

## Internal review and limits

The author does not claim an external independent review. Formal review request: [phase_02b_independent_review_request.md](phase_02b_independent_review_request.md). Unknown input/output/tool is NOT zero; jobs fail closed without actual initialized resources. Output and time are deterministic, with actual cost documented as consumed materials and reserved tool time. No monetary price, wages, currency, amortization, worker training, tool wear, multi-input recipes, spoilage, refunds, job interruption, owner-to-owner market transfers or fully autonomous occupational decision policy. Those are separate later phase decisions.

**P0 remains OPEN.** New Schema/Rules refuse 15/22 saves; no migration, no guarantee of durable canon gameplay. Do not import original Carlos story, alter `main`, or expose production authorities via a public/network API.
