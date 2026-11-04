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

## Phase 01-C: isolated NPC intention planner

`carlos_sim.npc` provides per-NPC needs, goals, received beliefs and deterministic, explainable intentions. NPC decisions are recorded as events and remain stable over snapshot/replay. They do **not** execute actions. An active local `TimeEngine` session is required for `NPCService.decide`.

Try the five-person test fixture with:

```sh
PYTHONPATH=src python scenarios/test_village/demo.py
```

The example values, goals and scoring weights are **test rules only**, not facts of Carlos's world. Database format is now schema v3/rules v4 and experimental older databases require explicit migration/recreation. See `docs/phase_01c_report.md`.

### Phase 01-C review corrections

NPC state writes require an open play session even when called through the lower-level event store. Decision events must obey a minimum 60-second simulation cooldown. Belief updates now require a recorded `NPCInformationDelivered` followed by matching `NPCBeliefReceived` acknowledgement; the delivery records its sender, location, time and channel. Delivery IDs cannot be reused. The system validates provenance claimed inside a trusted simulation call, not the factual truth of a rumor or external identity. Tests: 84 passed locally. The world uses schema v4 and rules v5; older prototype DBs require explicit migration/recreation.

## Phase 01-D: action execution (test world only)

`NPCActionService.start` starts a previously recorded NPC intention **at the current simulation tick**. It atomically records an `NPCActionStarted` event plus a durable, non-interrupting completion signal. `TimeEngine.advance` moves the shared world clock and applies deterministic action effects when the signal fires. Multiple NPC actions can overlap and finish in timestamp/order sequence without automatically interrupting the player's action. Other scheduled signals may still interrupt.

| Test action | Duration (sim seconds) | Bounded deterministic effect |
|---|---:|---|
| rest | 120 | fatigue -20, hunger +5 |
| work | 180 | fatigue +15, hunger +10, labor_units +1 |
| investigate | 90 | fatigue +10, hunger +5, investigation_attempts +1 (no discoveries) |
| wait | 60 | hunger +5 |

Needs clamp to 0–100; `labor_units` and `investigation_attempts` are **test counters, not currency or items**. Both must be explicitly initialized as known 0 before a work/investigate action starts; missing/unknown values are never treated as zero. Completion effects are recorded in the immutable action history and derived from the scheduled `ScheduledEventFired` event, so replay reproduces exactly the same result. A running action's completion signal cannot be cancelled directly.

Run from the `simulation` directory:

```bash
python -m pytest -q
PYTHONPATH=src python scenarios/test_village/demo_actions.py
```

This remains a **trusted local** prototype without API authentication. It does not automatically decide another action after completion, generate NPC discoveries, simulate food production or payments, or modify Carlos's real story. Logical time and action effects cannot advance while the play session is closed. World schema/rules versions: **5 / 6**. Older experimental SQLite databases require explicit migration/recreation.

## Phase 01-E — Autonomous NPC lifecycle (opt-in)

`LivingWorldEngine` coordinates the full **decision → action start → scheduled completion → re-evaluation** cycle during an explicit player-time command. It does not use real elapsed time, a background worker, or internet connectivity. A player-interrupting signal stops the cycle at that logical instant; remaining seconds are returned. Concurrent NPC actions complete independently and may automatically restart after their need-based decision. The whole requested step is committed as **one atomic event batch**; if a rule fails or a configurable event bound is reached, nothing is written.

```python
from carlos_sim import SQLiteEventStore, TimeEngine, LivingWorldEngine

# Using an already created and configured *test* world:
with SQLiteEventStore('test_world.sqlite') as store:
    clock = TimeEngine(store)
    clock.open_session('village-test')
    result = LivingWorldEngine(store, clock, max_events_per_advance=1000).advance(
        'village-test', seconds=300, command_id='player-moves-1',
        expected_revision=store.load('village-test').revision)
    clock.close_session('village-test')
```

