# Carlos Simulation Engine — Phase 01-B report

## Delivered

- Explicit, integer logical-time advance through `TimeEngine.advance` during an in-process active play session.
- A durable, ordered schedule (`ScheduledEventCreated`, `ScheduledEventCancelled`, `ScheduledEventFired`).
- Safe, deterministic signal-only scheduling with unique per-command IDs; no custom code or arbitrary state mutations fire automatically.
- Simultaneous signals execute by due-time then stable schedule order.
- Interrupting signals stop advancement after firing and return unconsumed seconds; continuing is a new explicit play command.
- Scheduled queue and ordering counters are persisted within `WorldState` and recovered by snapshots or event replay.
- Atomic clock events/queue operations in the existing SQLite store; no half-executed command after event-limit rejection.
- Ordinary events cannot change logical time. Direct trusted clock event writes require `clock_authorized=True`; do not expose this flag to untrusted callers.
- Session state is deliberately ephemeral, so reopening after an app restart never advances time automatically.

## Verification

Local command: `cd simulation && python -m pytest -q`.

**50 passed**, including the original 21 Phase 01-A tests, the 8 original Phase 01-A regression guards, and 21 Phase 01-B tests. Additional `compileall` check passed. Results are for local Python 3.13; GitHub CI was not executed.

## Changed files

- `simulation/src/carlos_sim/domain.py`: schedule projection and validation, schema/rules versions.
- `simulation/src/carlos_sim/store.py`: guarded clock commits, persisted provenance flag.
- `simulation/src/carlos_sim/time_engine.py`: new explicit session/time coordinator.
- `simulation/src/carlos_sim/__init__.py`: public exports.
- `simulation/tests/test_engine.py`: retained regression suite, trusted clock capability on direct tests.
- `simulation/tests/test_time_engine.py`: new clock/schedule tests.
- `simulation/README.md` and architecture/decision/report documentation.

## Important limitations

- This is a test-world scheduler; it supports **signals only**. It does not autonomously generate NPC choices, execute trade, change HP/XP or call ChatGPT.
- `open_session` and `clock_authorized=True` are local trusted API conventions, **not authentication or access control**. A real app must authenticate commands before using them.
- A replayed high-level `advance` command ID is rejected explicitly instead of returning historical `AdvanceResult`; the underlying event store still ensures atomic command idempotency.
- Scripted event scheduling during a multi-hour action is not implemented; advances are explicit and interruption-aware.
- Event count cap is per requested advance; too many due events reject the whole command, with no partial commit.
- Experimental databases from Phase 01-A have schema/rules versions 1/2; this phase uses versions 2/3 and requires recreation or a separately designed migration. No genuine Carlos state is imported.
- The state ledger is not suitable for secrets in a public GitHub repository.

## Story protection

No change to root narrative documents, Carlos XP, inventory, relationships or Harthn events. No branch merge into `main`.

## Post-review corrective verification

Two confirmed defects were fixed without changing the narrative files:

1. `ScheduledEventFired` now must use the current logical time; it cannot set the world clock through the event envelope.
2. `TimeEngine.advance` checks `max_events_per_advance` before breaking on an interrupting event.

Two additional regression tests reproduce the original failures and check that rejected commands leave state and the commands table unchanged. Local command `python -m pytest -q` yielded **50 passed**; `python -m compileall -q src tests` also completed successfully. GitHub CI was not executed.
