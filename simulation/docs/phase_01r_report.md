# Phase 01-R — Opportunistic autonomous recovery after investigation

## Scope and rationale

Phase 01-R adds an **opt-in, purely deterministic** collection decision
to the existing local living-world scheduler. Previously, Phase 01-Q
required a caller to explicitly request the physical transfer after
an NPC completed an investigation. Now a foraging-capable NPC can
**independently pick up one visible natural-food unit** at the moment
its own investigation completes, based on its hunger and available
carried stock. No player click or individual gathering command is
needed for that decision.

**Important distinction:** Phase 01-R does NOT yet make an NPC
choose to start an `investigate` action *because* it wants food. The
existing NPC utility planner still chooses actions, and the new
policy decides whether recovery is worthwhile **after** a completed
investigation. That limitation is intentional to preserve the
audited NPC decision scoring/provenance. A dedicated hunger-driven
search intention and perception/knowledge event is a **separate
next-phase design**, not falsely advertised as completed here.

## Rules

- Mode `LivingWorldEngine(..., gathering_enabled=True)` is **off by default**.
- `choose_gathering_intent(state, finished_action_id)` is pure and
  reads only the character's **own** needs/owned food, the completed
  investigation, the physical site occupied by that character,
  and `wild_food` **at that site only**.
- Threshold: hunger >= **65/100** and the actor has **exactly 0** known
  units of owned `food`. Missing/unknown stock is never treated
  as zero. Local `wild_food` is modeled as a plainly visible
  natural deposit for this synthetic scenario.
- The investigation must have just completed at the current
  logical tick, belong to the same NPC, and be unused for gathering.
  The character cannot be traveling or performing another action.
- When several investigation completions share a timestamp,
  each NPC's opportunity is checked against the **live remaining
  natural inventory** in the same durable due-signal order.
  There are no phantom reservations or duplicated products.
- The accepted choice emits the already defined,
  `action_authorized` **NPCFoodGathered** event. This uses the
  existing same-tick, atomic single-unit transfer and persistent
  `WorldState.gatherings` provenance ledger from 01-Q.
- The same high-level `advance` transaction includes decisions,
  scheduled completions, any gatherings and clock advancement,
  so an event limit, stale revision, or invalid event rolls back
  the **entire** attempt.
- No additional schema or rules change: **Schema 12 / Rules 16**.
  01-Q compatible experimental saves need no new migration.

## Seven-NPC simulated-world test

The synthetic grove has **two** natural food units and seven NPCs:
four hungry foodless investigators at the grove (Adel, Basim,
Nora, Salma), one not hungry (Huda), one already carrying food
(Layla), and one hungry investigator in a **different location**
(Omar). The engine runs a 90-second logical-time command.

- **7 NPCs**, **52 events** in the one advance command.
- **2 independent physical recoveries**: Adel and Basim each
  receive one unit; the deposit reaches zero. The other eligible
  investigators do not obtain phantom food.
- Low hunger, already-carried food and distant location prevent
  unauthorized pickup.
- Independent consumption can eat gathered food in later
  steps, without conflating eating with collection.

A reproducible isolated demonstration is available at
`scenarios/test_village/demo_gathering_autonomy.py`.
It includes source conservation, exact recovered action IDs and
`db.verify` full ledger/state replay assertions.

## Verification

- **445/445 passed** on Python 3.10 and 3.13 in GitHub Actions
  `41837296985` before the final documentation-only commit.
- **13 new focused tests** cover 7-character scarcity, opt-in/out,
  invalid mode, distant stock/private peer inventory non-leakage,
  unknown natural/owned stocks, per-character eligibility, bounded
  atomic rollback, paused sessions, split-time outcome equivalence,
  deterministic repeatability, no second recovery from a completed
  action and independent real eating.
- Final 7-NPC existing-scenario event log and state digests match
  the reviewed **Phase 01-Q** code when this new mode is off,
  since this phase leaves every old reducer and scoring algorithm
  intact. Test runs on Python 3.10 and 3.13.
- No 150-NPC speed benchmark: this is a small-world behavior
  improvement, not a throughput optimization.
- Only simulation code, scenario tests/docs and simulation CI
  changed. Neither `main` nor any Carlos narrative files changed.

## Remaining realism gaps

A character still does not proactively select an investigation
*because of hunger*. In particular, the preexisting critical
hunger survival policy may suppress investigate even when food is
nearby; that should be solved with an explicitly persisted,
knowledge-limited foraging intent, rather than an unrecorded
score override. No remote food sensing, navigation toward a
known food source, crop growth, price, theft, game hunting or
background simulation has been added.

**Review decision:** Complete within the described opt-in
opportunistic gathering scope; move to knowledge-limited
food-seeking intentions only as an independently tested stage.
