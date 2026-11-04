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

## Phase 01-L — Eating versus owning food; loans versus gifts

- A physical food transfer only changes inventory and a recipient's directed trust. Ownership is not consumption or satiation.
- An NPC eating owned food must use a separate, trusted, locally replayable event that atomically reduces food and hunger, with a before/after ledger. Default autonomous eating is opt-in.
- A character who takes a gift and leaves does **not** become a debtor merely because they traveled away. An exploitative borrower may deliberately flee, however, and the future **loan/debt contract** domain must preserve that obligation after separation and distinguish due date, consent, repayment/partial repayment, default, attempted contact, and independently sourced witness evidence. Do not erase such obligations with an automatic expiry, and do not infer dishonest intent merely from absence; history should support competing interpretations and enforce contract terms separately.
- Future lenders should be able to refuse based on their own trust, resources and evidence of prior unpaid debts; future borrowers may choose self-interested or deceptive decisions. No omniscient accusation or protection from consequences.
- No canonical Carlos narrative change and no `main` merge during Phase 01-L.

### Phase 01-L review decisions

- Close the legacy free-satiation route: an ordinary low-level `NPCNeedChanged(hunger ↓)` cannot bypass food conservation and the meal ledger.
- Permit explicit trusted hunger decreases only with the established `npc_authorized` capability and an active play session; these are non-food scenario/admin adjustments and are not claimed as meals.
- Keep natural hunger increases and explicit test fixtures working; six new regression tests cover refusal, rollback, replay and authorized behavior.
- Bump rule version from 13 to **14** (schema remains 10), because event acceptance changed. **351 tests passed in five separate local groups.**

## Phase 01-M — Survival timing decisions

- Keep survival progression opt-in and tied exclusively to explicit player
  time advances. No real-world clock, background need drift or off-session
  catch-up is permitted.
- Use integer remainder accounting (300s hunger, 600s fatigue) to ensure
  deterministic split-step invariants. Charge only actual elapsed seconds;
  interruptions and action completion boundaries remain causal.
- Treat baseline metabolism and the pre-existing action completion deltas as
  *separate causes*. Do not derive activity deltas again from elapsed time;
  revisit those provisional values in a balancing phase.
- Suspend baseline fatigue while the NPC is truly resting, but continue
  hunger progression. Critical hunger (>=90) conserves energy by deprioritizing
  ordinary work/investigation, not by inventing aid or bypassing food.
- Keep all survival logic free of knowledge about other characters' hidden
  resources. Only the NPC's own needs affect its survival decision.
- Preserve baseline behavior when the option is disabled, even after a
  previous enabled interval. Replaying a command uses its original
  `survival_authorized` flag.
- Distinguish gifts from repayment-bearing loans and carry forward the
  future need for evidence-based lending, default and potential deliberate
  evasion; do **not** infer a debt from food aid or erase an actual loan
  merely because the borrower disappears.
- New persisted progress and replay capability require schema 11/rules 15,
  explicit migration/recreation, independent review, and no `main` merge.

### Phase 01-M review conclusions

- Explicit NPC planner service must be able to opt into the same critical-hunger
  policy as the autonomous coordinator; it must not silently override an earlier
  intention or advance world time.
- Persist the exact selected policy capability for event replay without changing
  the schema or rules versions.
- Preserve the **379-test** passing regression baseline and document the six
  additional tests.
- Record reproducible **full living-world** timing separately from isolated
  survival reducer timing. On the local review host, 100 NPCs required roughly
  **9.4 seconds** for a 60-second world command with 301 events. This is a
  scaling warning, not an end-user gameplay performance guarantee.
- Defer structural event-store optimization to a separate controlled phase with
  replay and deterministic equivalence tests; do not replace the stable ledger
  during Phase 01-M review.

## Phase 01-N — Performance without altered world behavior

- Optimize redundant state serialization/copying rather than remove NPC
  decisions, simulate fewer interactions, or skip persisted events.
- Preserve one complete `WorldState.from_dict` validation and JSON
  normalization before the private fast path. Externally constructed states
  retain their full validation behavior; `to_dict` remains a detached copy.
- Keep event authorization, ordered per-event reducer validation, replay
  integrity and SQLite atomicity unchanged.
- Accept evidence from **388 local tests**, and identical complete event
  ledger/final-state digests against 01-M in two independent fixture sizes.
- Use like-for-like full-engine timings: approximately **2.14×** faster
  at 100 NPCs (10.4821 s → 4.8872 s). This remains inadequate for
  1000 active NPCs; address incremental projection separately.
- Maintain schema **11**, rules **15**, no changes to `main` or Carlos
  story files, and require independent review before 01-N closure.

### Phase 01-N final integration decisions

- Retain validated immutable projections, authorization, atomic rollback and
  original event order/decision counts; never trade correctness for speed.
- Fast-path trusted built-in JSON nodes, but retain JSON validation for
  external/constructor input and a generic `Mapping` fallback.
- Preserve all **410 passing tests** and exact event/state hash parity for
  10/25 NPC worlds. Earlier 388-test figures refer to an intermediate build.
- Measured at 100 NPCs: **9.5122 s → 3.4529 s** for the same 60-second
  full-engine workload, 301 events; more optimization needed for 1000+.
- Schema 11 / Rules 15 unchanged; no automatic migrations or `main` merge.
  Independent phase review remains mandatory.

## Phase 01-O — Bounded replay SQL queries (reviewed)

- Remove the event-store N+1 SELECT pattern without changing event ordering,
  provenance, hash verification, trust capabilities, transactional append
  semantics, optimistic revision checks, or immutable state construction.
- Use `LEFT JOIN` rather than `INNER JOIN` so orphaned/corrupt command
  rows remain visible and fail closed instead of silently disappearing.
