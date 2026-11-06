# Carlos RPG — 03-A7c: observational injury-knowledge contract (PROPOSAL, NOT APPROVED)

**Date:** 2026-11-06  
**Source base:** `simulation-engine-phase-03a-treatment-integrity` @ `a12b8aae3f66580657cfc54c4f43a0f08a6e3f46`  
**Task classification:** `DECISION_REQUIRED / WAITING_DECISION`  
**Design-only branch:** `simulation-engine-phase-03a7c-observation-design`  
**Status:** Candidate specification only. NO health disclosure implementation, migrations, Rules bump, new events or change to player-visible information.

## 1. Current contracts observed in source

- `injury_behavior.assess_own_injuries(state,npc_id)` deliberately reads **only** the named NPC's persisted injury rows. It never infers another NPC's diagnosis or injury severity.
- `player_perception.validate_player_perception_event` validates local physical presence and event evidence; the currently supported player hearsay pertains only to bounded food claims, not health.
- `knowledge.py` implements **food-specific** belief provenance, observation time, hearsay confidence and anti-instant-resharing. Food rules must **not** automatically become clinical truth or create medical records.
- `03-A8a` closes treatment reservation integrity; it does **not** authorize external disclosure of an injured NPC's underlying record.

## 2. Core separation (proposed)

1. **Ground truth (private):** injury registry, exact severity, onset cause, treatment and IDs. Remain available only to authorized engine mechanics and the subject's own self-assessment.
2. **Observable sign:** externally visible behavior only when actually manifested in the simulated world at a local observation tick (examples: visibly limping, visibly bleeding, difficulty standing). The sign is **not** an injury ID, diagnosis, cause, or severity number.
3. **Witness knowledge:** a time-and-place-grounded memory of an observed sign. It identifies observer, observed subject, sign, logical timestamp and provenance. Witnesses may misinterpret signs; neither memory nor hearsay modifies ground truth.
4. **Hearsay:** attributed third-party statement about a sign. A statement is not equivalent to direct observation, cannot silently overwrite a fresher direct observation and cannot be promoted into verified injury facts.
5. **Player-facing representation:** only signs Carlos directly witnessed or claims he explicitly heard. The narration must not leak the subject's hidden registry or medical course.

## 3. Candidate non-negotiable rejection rules

- Same location alone does **not** grant insight into injury; there must be an explicit perceptible sign and a valid, timestamped observation event.
- No remote sight, travel-in-transit sight, future timestamp, fabricated observer, fake subject, unrecorded sighting, hidden wound behind clothing, automatic medical examination, or diagnosis from a numerical injury severity.
- A health assessment of NPC A cannot iterate or read NPC B's hidden injury records. A pure observation projector must consume **approved, already manifest signs**, not the full injury registry supplied to a narrator.
- A claimant may lie, misunderstand, forget or be wrong. A hearer's claim remains a belief with source; it cannot cause `InjuryRecorded` or `RecoveryStarted` or alter severity.
- Repeated look commands at the same instant must not create inconsistent or multiplying memory; replay of the same event ledger must yield identical observations and knowledge.
- No generated player or NPC dialogue may reveal cause/severity/history absent an authorized source.

## 4. Decisions the project owner must approve (no default selected)

**D1 — Manifestation rule**: 
- **A: explicit sign event**: a physical, world-visible sign is emitted by an approved deterministic rule and persisted before witnesses can observe it. Strongest replay/visibility guarantee; requires a versioned event/rule contract.
- **B: derived sign projection**: approved pure policy computes a visible sign from already persisted physical state and situation at the current tick, then observation is separately recorded. Less stored state but replay equivalence/versioning must be demonstrated.
Neither option permits reading hidden injury data directly into an NPC belief.

**D2 — Perceptibility**:
- Strict: only obvious external signs plus explicit orientation/visibility conditions where the engine can already prove them.
- Minimal first slice: co-located, not traveling, not visually obstructed, explicit visible sign event; no invented eyesight, distance, lighting, NPC medical skill or examination yet.

**D3 — Speech**:
- Phase 1: direct observation only, no automated health gossip.
- Phase 2: explicitly sourced hearsay by co-located speakers, marked unverified, with cooldown/anti-instant-relay tests. Do not silently enable via existing food-sharing paths.

## 5. Recommended smallest executable slice, subject to D1–D3 approval

A narrow contract **without automatic gossip**, based on a manifest `limping` or `visible_bleeding` sign *only when the engine has a sound physical manifestation trigger*. Persist observation provenance; return a witness-safe DTO (subject ID, sign enum, observer ID, tick, source), with **no injury IDs, cause, severity, treatment history or hidden condition**. Keep self-injury decision policy unchanged. Player adapter added only after its own visibility proof and tests.

**Proposed test matrix (not run, no code yet)**:
- NPC A observes sign on co-located B; cannot access B's private injury registry.
- No sign / merely same room / A traveling / B traveling / hidden sign / distant B => no event or information.
- Two concurrent observers receive only what each actually saw; witnesses have independent histories.
- Repeated observation is idempotent as contracted; reverse and replay event sequences deterministic; SQLite reopen and snapshot reproduce the same knowledge.
- Forged cross-NPC evidence or a future tick fails atomically with no persisted event or mutation.
- Existing injury self-assessment, recovery reservation invariants and all frozen event parity tests remain unchanged until a deliberate versioned event/rules transition is approved.
- Python 3.10 and 3.13 complete suites, semantic parity and restore tests green at the *final* code SHA before `CLOSED_TECHNICALLY`.

## 6. Dependencies, risk, next action

**Blocked:** D1–D3 owner policy decision, verified explicit observable-sign source, event/schema compatibility review. **Do not** implement an injury-sharing event, infer severity from a character being near another, modify the player adapter, or migrate historical worlds before approval.

**External validation:** independent adversarial review remains `EXTERNAL_REVIEW_DEFERRED_BY_OWNER`. Production persistence and Windows restoration `EXT-002/EXT-003` remain unverified, and P0 production gating stays closed.

**Next action:** obtain owner choice on the minimal first slice (D1/D2/D3); then write a small versioned implementation plan with test evidence. Until then, this document is a proposal only and does not alter `03-A7c` status.
