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

**Schema 10 / Rules 13** — this phase changes WorldState and the command replay capability ledger. Old experimental DBs require deliberate migration/recreation; no automatic migration occurs.