The existing `TimeEngine.advance` remains manual and **does not** automatically make NPC decisions; applications must opt in to `LivingWorldEngine`. The five-person test demo runs using `PYTHONPATH=src python scenarios/test_village/demo_living_world.py`. All actions and policy weights remain experimental; no Harthn or Carlos story data is imported. The coordinator uses the existing schema 5/rules 6 event formats; it introduces no DB schema migration. No authenticated/public API is included. Explicit command IDs must be unique; duplicate high-level commands raise `DuplicateCommand` rather than replaying a historical result. A too-large advancement request fails atomically at the event cap; callers can explicitly advance in smaller steps.

### Phase 01-E reviewed behavior

An NPC decision recorded by `NPCService.decide` at the current tick is now consumed by `LivingWorldEngine.advance` immediately if the NPC is idle. The original decision is not recorded again. This fixes the manual-to-autonomous handoff while preserving cooldowns, transaction boundaries and the pause semantics. Post-review tests: **134 passed locally**. See `docs/phase_01e_report.md`.

## Phase 01-F — routes, travel and local perception

NPCs may travel only along explicitly bootstrapped **bidirectional routes** between two named locations. Each route has a positive duration in simulated seconds. `NPCMovementService.start(...)` creates a durable, non-interrupting arrival appointment; the entity remains at its origin until that appointment fires. Routes are not automatically discovered and multi-hop navigation requires separate explicit travel commands. Player-controlled entities (including Carlos) are excluded.

`NPCMovementService.observe(...)` explicitly records a **timestamped local snapshot** of co-located entity IDs. Arrival automatically records the same type of observation at the destination. `perceive_local(...)` reads only a previously recorded observation for the NPC's current location; it never queries unseen rooms, remote NPCs, or world secrets. Past observations may become stale and are **not a live truth feed**. These are geometric test-site snapshots, not visibility/line-of-sight, hearing, stealth or a fully implemented rumor system.

Traveling NPCs cannot start a second journey, run a work/rest/investigate action, or record an on-site observation while in transit. `LivingWorldEngine` skips routine autonomous planning while an NPC is traveling; after a travel completes it may plan local actions again. Player interrupt signals can pause a journey in the middle, and offline/restart time is frozen.

Try from the `simulation/` folder:

```sh
python -m pytest -q
PYTHONPATH=src python scenarios/test_village/demo_movement.py
```

The demo uses synthetic Square / Bridge / Courtyard places, not Harthn or Carlos's real world. All travel and observation operations are trusted-local prototype APIs; **not authenticated HTTP operations**. World schema v6/rules v7: previous test databases require deliberate migration or recreation. No `main` merge or story-file modifications.

### Phase 01-F review corrections

While an NPC is traveling, its stored location remains the departure endpoint for deterministic persistence, **but it is absent for local observation and local messaging**. Both the sender and recipient of a local information delivery must not be in transit. New NPC activity decisions are also blocked during travel and become eligible after arrival. Seven regression tests added; **160 passed locally** after review. See `docs/phase_01f_report.md`.

## Phase 01-G — NPC-local navigation (experimental)

Navigation profiles remember each NPC's **known routes**, **visited places**, and an optional learned target. Surveying reveals roads incident to the current location only. A deterministic Dijkstra planner considers only those learned roads. With `LivingWorldEngine(store, clock, navigation_enabled=True)`, explorers with sufficient stamina and exploration interest independently select unvisited, reachable known road endpoints and travel while explicitly requested player time progresses. Other NPCs continue their regular activities. Previously recorded manual intentions take priority over exploration. Offline time remains frozen.

`NPCNavigationService.survey(...)` performs a local survey; `NPCNavigationService.target(...)` selects a previously learned reachable destination. No automatic player-character travel or network authentication exists. From `simulation/` run `PYTHONPATH=src python scenarios/test_village/demo_navigation.py`. Test policy values are not Carlos story facts. World schema/rules: **7/8**; earlier experimental databases require deliberate migration/recreation. Details: `docs/phase_01g_report.md`.

### Phase 01-G post-review check

