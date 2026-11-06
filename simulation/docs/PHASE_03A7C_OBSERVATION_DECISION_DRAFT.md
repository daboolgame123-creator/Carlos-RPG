# 03-A7c — Cross-NPC injury observation and disclosure contract (proposal only)

Date: 2026-11-06
Branch: `simulation-engine-phase-03a-treatment-integrity`
Status: `DECISION_REQUIRED / WAITING_DECISION`
Parent: 03-A OPEN
Base reviewed: `a12b8aae3f66580657cfc54c4f43a0f08a6e3f46`
No executable permission or gameplay change authorized by this document.

## Existing verified boundaries

- `WorldState.injuries` is a truth ledger, not an observer's knowledge. A record has subject, bounded severity, onset and status. It is currently NPC-only.
- `assess_own_injuries` intentionally reads only the named NPC's own injuries.
- The existing food-knowledge mechanism handles sourced claims but is **food-specific**; do not write injury details under food keys or interpret food confidence as medical reliability.
- Existing local presence checks must account for travel and ongoing actions. Mere shared location is not authenticated injury knowledge.
- The player gateway is not a general NPC medical-record reader.

## Proposed decision for owner approval (not accepted automatically)

**Option A — limited visible symptoms (recommended):** A separate, explicitly invoked and engine-validated local observation may issue only qualitative, non-diagnostic symptoms, when an observable symptom predicate is met; otherwise it emits no claim. The observation is an event with provenance and only changes the observer's own knowledge.

**Option B — no cross-NPC health observation in 03-A:** Retain self-awareness only and defer visible injury interactions. Lowest immediate scope, but NPC cannot respond to another's visible distress.

**Option C — broad automatic inference from co-location:** Rejected recommendation: co-location alone is not evidence, and exposes precise internal health state.

Approval questions: (1) A or B? (2) Are only outward signs such as visible limping or collapse observable, rather than injury severity? (3) Must the observer actively look / have a validated observation opportunity rather than every tick revealing symptoms? Proposed defaults: A; outward signs only; explicit observation opportunity.

## Candidate A contract — implementation requirements, not current capabilities

1. **Source truth versus evidence:** The world injury record may be consulted by a trusted *perception producer* only. Public NPC knowledge receives a coarse code (e.g. `visible_mobility_difficulty`), not injury ID, numeric severity, original cause, treatment history, hidden status or exact onset.
2. **Visibility:** Observer and target must be valid distinct entities, within an actually observable local scene and not traveling/unavailable; a visible sign must be derived by deterministic policy from supported underlying state. Co-location without a sign emits no new belief. Do not claim full line-of-sight until environment supports it.
3. **Provenance:** Accepted observations must bind observer, target, local site, simulation tick, sign code and corresponding trusted source event or engine-verifiable snapshot/revision. Caller-supplied symptom/sign must be checked rather than trusted. Failed attempts must be atomic and leave no knowledge events.
4. **Memory:** Store only an observer-scoped claim with original observed logical time and source; replay, snapshot and SQLite reopening reproduce exactly. A later observation may update or contradict a stale claim; no implicit claim of current medical truth.
5. **Inferences:** An NPC may believe 'Nora seems to be struggling to walk' but must not infer 'Nora has severity 35 exhaustion injury', a diagnosis, its precise cause, or a treatment schedule. No medical identity/metadata in the LLM/player adapter.
6. **Disclosure:** Conversation/rumor propagation is a **separate opt-in task**, requiring source and recipient checks; 03-A7c must not silently spread observations through existing food-knowledge or general gossip machinery.
7. **NPC behavior:** Initial observation makes no automatic rescue, movement, transaction, or treatment decision. Optional assistance decision is downstream with its own authorization, cost and tests.
8. **No magic cures:** Observation never mutates injury, HP, treatment reservations, food balance, time, action schedules or travel.
9. **Compatibility:** Any new persisted event, knowledge schema or changed decision policy requires explicit Schema/Rules analysis/version bump, exact-SHA dual-Python CI, and frozen baseline/parity checks; never rewrite historic hashes.

## Acceptance tests to write after decision

Use a 5–7 NPC disposable village, including Nora, Basim, Salma, Adel, Huda (and optionally Carlos as an independent player-controller case).

- Nora has a verified active injury and visible physical sign; Basim co-located and available obtains **only** the allowed qualitative observation after a legitimate trigger.
- Salma at a different site does not obtain injury knowledge; travel in progress or a busy observer fails closed.
- Nora has an active but non-visible injury: even a present Basim learns nothing from observation.
- An injured target is co-located with Basim, but no observation command/event occurs: no knowledge is generated merely by elapsed time.
- Reject observer=subject, missing actors, forged sign, forged observation origin, fabricated site, past/future timestamp and duplicate command/event ID without partial mutation.
- No observer can read another NPC's true injury ID, numeric severity, onset or paid treatment schedule through the projected claim, player view or narrative adapter.
- Recover/change Nora's injury: old observed symptom remains **historical** until a new supported observation, never a claim of current clinical status.
- Recovery/food/schedule/injury ledgers unchanged before and after observation; deterministic event order, split time, replay, snapshot, SQLite reopen and stale revision rejection.
- Existing 03-A8a treatment integrity and all other regression/parity gates remain green on final SHA for Python 3.10 and 3.13.

## Routing and non-claims

03-A7c is `DECISION_REQUIRED / WAITING_DECISION` until the owner approves a visibility mechanism. Draft authoring is `CHAT_EXECUTABLE`, not completion of the feature. Do not implement any cross-NPC leakage or close 03-A on the basis of this draft. External independent review is deferred, not passed. P0 production is not approved.
