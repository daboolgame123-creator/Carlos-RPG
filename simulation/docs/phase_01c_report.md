# Phase 01-C — NPC state and deterministic decision prototype

## Status

Implemented and tested **locally** on the Python Phase 01-B baseline. **Not a complete autonomous living-world engine.** The current implementation records explainable intentions; it does not carry out commerce, movement or combat. Only a trusted play-session caller can request an NPC decision. The player-controlled Carlos entity is never selected by the NPC planner.

## Capabilities

- Immutable, event-sourced NPC profiles keyed to existing NPC-controlled entities.
- Strictly validated three needs (fatigue/hunger/safety) and three goal weights (earn/explore/survive) on integer 0–100 scale, all **test prototype** values.
- Per-NPC beliefs with provenance, receipt time and confidence; NPC policy reads its own profile and beliefs, not global knowledge.
- Deterministic integer utility scores for four preliminary intentions: rest, work, investigate and wait. Tie-break order is stable.
- `NPCDecisionRecorded` is validated against policy, actor and cooldown. Decision records do not themselves modify resources, NPC position, HP, XP or logical time.
- Trusted local `NPCService` requires an active `TimeEngine` session. No decisions run while the session is closed or on application restart.
- Durable NPC profiles, beliefs, needs, decisions and cooldowns through SQLite event log and verified snapshots.
- Five-person isolated fixture in `scenarios/test_village`, with reproducible decisions and no link to Harthn.

## Verification

Run from `simulation/`:

```sh
python -m pytest -q
PYTHONPATH=src python scenarios/test_village/demo.py
```

**72 passed** locally, including the original 50 tests and 22 NPC tests. The five-person demo produced: nora=rest, basim=work, salma=work, adil=investigate, huda=rest. These are **intentions**, not physically executed actions. No GitHub CI or cross-platform runtime verification was performed.

## Version and boundaries

Schema v3 / rules v4. Phase 01-B experimental SQLite files need an explicit migration or recreation; no Carlos story database exists yet. `npc_authorized` and `bootstrap` are trusted internal store flags, not authentication; exposing them to untrusted remote callers is prohibited. External information delivery remains a trusted explicit event; no automatic gossip transmission or sensory model exists. NPC policy does not automatically run from the scheduler yet; this will be integrated with decision cadence in a later reviewed step.

## Deferred

Action resolver, activity durations, automatic needs decay, world perception, location movement, trade, broader goals, personality traits, dynamic memory, rumors, player-facing views and LLM narration are not implemented. Exact decision weights are test-only and must not be imported into Carlos's world without approval. Narrative documents and the real Carlos state remain unchanged.
