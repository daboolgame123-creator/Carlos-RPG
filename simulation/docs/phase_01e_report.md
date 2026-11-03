# Phase 01-E — autonomous NPC lifecycle report

## Implemented

`LivingWorldEngine.advance` coordinates independent NPC re-evaluation, action start and completion across multiple NPCs as the player explicitly advances logical time. It supports two or more consecutive actions per NPC, simultaneous NPC work, deterministic schedule ordering, per-NPC cooldowns and belief-limited deterministic decisions. It stops at player-interrupt signals and returns the remaining requested duration. The entire operation is committed as one event-sourced SQLite transaction, with a configurable event count cap and strict rollback on invalid action prerequisites. It does **not** update the real Carlos character or story.

## Verification

Command: `cd simulation && PYTHONPATH=src python -m pytest -q` → **132 passed before review**, **134 passed after review** (112 baseline + 20 new tests) in local runtime. `python -m compileall -q src tests scenarios` passed. Test coverage includes multi-cycle execution, concurrent NPCs, predictable ordering, player interrupts, same-time events, cooldowns, detached offline time, restarts, snapshots, event budget rollback, idempotency and revision conflicts, missing resource prerequisites, Carlos/player exclusion, no-NPC worlds, single vs split command consistency, reproducibility across two databases, and bounded long advances.

Five-NPC village demo: `PYTHONPATH=src python scenarios/test_village/demo_living_world.py` yielded **27 started actions and 22 completed actions** in 720 simulated seconds, without player interruption. Five actions remained in progress at the end. Figures are test-only, not canon. No GitHub-hosted CI run has been claimed.

## Changed files

New: `src/carlos_sim/living_world.py`, `tests/test_living_world.py`, `scenarios/test_village/demo_living_world.py`, `docs/phase_01e_report.md`. Updated: `src/carlos_sim/__init__.py`, `README.md`, `docs/architecture.md`, `docs/decisions.md`.

## Limitations

No autonomous decisions are made when no player time command is underway. No system clock or background task is used. The existing manual `TimeEngine.advance` does not run NPC planning. No real social/world knowledge generator, action-precondition alternatives, production economy, settlements, movement, relationships, combat, character death, knowledge leakage into player view or ChatGPT narration is implemented. Invalid prerequisites abort the whole time command; a fallback policy is future work. The in-process session and trusted capability switches are **not** network authentication. Fixed durations/utility formula and resource counters remain *prototype rules*. The phase reuses **schema 5/rules 6**, without importing real Carlos story state, migrating older experimental schemas or altering `main`.

## Post-implementation review — 2026-11-03

**Finding:** An NPC that had already recorded an intention through `NPCService.decide` at the current logical tick remained idle when the autonomous coordinator was called. The decision cooldown prevented `choose_action` from selecting the already-pending intention; the NPC could lose up to 60 simulated seconds before work began.

**Fix:** During an explicit `LivingWorldEngine.advance`, before asking for a new decision, detect a valid existing `last_decision` recorded at exactly the current simulation tick. If no action is currently running, start that intention directly, without emitting a duplicate `NPCDecisionRecorded` event. Future/expired intentions do not bypass the cooldown. Action-start and replay safeguards still apply.

**Regression:** Two new tests verify immediate start for a previous manual decision and ensure the historical decision is not recorded twice. Local Python run: `python -m pytest -q` → **134 passed** (132 previous + 2 new), `python -m compileall -q src tests scenarios` passed, and the five-NPC demo reproduced **27 started / 22 completed** actions in 720 simulated seconds. The uploaded Git blobs for `living_world.py` and `test_living_world.py` match the locally executed files. No GitHub CI run was performed.

**Review disposition:** Phase 01-E is ready for closure within the prototype scope. No source files outside `simulation/` were changed, no Carlos story data was modified, and the branch was not merged.