- Guard the query count, snapshot/full replay consistency and missing-command
  corruption explicitly with new tests. Avoid hardware-specific speed gates.
- Independent GitHub Actions on Python 3.10/3.13: **413/413 tests passed**;
  event/state parity with reviewed 01-N at 10 and 25 NPCs also passed.
- Same-workload 100-event full replay: **102 to 2 SQL SELECTs**; observed time
  gains are modest and are not a promise about large 1,000-NPC populations.
- Remain at Schema 11 / Rules 15. Do not merge to `main` or alter Carlos
  narrative. Future scaling work requires separate profiling and review.

## Phase 01-P — Reviewed performance invariants

- Eliminate only the duplicate JSON normalization of reducer-owned
  projected world data; **never skip** per-event or all-domain validation.
- Public `WorldState.from_dict` stays strict. Direct constructors, invalid
  input rejection, detached returned dictionaries and immutable nested state
  must behave as before.
- Keep nested mapping iteration canonical and sorted, not merely hashes
  equivalent. An independent review caught and resolved this ordering issue.
- Preserve atomic SQLite commits, authorization/capability provenance,
  snapshot/full-replay parity, event counts and world-time behavior.
- Independent CI: **419 tests** on Python 3.10 and 3.13, with exact
  event/state parity against Phase 01-O for 10/25/50 NPCs.
- Full-engine 60s step at 150 NPCs: **451 events**, measured **11.2778→6.5542s**
  (Python 3.13) and **12.1070→7.7901s** (Python 3.10). No setup time in
  timings; these are single samples, not capacity promises.
- Schema 11 / Rules 15; `main` and Carlos's narrative remain unchanged.
  Future structural reductions in double batch projection require
  a separate design/review.

## Phase 01-Q — Scarcity and explicit physical effort

- Return development focus from throughput optimization to NPC-world
  causal mechanics; small-world tests remain the standard for behavior.
- A location's natural deposit is **finite and explicitly initialized**.
  Existing `investigate` action duration is the required physical
  effort. Recovery is an explicit command immediately upon completion.
- One recovery per completed action, at the same site and simulation
  tick, credited only to the actor. The ledger records source/recipient
  before and after balances; no missing stock becomes zero.
- Do not auto-spawn, regrow or synthesize food. Actual eating remains
  separate. Agricultural growth and autonomous collection are deferred.
- Reuse the persisted trusted `action_authorized` provenance, checked
  again at the store boundary with the open play session. No new
  untrusted endpoint or implied permissions were created.
- A new immutable `gatherings` collection needs Schema 12 / Rules 16
  and explicit migration/recreation of older experimental saves.
- Regression test 10/25 NPC scenarios rather than running an
  unnecessary 150-NPC benchmark for this small behavioral feature.

## Phase 01-R — Local, hunger-limited automatic pickup

- Use **seven** synthetic characters for causal integration
  testing and a small 7-NPC parity fixture, not 150 characters
  by default. Keep the large-scale benchmarks for future
  architecture/performance changes.
- Collection mode defaults to off. The local site deposit is
  modeled as physically visible after an investigation has
  completed. The planner must never read an unknown distant
  site, peer's hidden inventory or any background wall-clock.
- Hunger >=65 and owned food **exactly zero** are the
  conditions for opportunistic pickup. Unknown owned food is
  not zero; natural stock must be known and positive.
- One completed local investigation permits at most one
  same-tick unit recovery. Use the previously authorized
  `NPCFoodGathered` event, preserving atomic resource
  conservation and stable due-event order.
- Do not tamper with `NPCDecisionRecorded` to fake a new
  food-seeking intention. Hunger-driven initiation, location
  knowledge and travel toward food require separate audited
  event provenance.
- Schema 12 / Rules 16 stay unchanged; `main` and all
  real Carlos story files remain unchanged.
- Final seven-NPC demo reports **52 events, 2 recoveries**,
  with **445 successful tests** under Python 3.10 and 3.13.

## Roadmap and delivery governance — 2026-11-04 (planning-only)

- Adopt [ROADMAP.md](ROADMAP.md) as the maintained planning baseline **from Phase 01-R onward**, and [DEVELOPMENT_PROTOCOL.md](DEVELOPMENT_PROTOCOL.md) for phase acceptance and independent review.
- Prioritize causality, limited character knowledge, resource conservation and early playable interaction over routine 150-NPC benchmarking. Behavior phase default: 5–10 NPCs; integrated cases 10–25; scale testing when justified.
- Future entries 01-S through 05-E are **proposed milestones**, not implemented or promised as fixed API/schema contracts. Recheck ordering at each milestone and record changes.
- Require explicit schema/rules compatibility review for each phase, preserve the event log, offline logical time, atomicity, and separation of player input from narration.
- The roadmap/protocol change is **documentation-only**; no engine code, schema version, Rules version, or Carlos story file is modified.

## 2026-11-04 — Living roadmap, save compatibility, and P0 gate (documentation only)

- The user explicitly approved **adapting the roadmap as needed**. Plan changes require a reason, dependency/risk impact analysis and a durable entry in ROADMAP_CHANGELOG.md. A plan change is not evidence of executed features.
- Adopt SAVE_COMPATIBILITY_POLICY.md: each phase assesses whether it changes event semantics or Schema/Rules; reject incompatible worlds fail-closed instead of guessing missing fields.
- Require **P0** (verified coherent backup, restored replay, compatibility checks and rollback rehearsal) before the first long-lived game world, including if requested earlier than 01-Z. Scope is policy now, not implementation.
- Existing SQLite append atomicity, snapshots and hashes are not an off-file backup or general migration solution. Trusted capability flags are not network authentication.
- Do not alter main, the original Carlos story, or saved user world data without explicit authorization. This governance commit changes documentation only.
