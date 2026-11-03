# Architecture decisions — Phase 01-A

- **Python 3.10+**: lightweight, typed, local, testable; standard library SQLite and JSON.
- **Event log as source of truth**: state can be replayed; snapshots are accelerators, not authoritative over events.
- **No plugin or API runtime**: avoid consuming ChatGPT/API quotas for core simulations.
- **No default zero for unknown resources**: missing or `null` means unknown; explicit zero is distinct.
- **Determinism**: integer logical time, ordered event sequences, canonical JSON and no random or wall-clock calls.
- **Immutable projections**: frozen dataclasses plus recursive read-only copies prevent accidental mutations from callers.
- **Private-by-default view**: hide state until permissions and perception are implemented.
- **Separate from story**: no imports, content changes or overwriting the narrative reference files.
- **Conservative errors**: mismatched snapshots, versions, event ordering and payloads raise exceptions rather than self-heal silently.

- **Resource provenance in 01-A**: bootstrap-only initial stock at time zero; owning actor can consume but cannot mint resources. Production/transfers need future dedicated rules. Caller-provided bootstrap MUST be protected at future API boundary.
- **Rules v2**: incompatible with the original Phase 01-A experimental schema/data. No database migration is included because there are no production saves.

Deferred decisions: RNG algorithm/state; knowledge models; NPC utility-scoring; scheduled actions; sessions; identity and authorization; importing story facts; future DB event migration policy.