Once an NPC has a navigation profile, **all** NPC travel starts (including direct `NPCMovementService` calls and trusted event batches) require the road to be present in that NPC’s learned-route list. Legacy 01-F worlds without navigation profiles retain explicit-route movement behavior. Post-review local tests: **188 passed**.

## Phase 01-H — Asymmetric NPC relationships

`NPCSocialService.interact` atomically records a local speech act and its recipient's interpretation. Only NPC recipients are automatically processed; the player character may be a sender but cannot be impersonated as an autonomously reacting NPC. Both parties must be co-located and neither may be traveling. Trust is asymmetric, bounded −100…100, and per-NPC. Each message and outcome is event-sourced for replay. `greeting`, `offer_help`, `request_help`, and `threat` are fixed **prototype categories**; the words of a message do not independently prove the claimed act, and an offer is not actual aid. No unsolicited NPC dialogue or social planning yet.

Run `PYTHONPATH=src python scenarios/test_village/demo_social.py` from `simulation/`; read `docs/phase_01h_report.md`. Schema/rules versions are 8/9. Earlier experimental databases require migration or re-creation; no Carlos story state imported. Local capability flags are not network authorization.

### Phase 01-H post-review corrections

Delayed local speech receipts must be confirmed at the **original message location**, not merely wherever both participants happen to reunite. Repeating the same speech-act kind by the same sender to the same recipient in one simulated timestamp is rejected, preventing instant trust farming without time progression. This does **not** model full social effort or truthful help. The verified local suite has **216 passing tests**. Schema remains **8**, while rule version is now **10**; rules-v9 prototype worlds need explicit migration/recreation. See `docs/phase_01h_report.md`.

## Phase 01-I — Autonomous NPC social initiative (opt-in)

`LivingWorldEngine(store, clock, social_enabled=True)` now gives idle NPCs a **bounded local social initiative** during the player's explicitly requested simulated-time advance. The pure `choose_social_intent` policy uses only the speaker's needs, directed trust and recorded pairwise encounters; it excludes busy/traveling NPCs, distant actors and the player character. Manual action intentions take precedence. Social pairs of `SocialMessageSent` and `SocialMessageReceived` are appended atomically and reported through `LivingAdvanceResult.social_message_ids`.

Each sender waits at least **180 simulated seconds** between automatic initiations and **900 simulated seconds** before repeating the same type of exchange with the same person. Choosing another conversation partner is still possible after the per-speaker cooldown. The original `NPCSocialService` stays available for authorized manual interactions. The social mode defaults to **off**, preserving earlier behavior. No messages or actions advance while the play session is closed.

From `simulation/` run `python -m pytest -q` or `PYTHONPATH=src python scenarios/test_village/demo_social_autonomy.py`. The demonstration involves fictional test characters and fixed speech templates, not the actual Carlos narrative. **Speech does not execute help, transfer resources, settle debts or generate truthful knowledge.** See `docs/phase_01i_report.md`. Schema **8**, rules **10** unchanged; no database migration.

## Phase 01-J — Promises and resource-backed help (opt-in API)

`NPCAssistanceService` records actual NPC-to-NPC assistance as a **request → promise/refusal → delivery/cancellation** workflow. Only a successfully fulfilled promise transfers initialized **food** or **water**. One transfer reduces the provider's stock and adds the same quantity to the recipient's stock; the ledger records quantities before/after and adjusts only the recipient's directed trust (+5). A spoken `offer_help` does **not** automatically donate goods.

The two NPCs must be present and idle; a request and reply occur face-to-face, with the reply at the original request site. Fulfillment requires co-location and available stock, but may occur later at another place. World time never advances when a session is closed. Duplicate transfers, insufficient stock, uninitialized inventories and unauthorized events are rejected atomically. Carlos remains player-controlled and is excluded from automatic assistance transactions.

