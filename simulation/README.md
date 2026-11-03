# Carlos Simulation — Phase 01-A

Independent, offline Python core for *test worlds only*. **No actual Carlos story data is imported or changed.**

## Requirements

Python 3.10+; SQLite from the standard library. For tests, install `pytest` (not required for the engine).

## Run tests

```bash
cd simulation
python -m pip install pytest
python -m pytest -q
```

## Minimal local use

```python
from carlos_sim import SQLiteEventStore, DomainEvent

with SQLiteEventStore("example.sqlite") as store:
    store.create_world("village-test")
    event = DomainEvent("LocationCreated", None, "test setup", 0,
                        {"id": "market", "name": "Market"})
    store.append("village-test", "command-1", 0, [event])
    store.snapshot("village-test")
    assert store.verify("village-test").revision == 1
```

Run the script with `PYTHONPATH=src python your_script.py` from the `simulation` directory, or install the package using `python -m pip install -e .` (requires setuptools).

## Supported initial event types

- `LocationCreated`: `{id, name}`
- `EntityCreated`: `{id, name, location_id, controller}` where controller is `npc` or `player`
- `ResourceChanged`: `{owner_id, resource, previous, current, source}`. `source="initialization"` requires a trusted `append(..., bootstrap=True)` operation at simulation time zero with `previous=null` and a non-null initial amount. `source="consumption"` requires the owning entity as `actor_id` and strictly decreases a known balance. Arbitrary creation, production and transfers are NOT supported.
- `TimeAdvanced`: `{from, to}`; explicit logical time transition

Every event requires a nonempty `cause`, optional `actor_id`, and nondecreasing integer `time`. Ordinary events must have the current world time; only `TimeAdvanced` can change it. Actor references must resolve to an existing entity. Time progression is **not** automatic. The API does not yet have a session authorization layer; only trusted local callers should call `append` or set `bootstrap=True`. Bootstrap is a caller-supplied capability flag, **not authentication**. Do not expose it over an API. The changed resource rules use `rules_version=2`; old experimental databases are incompatible and need explicit migration or re-creation.

## Limitations

This is a foundation, not an RPG or narrative engine. No NPC decisions, knowledge propagation, tasks, combat, prices, ChatGPT connector, permissions, or automatic player-context perception. The player view is intentionally minimal to avoid disclosing secrets. Rebuild verification detects discrepancies between snapshots and the complete event log. It is not intended to prevent a privileged database operator from rewriting both events and stored hashes.

## Phase 01-B: manual clock and scheduled signals

`TimeEngine` is a local, trusted coordinator. Opening a session does **not** start an asynchronous clock; only `advance` moves logical time. Closing or restarting the process freezes the world.

```python
from carlos_sim import SQLiteEventStore, TimeEngine

with SQLiteEventStore("test_world.sqlite") as store:
    store.create_world("village")
    clock = TimeEngine(store)
    clock.open_session("village")
    state = clock.schedule_signal("village", "alarm", due=30,
                                  payload={"label": "bell"}, interrupt=True,
                                  expected_revision=0)
    result = clock.advance("village", seconds=100,
                           command_id="wait-1", expected_revision=state.revision)
    assert result.state.time == 30
    assert result.remaining_seconds == 70
    assert result.interrupted
    clock.close_session("village")
```

A scheduled item is a *signal*, not arbitrary Python execution, a quest, a payment or an NPC action. The schedule is durable; the session flag is intentionally **not** durable. `clock_authorized=True` on the low-level event store is a **trusted internal capability**, not a security boundary; do not expose the store directly to HTTP or untrusted callers. `advance` rejects reusing a high-level command ID (rather than returning its original timing receipt). Cancelling uses `clock.cancel` before an item fires.

Phase 01-B increments the world schema version to 2 and rules version to 3. Existing experimental databases from the earlier phase require explicit migration or recreation. Details: `docs/phase_01b_report.md`.
