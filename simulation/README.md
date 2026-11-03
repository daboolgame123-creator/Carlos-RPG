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
- `ResourceChanged`: `{owner_id, resource, previous, current}`; `null` means unknown
- `TimeAdvanced`: `{from, to}`; explicit logical time transition

Every event requires a nonempty `cause`, optional `actor_id`, and nondecreasing integer `time`. Time progression is **not** automatic. The API does not yet have a session authorization layer; only trusted local callers should call `append`.

## Limitations

This is a foundation, not an RPG or narrative engine. No NPC decisions, knowledge propagation, tasks, combat, prices, ChatGPT connector, permissions, or automatic player-context perception. The player view is intentionally minimal to avoid disclosing secrets. Rebuild verification detects discrepancies between snapshots and the complete event log. It is not intended to prevent a privileged database operator from rewriting both events and stored hashes.
