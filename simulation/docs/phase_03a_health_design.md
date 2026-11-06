# Phase 03-A — Health, injury and recovery: isolated design contract

Date: 2026-11-06
Status: DESIGN_DRAFT / NOT IMPLEMENTED / NOT TESTED
Work classification: CHAT_EXECUTABLE (design), CHAT_PARTIAL_EXTERNAL_GATE (runtime verification)
Branch: design-phase-03a-health
Baseline: green documentation commit 7a124c83f3a350f813f46af1f6ea10a342ad18b5
Independence: does **not** consume J1c2b-LAW, institutional authority, title, courts or pending authority-draft verification.

## Purpose

Make injury and recovery causal, local and persistent, rather than arbitrary story decisions. Extend the already-existing opt-in RPG profile and event-sourced world, but never silently interpret old HP changes as injuries. The first implementation must remain a **disposable-world, trusted-engine-only** feature. Combat, death, disease spread, professions, medicines and AI diagnosis are separate stages.

## Decisions frozen for first proposed slice (no executable rule yet)

1. A character's HP is distinct from a list of specific injuries. Existing profile HP alone is insufficient to infer *where* an injury exists or its cause. When existing old worlds lack an injury ledger, it is **unknown**, not 'healthy'.
2. An injury is created by a validated event referencing the affected character and a source/cause already established in the same transaction or accepted trusted scenario; never by a narrator's assertion.
3. Injuries have stable IDs, affected entity IDs, onset simulation time, bounded severity, and an explicit state (active/recovered). A state change is event-sourced and replayable. No duplicate recovery and no spontaneous recovery by wall-clock passage.
4. Recovery is an **action with time and prerequisites**, not a free `wait` or a blind HP increase. An initial recovery slice may record medically agnostic resting/recovery progress, but must not claim treatment efficacy or clinical realism.
5. Injury impairs action participation based on deterministic capability gates; never alter queued actions halfway without an explicit interruption/cancellation event. Integrate with existing scheduled action machinery rather than introduce a second independent clock.
6. The actor cannot claim to heal another NPC at a remote location; check co-location, travel/work commitments, identity and trust boundary at actual event application.
7. A player sees only permitted symptoms, current permitted vitals and observable consequences. NPC-only internal medical state is not exposed through player status or narrative/LLM adapters.
8. Rules operate in logical simulation time; time-splitting invariance must be proved for equivalent schedules. Recovery cannot happen before its completion event or at negative elapsed duration.
9. Old SQLite worlds with incompatible schema/rules are refused unmodified unless a separate, tested migration exists; preserve original parity expectations when feature is disabled.
10. No injury generates XP, currency, skill, item or death automatically in this stage.

## Minimal domain event design (proposed, not yet implemented)

- `InjuryRecorded`: trusted, verified source; affected ID; injury ID; severity 1..100; onset time == event time; provenance references; optional verified HP decrement bounded to currently known HP, never invent HP from unknown. The event type is only a proposal until full trust validation is specified.
- `RecoveryStarted`: valid injured subject + real caregiver/self + real location, active injury, available slot and positive duration; records a scheduled action and resource/effort reservation if specified.
- `RecoveryCompleted`: issued only for the exact eligible scheduled action at or after due time; can reduce severity only by an explicitly defined, bounded rule; cannot resolve another injury.
- `InjuryStatusChanged`: separate transition to recovered only when deterministic criteria are satisfied. A character cannot self-authorize this event from an untrusted command.

If reusing existing event families is safer, document the exact equivalence before implementation. All of these names are provisional and must not be emitted by current code.

## Acceptance examples (5–7 characters, not 150)

1. Nora is injured in a trusted scenario: HP and injury record are consistent where HP is known, event provenance exists, and persistence survives process restart.
2. Basim tries to heal Nora from a different site: reject with **no mutation**.
3. Salma starts a valid local recovery effort; before due time, no benefit; after exact completion, a deterministic bounded improvement occurs.
4. Two caregivers attempt the same exclusive recovery slot concurrently: only one succeeds; losing command is rejected without duplicate healing.
5. An invalid or spoofed source, negative duration, unknown HP, wrong injury ID, fabricated caregiver, duplicate ID, stale revision and conflicting queued work fail closed.
6. A resting character's recovery does not cause food, copper, medicine, energy or XP to appear from nowhere.
7. Simulate 600 seconds as one step vs ten 60-second steps: same accepted events and semantic state under equivalent event boundaries.
8. Snapshot, full replay, SQLite reopen, backup-to-new-target and corruption rejection reproduce exactly.
9. Entire regression suite + compatibility parity + adversarial checks on Python 3.10 and 3.13 pass on the **final implementation SHA**.
10. Player observation returns no hidden injury details for NPCs out of sight.

