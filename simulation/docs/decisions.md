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

## Phase 01-B decisions

- **Clock is manual:** opening/closing a session never advances elapsed time. All time advances are explicit integer-second commands.
- **Local session lifecycle:** in-process only; restarting requires opening a new session, and downtime is not simulated.
- **Scheduled signals only:** deliberately no arbitrary code callbacks or automatic changes to RPG/commerce/quests.
- **Deterministic ordering:** due time, then a durable monotonically increasing scheduling sequence.
- **Interruption:** stop immediately after a triggering signal is recorded; return the unused requested duration, do not automatically continue.
- **Trusted clock capability:** low-level writes have an explicit `clock_authorized` parameter persisted with commands. The future API must implement actual authentication and authorization.
- **Strict replay:** queue and ordering state are projected from events and included in snapshots and hashes.
- **Version bump:** schema 2, rules 3. No silent migration of experimental databases.

Open questions for later phases: NPC decision cadence, resource production and transfers, multi-actor interrupts, semantic interpretation of signals, persistent user identity, and authenticated gameplay sessions.

## Phase 01-C decisions

- **NPC perspective:** the planner consults only the NPC's stored needs, goals and beliefs; a rumor can be wrong.
- **Prototype policy:** integer scores, stable tie order, four possible intentions. No unseeded RNG.
- **Separation of planning and execution:** a selected intention has no economic, combat or movement side effects.
- **Event provenance:** decisions are validated against policy before committing and use trusted local planner capability.
- **Time boundary:** decisions require an active local play session and are cooldown-limited; there is no wall-clock tick or autonomous background service.
- **Migration:** schema 3/rules 4; no silent conversion of test databases.
