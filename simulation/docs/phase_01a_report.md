# Phase 01-A execution report

## Scope completed

- World state, typed entities/locations/resources, unknown resource support.
- Pure deterministic event application with immutable domain state.
- Ordered event log with SQLite atomic transactions and idempotent commands.
- Optimistic revision checking, time fields and nondecreasing clock rules.
- Canonical hashes, snapshots, recovery and full replay verification.
- Privacy-preserving minimal public view.

## Test result

`python -m pytest -q` — **29 passed** in the local repair workspace; 21 original plus 8 regression tests for future-time ordinary events, unknown actors, unauthorized minting, valid bootstrap replay, disallowed increases, invalid consumption, late bootstrap and idempotency provenance. Tests cover genesis, projection/replay, unknown != 0, invalid event rejection and atomic rollback, idempotency, revision collision, snapshots/tail replay, tamper detection, unsupported schema, event tampering, time freeze, validation, hidden-data view, immutable state, stable hashes, invalid resources, reopening database, duplicate world, cross-store deterministic replay, and fault-triggered transaction rollback.

## Files created

`simulation/pyproject.toml`, `simulation/.gitignore`, `simulation/README.md`, `simulation/src/carlos_sim/__init__.py`, `simulation/src/carlos_sim/domain.py`, `simulation/src/carlos_sim/store.py`, `simulation/tests/test_engine.py`, and this report plus `docs/architecture.md`, `docs/decisions.md`.

## Not implemented

NPC decisions, goals, perception, gameplay session controller, scheduling, real Carlos state import, economy, RPG combat, ChatGPT API and live narration. Their absence is intentional.

## Review notes and risks

- Snapshot hashes detect accidental damage, not malicious tampering by someone with DB write access.
- Default snapshot recovery is fail-closed if the newest snapshot is corrupt (not an automatic fallback to older snapshot).
- `WorldState.from_dict` validates main schema and resource balances; a separate exhaustive event schema registry can be added with future event families.
- The store has an unprotected internal append API and must not be exposed over a network before an authorization layer exists.
- Idempotent retry returns the current world state, which may contain later commits; it does not provide the historical command-result snapshot.
- GitHub story files must remain source references until a separate approved migration is implemented.
- Review corrections: disallow implicit clock advancement, require existing actor references, and restrict resource writes to bootstrap setup or actor-owned consumption. Bootstrap is a trusted caller flag, not an authentication boundary; never expose it to untrusted clients.
- Rules version was raised to 2. Earlier experimental databases require re-creation or explicit migration before use.
- Tests were run locally; GitHub CI has not been run.

## Git status

Published to the isolated `simulation-engine-phase-01a` branch by direct GitHub file commits. `main` and the story files remain unchanged; no merge was performed.