## Implementation sequence (provisional)
- 03-A1: precise audit of RPG profile events, state validators and scheduling/replay; then choose the minimal compatible domain contract.
- 03-A2: strict injury record (trusted/disposable) and deterministic projection with focused negative tests.
- 03-A3: timed recovery with explicit cost/interruptions, co-location and resource requirements.
- 03-A4: capability effects and visible symptoms through permission-filtered observation.
- 03-A5: replay, parity, adversarial, backup/restore, exact-SHA CI and technical closure report.

## Boundaries and live-world safety

- No production or real-player save changes; no `main` change.
- No permanent hidden regeneration from merely advancing wall clock.
- No combat, death, criminal responsibility, courts or title effects.
- Existing `RPGVitalAdjusted`-style test-only adjustments (exact name to be verified) must not be misrepresented as approved medical treatment.
- `J1c2b-LAW-DRAFT` is still pending an independent verification task elsewhere; this document does not imply its completion.
- This design is **not** an approved mechanics contract or tested code; an audit of actual event signatures is required before implementation.

## Planning status

The independent design outline is completed. 03-A1 implementation remains pending source audit and acceptance checks. Branch stays separate and must not be merged into the 04-A branch while concurrent changes are unverified.

## 03-A1 source audit — first concrete findings (2026-11-06)

Reviewed actual `domain.py` and `rpg_state.py` at the independent green baseline. **Important correction to the initial plan:** `rpg_profiles` only accepts `state["entities"][id]["controller"] == "player"`. It is **not** an NPC health system. `PlayerRPGInitialized` is trusted time-zero bootstrap and `PlayerVitalChanged` is exclusively trusted `source="test-scenario"`, with explicit previous/current and no gameplay healing. Therefore no NPC injury reducer may assume the existing RPG ledger holds NPC vitals.

The actual domain reducer processes `ScheduledEventCreated`, `ScheduledEventFired`, and `ScheduledEventCancelled` with strict due/order rules. Recovery must integrate with the existing schedule without bypassing scheduled event order or mutating time itself.

### Scope correction required before implementing 03-A2

- Implement **NPC injury evidence/capability** in an independently validated bounded structure instead of placing NPCs in `rpg_profiles`.
- Player HP may only be coupled to health by an explicit new trusted event contract (and schema/rules bump), not by silently reusing `PlayerVitalChanged` or treating missing HP as zero.
- Tests for Nora/Basim/Salma should first prove that they are NPCs and have no RPG player profile, then test injury state independently of HP. A separately configured player profile scenario is needed for HP-specific behavior.
- Audit the rest of the scheduling command producers and player-observation gateway before choosing field names and event authorization; do **not** implement a reducer yet.

This source audit is a partial 03-A1 deliverable. It has not been runtime tested. No actual injury state or healing mechanic has been added.

## 03-A2 preliminary read-only injury intake (2026-11-06)

The audit now covers `PlayerGateway.status/inspect/observe`, `SQLiteEventStore`'s replay authorization rows, and `domain.py` schedule creation/firing/cancellation. Important constraint: privileged scheduler payloads are protected by existing capability flags and cannot safely be reused for a new recovery action without a dedicated authorization and validation path. Also, `PlayerGateway` explicitly reveals only the invoking player's RPG profile; proposed NPC injury records must NOT be automatically exposed via it.

New isolated code:
- `simulation/src/carlos_sim/injury_intake.py` at commit `6eb1a651`.
- `simulation/tests/test_injury_intake_03a.py` at commit `1e84b4c7`.

This is an **unverified test-scenario intake proposal**, not an injury reducer. It validates existing subject ID, ID syntax, severity 1..100, exact logical onset time and test-only source description. Critically, a caller-provided source reference **is not verified provenance**, so every returned packet explicitly says `source_provenance_verified=False`, `injury_recorded=False`, `hp_adjustment=None`, `commit_authorized=False`. It does not write, heal, authorize a gameplay command or expose private NPC health.

A temporary stand-alone contract test for the matching pure function passed 3 unittest cases and 11 invalid parameter variants in the chat's Python environment. **That is not a test of the GitHub package or pytest integration**. The committed tests must be run on exact code SHA in real engine environment; full CI/parity are also pending. The 03-A stage remains OPEN.

Before persisted injuries, build and test a trusted **source-of-injury event** authorization path, independent NPC injury storage with schema/rules migration policy, and explicit scheduler capability for recovery. Do not treat speculative intake as proof that any injury happened.
