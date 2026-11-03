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

## Phase 01-C review resolutions

- Store-level session checks prevent bypassing application-level pause for NPC mutations. Session activity is explicitly ephemeral and not wall-clock driven.
- Fixed minimum 60 simulated seconds between NPC decision events, enforced by projection and service.
- Claims and their delivery are distinct events with traceable identifiers. A belief is not populated before a matching delivered claim is acknowledged; delivery identity remains reserved after consumption.
- Sender identity and co-location are validated against simulated entities; trusted callers remain responsible for the authenticity of outside inputs. No omniscience or automatic truth inference.
- Schema v4 / rules v5; do not silently migrate old prototype databases.

## Phase 01-D decisions

- Resolve action effects at a durable scheduled completion, not immediately on deciding or starting an action.
- NPC routine completions proceed while simulated time advances without needlessly interrupting the player.
- Apply effects through a deterministic, pure event projection to preserve full replay and atomicity.
- Separate NPC intentions from executed actions, and refuse stale decisions, duplicate execution, per-NPC overlapping work or cancellations that would strand an action.
- Record explicit test `labor_units`/`investigation_attempts`; they are neither money nor guaranteed goods/discoveries.
- Unknown resource counters are never assumed to equal zero; bootstrap them explicitly and require known values before action start.
- Local-session checks apply to direct clock writes too; no world time advances while app/session is closed.
- Defer action cancellation, travel, combat, production, economic transfer, knowledge generation, continuous NPC decision scheduling and production DB migrations.

## Phase 01-E — Autonomous life decisions

- Opt-in `LivingWorldEngine` coordinates entire NPC cycles during an explicit in-game time request; no wall-clock ticking, background simulation or external API.
- Commit the whole requested time step as one transaction, avoiding partial NPC cycles when event budgets/rule validation fail.
- Process already due signals before making new decisions and prioritize explicit player-interrupt events over NPC continuations.
- Choose NPCs in ID order and preserve durable signal ordering; preserve per-NPC knowledge separation and decision cooldowns.
- Allow repeated actions as time passes, including multiple NPCs in parallel. Completing an action cannot itself create a new narrative scene or reveal hidden facts.
- Fail closed on missing required resource counters or duplicate action IDs; do not invent resources, discoveries or results.
- Keep `TimeEngine.advance` unchanged for backward compatibility; applications wishing for autonomy must explicitly use the new coordinator.
- No change to schema 5/rules 6; original test databases can be opened with the same event formats.

## Phase 01-F decisions

- World geography is an explicitly constructed, bidirectional graph; no arbitrary teleportation and no pathfinding or goal-based travel yet.
- Moving consumes simulation time, survives an application restart, and respects player-interrupt signals.
- A traveling NPC is physically anchored to its departure location in state until arrival, while its `traveling` flag prevents local action/perception; precise in-transit positions are outside current scope.
- Perception captures only currently co-located entity IDs at an event timestamp, never omniscient/current global knowledge.
- Observation snapshots can be stale and are not automatically converted to the NPC's private semantic beliefs.
- Multiple arrivals at the same tick are resolved in persistent schedule order; each snapshot reflects the world as of that completion event.
- No automatic route choice, sight/occlusion, stealth, encounters, combat, hearing, moving player characters or canonical Harthn geography yet.
- Movement capability and session flags are trusted local controls, **not network authentication**. Schema/rules versions advance to 6/7.

### Phase 01-F review resolution

- In-transit NPCs are not present at their stored departure location for the purpose of local perception, message delivery or new activity planning.
- Preserve origin in stored entity state until arrival; derive physical presence from active travel status rather than introducing invented intermediate coordinates.
- Enforce in-transit guards at both high-level planner and low-level event projection; reject impossible local message delivery whether the traveler is sender or recipient.
- After arrival, restore ordinary observation, message and decision eligibility. Preserve stale historical observations as dated evidence rather than silently replacing them.

## Phase 01-G decisions

- Opt in to spatial autonomy; preserve earlier NPC activity semantics when disabled.
- Survey only actual adjacent roads while the NPC is idle, not a global map.
- Explore by minimum reachable known-road travel seconds, then deterministic destination ID.
- Keep route memory per NPC; explicit targets must be learned and reachable.
- Reuse durable arrival signals, atomic event batches, pause rules and existing local capability checks.
- Prefer an already recorded activity intention over newly proposed autonomous travel.
- Defer professional travel goals, road hazards, map changes, inter-NPC map sharing, traffic and richer motivations.

### Phase 01-G review resolution

- Enforce learned-road restrictions at the common movement reducer whenever a navigation profile exists, not only in the autonomous planner.
- Maintain explicit-route compatibility for older test worlds without NPC navigation profiles.
- Add both direct-service and low-level event regression tests, verifying rollback and the ability to travel after local surveying.

## Phase 01-H design decisions