Run `PYTHONPATH=src python scenarios/test_village/demo_assistance.py` from `simulation/` for an isolated demonstration, and see `docs/phase_01j_report.md`. **Schema 9 / Rules 12** require an explicit migration or new experimental test database. This is a trusted **local prototype API**, not a public authenticated service or automatic autonomous social planner.

### Phase 01-J reviewed behavior

The review closed two integrity holes: direct gameplay food/water **consumption requires an active play session** (only trusted bootstrap initialization is exempt), and cancelling an assistance request/promise is a **local communication event** requiring both NPCs to be present, idle, and in the same location. Remote silent withdrawal is rejected; cancellation remains possible after the characters reunite elsewhere. This is an explicitly local workflow, not a remote correspondence channel.

**282 local tests passed in three batches, including six new review regressions.** Schema **9**, rules **12**; existing rules-11 test worlds need explicit migration or recreation.

## Phase 01-K — Autonomous resource-backed assistance (opt-in)

`LivingWorldEngine(store, clock, assistance_enabled=True)` lets idle NPCs
**request, accept/decline, and later deliver food** during explicitly requested
player time. A hungry NPC checks **its own hunger and food** and chooses a local,
present NPC using **its own directed trust**. It never selects a provider based
on the provider's hidden food quantity or private hunger. The provider alone
checks **its own** food, hunger, trust in the requester, and previously promised
quantities before accepting or declining. Unfulfilled promises may be cancelled
in person if supplies are lost. Delivery is a separate, later event, not the
same event as speech or acceptance.

The policy uses the existing Phase 01-J validated obligation events; inventory
transfer conserves actual goods and never occurs remotely, while traveling, or
outside a play session. Default mode remains **off** for compatibility. Automatic
food requests require hunger >= 75 and food <= 2, and the requester waits 900
simulated seconds before another food request after any request. At most one
autonomous assistance transition per NPC per tick is allowed; a promise cannot
be fulfilled before a later simulated tick. Unknown/uninitialized inventory is
never silently treated as zero. Water is deliverable under existing manual
obligations but **no autonomous water requests**, because there is no thirst
need mechanic yet.

`LivingAdvanceResult.assistance_transitions` records `(obligation_id, status)`
for each autonomous transition. From `simulation/`, run
`PYTHONPATH=src python scenarios/test_village/demo_assistance_autonomy.py`.
All demonstrations use separate fictional fixtures, never real Carlos story data.
See `docs/phase_01k_report.md`. **Schema v9 / Rules v12 unchanged:** no new
events or migrations, and no autonomous work occurs in background.

### Phase 01-K post-review safeguards

Reviews now confirm that **earlier obligations take priority** over later ones in the autonomous response and delivery queues, regardless of the alphabetical order of request IDs (ties break by ID). NPCs with very long valid identifiers can still request help: the planner uses a deterministic hash-derived obligation ID when the human-readable form exceeds the event limit. The updated locally tested suite has **313 passing tests**, including three new regressions. The original Phase 01-J ledger and manual API remain unchanged; schema **9** and rules **12** remain compatible. See `docs/phase_01k_report.md` for open limitations, notably unexpired requests while parties remain separated.

## Phase 01-L — Owned food consumption and hunger relief (experimental)

`NPCConsumptionService.eat(world_id, npc_id, quantity, command_id=..., expected_revision=...)` records a strictly authorized `NPCFoodConsumed` event. That event decreases **already-owned, explicitly initialized food** and lowers the **same NPC's hunger** by 25 per food unit (clamped to zero), atomically. A meal is limited to 1–3 units and at most once per NPC per simulated tick. The event ledger retains where, when, food before/after, and hunger before/after. A generic `ResourceChanged` consumption event continues to represent other resource expenditure; it does not count as eating or provide satiety.

`LivingWorldEngine(store, clock, consumption_enabled=True)` enables a deterministic self-need policy: an available NPC with hunger ≥50 and owned food consumes **one unit** before starting another routine activity, without knowing other NPC inventories. Disabled by default to preserve previous stages. No food eating while traveling or working, no off-session eating, no player-controlled Carlos actions. The eating event is instantaneous in this prototype; time spent eating, nutrition and food types need separate rules.

