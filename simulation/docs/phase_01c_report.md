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

**72 passed** before review and **84 passed** after corrections, including the original 50 tests and 22 NPC tests. The five-person demo produced: nora=rest, basim=work, salma=work, adil=investigate, huda=rest. These are **intentions**, not physically executed actions. No GitHub CI or cross-platform runtime verification was performed.

## Version and boundaries

Schema v3 / rules v4. Phase 01-B experimental SQLite files need an explicit migration or recreation; no Carlos story database exists yet. `npc_authorized` and `bootstrap` are trusted internal store flags, not authentication; exposing them to untrusted remote callers is prohibited. External information delivery remains a trusted explicit event; no automatic gossip transmission or sensory model exists. NPC policy does not automatically run from the scheduler yet; this will be integrated with decision cadence in a later reviewed step.

## Deferred

Action resolver, activity durations, automatic needs decay, world perception, location movement, trade, broader goals, personality traits, dynamic memory, rumors, player-facing views and LLM narration are not implemented. Exact decision weights are test-only and must not be imported into Carlos's world without approval. Narrative documents and the real Carlos state remain unchanged.

## Post-review corrections (2026-11-03)

Three issues found in code review have been corrected in the isolated Phase 01-C branch:

1. **World freeze:** SQLiteEventStore now rejects NPC needs, information deliveries, belief acknowledgements and decision writes unless a play session is open for that world. TimeEngine instances sharing the same store also share this session flag; simply creating a new TimeEngine cannot bypass a closed session. Bootstrap setup remains possible without gameplay.
2. **Minimum decision cadence:** deterministic policy requires at least 60 simulated seconds between NPC decision events, enforced by both the reducer and NPCService. A trusted low-level write cannot shorten this minimum.
3. **Information provenance:** added NPCInformationDelivered events with recorded sender, shared location, channel, receipt time and claim; NPCBeliefReceived must reference and consume a matching pending delivery. Unique delivery IDs are remembered to prevent reuse. Incorrect sender/source, missing delivery, duplicate receipt and offline delivery are rejected. The record proves **what was submitted to the simulation**, not the objective truth of the rumor or that a human really uttered it.

**Verification:** `python -m pytest -q` locally: **84 passed** (72 pre-review + 12 new regression tests). `python -m compileall -q src tests`: passed. No public network or external AI service used in tests. GitHub CI not run. This report does not represent an independent hosted test run.

**Schema/rules:** v4/v5. Existing local experimental SQLite databases from v3/v4 need explicit migration or recreation; no automatic migration and no Carlos story state import. Future network-facing application must authenticate and authorize session activation and trusted NPC capability; neither an event payload nor an in-process flag proves external identity.