- Social relationships are **asymmetric** and each NPC remembers its own trust; there is no automatic reciprocal relationship.
- Use traceable typed speech acts and deterministic interpretation for the first version, rather than inferring social outcomes from generated text.
- Message creation and acknowledgement are distinct events; only acknowledgement changes the recipient's trust.
- Apply co-location plus in-transit checks at event-projection level; preserve replay and the explicit-player-time freeze.
- Distinguish offered favors and requests from actual aid or debt. No resource transfer or reward is created by a sentence.
- Defer fully autonomous social initiative, partner preferences, dynamic alliances, reputation, deception mechanics and LLM dialogue to later reviewed phases.

### Phase 01-H review resolutions

- Preserve the place of a locally delivered speech act: delayed acknowledgement cannot move to another location with the characters.
- Limit repeated identical social acts from the same sender to the same recipient within one simulated tick. Different kinds can occur in the same tick; later repetition requires logical time progression.
- Treat the guard as anti-duplication, not fully realistic social pacing; future phases should connect influence to attention, time, truth, reputation, promises and fulfilled actions.
- Bump rules version 9→10 without changing schema version 8, to reject earlier replay semantics pending migration.

## Phase 01-I design decisions

- Make independent social initiative explicitly opt-in on the living-world coordinator, not an implicit change to the manual time engine.
- Base motives on **speaker-owned** needs and directed relationship, never on hidden information belonging to the recipient. Select only idle, present NPC peers and never autonomously act as Carlos.
- Maintain causal audit: record typed speech and receiver acknowledgement using existing domain events, under one atomic, bounded time command.
- Respect previously recorded manual activity intentions, and do not allow conversation to interrupt active work or travel.
- Prevent social influence farming: minimum 180 simulated seconds between outgoing initiatives per speaker, and 900 seconds between same-topic auto-initiatives to the same partner. Earlier Phase 01-H low-level anti-duplication rules remain intact.
- Treat greetings, requests, offers and threats as *speech only*. Defer actual assistance, negotiation, deception, dialogue generation, reputation, obligations, partner consent and duration-based conversation costs.
- Keep schema 8/rules 10 and story state unchanged. Verify each phase before progressing.

## Phase 01-J decisions

- Distinguish spoken intent, acknowledged promise and **actually transferred** goods. Words alone are not help.
- Permit only explicitly initialized, conserved `food` and `water` balances in this prototype; do not invent missing supplies or allow negative inventory.
- Track each request and authorized resolution through immutable event replay. An actual transfer earns the *recipient's* directed trust, not the provider's.
- Enforce co-location, active play sessions, separate trusted assistance capability and optimistic concurrency at the event-store/reducer boundary.
- Permit refusal, cancellation and insufficient-stock failures without silent material effects or partial commits.
- No autonomous physical help, economic production, deadlines, multi-resource barter, debt or player-character actions in this phase. Maintain `main` and real story state unchanged.

### Phase 01-J review decisions

- Require the active play session for actor-owned resource consumption, even through direct event-store calls; preserve setup-only `bootstrap` inventory initialization.
- Treat withdrawal of a local request or promise as an in-person communication. Do not grant instantaneous, unmodeled remote awareness; both parties must be physically co-located and idle.
- Allow withdrawal after a meeting at another site, without changing inventory or trust. Future remote cancellation must add a real messaging/delivery protocol.
- Increase rules version to 12 (schema stays 9), retain six new regression tests and 282 locally passing tests. No migration is performed automatically.

## Phase 01-K decisions

- Opt in to autonomous physical assistance; keep 01-J manual workflow and
  all previous living-world defaults unchanged.
- Need-driven requests use the requester's **own** hunger, inventory and trust;
  provider response uses **provider-owned** resources, hunger, trust and promises.
- Do not infer a food contract from a generic `request_help`/`offer_help`
  speech act. A request is a separate typed obligation and is auditable.
- Enforce a per-requester 900-second retry interval, a one-transition-per-NPC
  per-tick bound, and a later tick for actual physical delivery.
- A provider does not promise stock already committed to others; promise
  acceptance still does not escrow goods. Broken promises can be withdrawn
  only in person under the 01-J reducer rules.
- Defer hunger relief by eating, thirst-driven requests, timed carrying,
  debt, automatic negotiation, player-directed charity and narrative canon.
- Preserve Phase 01-J schema 9/rules 12 and keep changes in `simulation/`
  on a separate, unmerged branch.

### Phase 01-K review decisions

- Order autonomously serviced eligible requests and promises by creation time; use the request identifier only as a deterministic tie-break.
- Normalize overlength automatically generated obligation IDs into stable SHA-256-derived identifiers instead of freezing an otherwise valid world.
- Keep schema 9/rules 12 because no event acceptance contract changed; verify with 313 passing tests in four local groups.
- Defer expiry or remote withdrawal of abandoned requests to a future phase that defines real communication/delivery semantics.