Run `PYTHONPATH=src python scenarios/test_village/demo_consumption.py` from `simulation/`. Food acquired by `Phase 01-K` gift assistance is not eaten until `NPCFoodConsumed` actually occurs. Do not interpret fleeing after a **gift** as unpaid debt: documented loans and their repayment terms require a future distinct contract system. See `docs/phase_01l_report.md`.

**Schema 10 / Rules 14** — this phase changes WorldState and the command replay capability ledger. Old experimental DBs require deliberate migration/recreation; no automatic migration occurs.

### Phase 01-L review — closing the foodless hunger bypass

The generic `NPCNeedChanged` event may **increase hunger** as before, but decreasing hunger without consuming food now requires the separate, trusted `npc_authorized=True` adjustment capability while the play session is active. This preserves a documented administrative/scripted need override without treating it as a meal; actual eating must use `NPCFoodConsumed`, which atomically debits real food and records hunger relief. The normal low-level event path can no longer provide free satiation. Six new review regressions pass; the complete local suite has **351 passing tests in five separate groups**. Schema remains **10**, while **Rules 14** replace rules 13. Older experimental DBs require migration or recreation.

## Phase 01-M — Opt-in survival needs over play time

`LivingWorldEngine(store, clock, survival_enabled=True)` advances background
hunger at **1 point / 300 simulated seconds** and fatigue at **1 point / 600
simulated seconds outside an active rest action**. Fractional elapsed seconds
are saved in `WorldState.survival_progress` so the same total simulation time
produces the same needs across single or split steps. At hunger **90+**, the
survival-mode NPC policy favors energy conservation over routine work or
investigation, starting at the first decision. Other completed action costs
remain **separate activity surcharges** rather than another baseline elapsed
time calculation. Neither food nor HP is conjured by this policy.

The mode is **disabled by default**. A manually advanced `TimeEngine`
without this option still advances only the clock; no offline or wall-clock
time passes. `survival_authorized` is a trusted **internal capability**, not
authentication; it is recorded with commands for event replay. There is no
retroactive charge for periods deliberately advanced while the feature was
disabled.

Run `PYTHONPATH=src python scenarios/test_village/demo_survival.py` to see
the precise 300/600-second boundaries and
`PYTHONPATH=src python scenarios/test_village/bench_survival.py` for a
**pure reducer only** measurement on 10, 100, and 1000 NPCs. The latter is
*not* end-to-end engine throughput. **373 tests passed locally in five
completed groups**, including 22 new phase tests. See
`docs/phase_01m_report.md` for measurements, constraints and caveats.
**Schema 11 / Rules 15** require explicit migration or fresh experimental
databases. Main and canonical Carlos narrative remain untouched.

### Phase 01-M independent review

`NPCService(store, clock, survival_enabled=True).decide(...)` uses the same
critical-hunger policy as the survival-enabled living-world coordinator for a
**pre-recorded intention**, without advancing simulated time. The default remains
`False` and an existing recorded manual intention is not silently overridden.
The opt-in capability is stored with the command for deterministic replay.
Six additional regressions passed; total **379/379 local tests**.

`PYTHONPATH=src python scenarios/test_village/bench_living_world.py` performs
a separate **full engine** sample including NPC decision/action events and SQLite
writes. In the local review environment, one 60-second advance took ~0.14 s for
10 NPCs, ~2.53 s for 50, and ~9.42 s for 100. These are not production
throughput figures. The full event projection/replay pipeline is the current
scaling concern; the isolated 1000-NPC metabolism benchmark is **not** evidence
that 1000 complete NPCs run in 0.05 s. Larger-scale engine profiling and
optimization remain separate follow-up work.

## Phase 01-N — Event projection performance (initial implementation)

The event-sourced world still validates **every event** and retains full
snapshot/replay checks, authorization, atomic rollback, and existing decisions.
The optimized `WorldState.from_dict` normalizes JSON **once** and freezes the
checked data directly. `WorldState.to_dict` returns an independent deep copy
without re-serializing an already-normalized projection. Direct constructors
still use strict JSON checking, and no state or event schema was changed.

The complete local regression suite passed **388/388**, including nine new
defensive-copy, invalid-input, snapshot and atomicity regressions. Running the
same 60-second full-engine benchmark for **100 NPCs** took **10.4821 s**
on reviewed 01-M versus **4.8872 s** here (one sample per version, about
2.14× faster). That is still too slow for a large living world.

Reproduce via `PYTHONPATH=src python scenarios/test_village/bench_living_world.py
--counts 10 25 50 100`. To check the **full event-log and state digest** across
branches, use the identical `scenarios/test_village/bench_event_parity.py`
script with the respective branch's `PYTHONPATH=src`. Schema **11**, rules
**15**, and existing experimental DB formats remain unchanged. See
`docs/phase_01n_report.md` for data and limitations. Await independent review
before closing 01-N.

## Phase 01-N final integrated verification (replaces interim figures)

The combined optimized implementation adds fast-path JSON leaf/container copying
and 15 further integrity tests to the first 01-N candidate. **410/410 tests
passed locally**; event-log and final-state digests matched reviewed 01-M
byte-for-byte for 10 and 25 NPC fixtures. A separate same-host 100-NPC
full-engine run took **9.5122 s (01-M) versus 3.4529 s (01-N)**, about
**2.75× faster**, while still generating 301 events. This is an isolated sample,
not proof that 1000 active NPCs are production-ready. See
`docs/phase_01n_validation.md` for the final measurements; any 388-test count
in earlier 01-N notes describes the intermediate revision only.

Schema 11 / Rules 15 remain compatible. No `main` merge. Independent review completed with GitHub Actions (410/410 passing on Python 3.10 and 3.13, plus matching 01-M/01-N event and state digests). See `docs/phase_01n_independent_review.md`.

## Phase 01-O — Bounded SQLite queries during event replay

`SQLiteEventStore.load` now reads each event together with its command's
replay capabilities using one ordered `LEFT JOIN` instead of issuing another
SQLite query for every event. This preserves per-event reducers, payload hash
checks, missing-command detection, immutable projections, snapshots, atomic
writes and the explicit simulation-time model. **Schema 11 / Rules 15** are
unchanged, and no story files or `main` branch were changed.

**413/413 tests pass** on Python 3.10 and 3.13 in GitHub Actions, including
three new replay/integrity regressions. The complete event-log and final-state
digests still match the reviewed Phase 01-N fixture at 10 and 25 NPCs.

The identical replay benchmark at 100 stored events recorded **102 SQL SELECTs**
on 01-N versus **2 SELECTs** on 01-O. This was an isolated, single-run CI
measurement (three timed repetitions per variant); full-world event projection
and double simulation remain more substantial bottlenecks. See
`docs/phase_01o_report.md` for evidence and caveats.

## Phase 01-P — Faster full-world event projection (reviewed)

The internal domain reducer still validates **every event and every world
invariant** before producing a frozen state. It now avoids an extra full-world
JSON encode/decode after verifying a reducer-owned JSON-native projection.
Public snapshots and direct constructor calls continue to enforce portable
JSON normalization. Canonical sorted nested mapping order remains identical
to earlier phases. No rules, event schema, or database migration change:
**Schema 11 / Rules 15**.

Final independent GitHub CI passed **419/419 tests on both Python 3.10
and 3.13**, with matching full event-ledger and world-state digests
against Phase 01-O at 10, 25 and 50 NPCs. In a single full-engine 60-second
advance with **150 NPCs and 451 events**, measured execution fell from
11.2778 s to 6.5542 s (Python 3.13) and from 12.1070 s to 7.7901 s
(Python 3.10), excluding fixture setup. These are environment-specific
samples, not production capacity guarantees; 1,000 active NPCs are not
yet benchmarked. See `docs/phase_01p_report.md`.
