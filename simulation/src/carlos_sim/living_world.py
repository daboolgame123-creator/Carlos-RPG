"""Bounded, atomic autonomous NPC lifecycle during explicitly requested play time.

This coordinator is opt-in: the ordinary TimeEngine remains a manual clock.
No wall-clock tasks, hidden knowledge, arbitrary scripts or real Carlos story data.
"""
from __future__ import annotations

from dataclasses import dataclass

from .actions import DURATIONS
from .domain import DomainEvent, WorldState, apply_event
from .npc import MIN_DECISION_COOLDOWN, choose_action
from .store import DuplicateCommand, InvalidEvent, SQLiteEventStore
from .time_engine import AdvanceLimitExceeded, TimeEngine
from .navigation import next_route, needs_survey
from .social_autonomy import MIN_SOCIAL_COOLDOWN, choose_social_intent
from .assistance_autonomy import choose_assistance_intent
from .consumption import choose_food_consumption, _meal_id
from .gathering import choose_gathering_intent
from .knowledge import make_observation_events, choose_food_sharing_round, known_food_sites
from .food_navigation import choose_food_route


@dataclass(frozen=True)
class LivingAdvanceResult:
    state: WorldState
    requested_seconds: int
    elapsed_seconds: int
    remaining_seconds: int
    started_action_ids: tuple[str, ...]
    completed_action_ids: tuple[str, ...]
    fired_ids: tuple[str, ...]
    interrupted: bool
    event_count: int
    social_message_ids: tuple[str, ...] = ()
    assistance_transitions: tuple[tuple[str, str], ...] = ()
    meals_consumed: tuple[str, ...] = ()
    gathered_action_ids: tuple[str, ...] = ()
    knowledge_shares: tuple[str, ...] = ()


class LivingWorldEngine:
    """Run NPC intentions/actions alongside an explicit in-world time command.

    One clock request is simulated in memory, then persisted as a single atomic
    event batch. An interruption commits *only* the portion through that signal.
    An event limit failure commits nothing, including any NPC decisions.
    """

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine, *,
                 max_events_per_advance: int = 1000,
                 decision_cooldown: int = MIN_DECISION_COOLDOWN,
                 navigation_enabled: bool = False, social_enabled: bool = False,
                 social_cooldown: int = MIN_SOCIAL_COOLDOWN,
                 assistance_enabled: bool = False, consumption_enabled: bool = False,
                 survival_enabled: bool = False, gathering_enabled: bool = False,
                 foraging_enabled: bool = False, knowledge_enabled: bool = False,
                 food_navigation_enabled: bool = False,
                 scarcity_enabled: bool = False):
        if clock.store is not store:
            raise ValueError('the clock and living-world coordinator must share a store')
        if type(max_events_per_advance) is not int or max_events_per_advance < 1:
            raise ValueError('max_events_per_advance must be a positive integer')
        if type(decision_cooldown) is not int or decision_cooldown < MIN_DECISION_COOLDOWN:
            raise ValueError('decision_cooldown must be at least 60 simulation seconds')
        self.store = store
        self.clock = clock
        self.max_events_per_advance = max_events_per_advance
        if type(navigation_enabled) is not bool:
            raise ValueError("navigation_enabled must be boolean")
        self.decision_cooldown = decision_cooldown
        self.navigation_enabled = navigation_enabled
        if type(social_enabled) is not bool:
            raise ValueError("social_enabled must be a boolean")
        if type(social_cooldown) is not int or social_cooldown < MIN_SOCIAL_COOLDOWN:
            raise ValueError("social_cooldown must be at least 180 simulated seconds")
        self.social_enabled = social_enabled
        self.social_cooldown = social_cooldown
        if type(assistance_enabled) is not bool:
            raise ValueError("assistance_enabled must be boolean")
        self.assistance_enabled = assistance_enabled
        if type(consumption_enabled) is not bool:
            raise ValueError("consumption_enabled must be boolean")
        self.consumption_enabled = consumption_enabled
        if type(survival_enabled) is not bool:
            raise ValueError("survival_enabled must be boolean")
        self.survival_enabled = survival_enabled
        if type(gathering_enabled) is not bool:
            raise ValueError("gathering_enabled must be boolean")
        self.gathering_enabled = gathering_enabled
        if type(foraging_enabled) is not bool:
            raise ValueError("foraging_enabled must be boolean")
        self.foraging_enabled = foraging_enabled
        if type(knowledge_enabled) is not bool:
            raise ValueError("knowledge_enabled must be boolean")
        self.knowledge_enabled = knowledge_enabled
        if type(food_navigation_enabled) is not bool:
            raise ValueError("food_navigation_enabled must be boolean")
        if food_navigation_enabled and not (
                self.navigation_enabled and self.knowledge_enabled
                and self.foraging_enabled):
            raise ValueError(
                "food_navigation_enabled requires navigation_enabled, "
                "knowledge_enabled and foraging_enabled"
            )
        self.food_navigation_enabled = food_navigation_enabled
        if type(scarcity_enabled) is not bool:
            raise ValueError("scarcity_enabled must be boolean")
        if scarcity_enabled and not (self.food_navigation_enabled
                                    and self.assistance_enabled):
            raise ValueError(
                "scarcity_enabled requires food_navigation_enabled and assistance_enabled"
            )
        self.scarcity_enabled = scarcity_enabled

    def advance(self, world_id: str, *, seconds: int, command_id: str,
                expected_revision: int) -> LivingAdvanceResult:
        self.clock._require_session(world_id)
        if type(seconds) is not int or seconds <= 0:
            raise ValueError('seconds must be a positive integer')
        if not isinstance(command_id, str) or not command_id:
            raise ValueError('command ID is required')
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('expected revision must be nonnegative')
        if self.store.db.execute('SELECT 1 FROM commands WHERE world_id=? AND command_id=?',
                                 (world_id, command_id)).fetchone():
            raise DuplicateCommand('living-world command already executed')
        original = self.store.load(world_id)
        if original.revision != expected_revision:
            from .store import RevisionConflict
            raise RevisionConflict(f'expected {expected_revision}, current {original.revision}')
        target = original.time + seconds
        current = original
        events: list[DomainEvent] = []
        started: list[str] = []
        completed: list[str] = []
        fired: list[str] = []
        interrupted = False
        social_messages: list[str] = []
        assistance_transitions: list[tuple[str, str]] = []
        meals_consumed: list[str] = []
        gathered_actions: list[str] = []
        knowledge_shares: list[str] = []

        def append(event: DomainEvent, *, action_capability: bool = False,
                   movement_capability: bool = False,
                   social_capability: bool = False,
                   assistance_capability: bool = False,
                   consumption_capability: bool = False,
                   survival_capability: bool = False) -> None:
            nonlocal current
            # Keep the entire high-level command fail-closed and bounded.
            if len(events) >= self.max_events_per_advance:
                raise AdvanceLimitExceeded('autonomous simulation event budget exhausted')
            try:
                current = apply_event(current, event, action_authorized=action_capability,
                                      movement_authorized=movement_capability,
                                      social_authorized=social_capability,
                                      assistance_authorized=assistance_capability,
                                      consumption_authorized=consumption_capability,
                                      survival_authorized=survival_capability)
            except (ValueError, TypeError) as exc:
                raise InvalidEvent(str(exc)) from exc
            events.append(event)

        while True:
            # Scheduled occurrences at the current tick always have priority
            # over newly planned NPC decisions. Stable ordering is persisted.
            due = sorted(((ident, item) for ident, item in current.scheduled.items()
                          if item['due'] == current.time),
                         key=lambda x: (x[1]['order'], x[0]))
            if due:
                ident, item = due[0]
                append(DomainEvent('ScheduledEventFired', None,
                                   'scheduled signal became due', current.time, {'id': ident}))
                fired.append(ident)
                if '__npc_action_id' in item['payload']:
                    finished_id = item['payload']['__npc_action_id']
                    completed.append(finished_id)
                    if self.gathering_enabled:
                        # The scheduled investigate completion is authoritative:
                        # its event has already projected effort and time cost.
                        # Each contender now observes ONLY the remaining food
                        # at its own site, in durable due-signal order.
                        intent = choose_gathering_intent(current, finished_id)
                        if intent is not None:
                            append(DomainEvent(
                                'NPCFoodGathered', intent.npc_id,
                                'autonomous local recovery after completed investigation',
                                current.time,
                                {'npc_id': intent.npc_id,
                                 'action_id': intent.action_id,
                                 'site_id': intent.site_id}),
                                action_capability=True)
                            gathered_actions.append(intent.action_id)
                    if self.knowledge_enabled:
                        action_info = current.actions.get(finished_id) if isinstance(finished_id, str) else None
                        if (action_info is not None and action_info["action"] == "forage"
                                and action_info["status"] == "completed"):
                            who = action_info["npc_id"]
                            site = current.entities[who]["location_id"]
                            for event in make_observation_events(current, who, site, current.time, 'forage'):
                                append(event)
                                if event.event_type == 'NPCInformationDelivered':
                                    knowledge_shares.append(event.data['delivery_id'])
                # A travel completion has a "__npc_travel_id" payload, never
                # "__npc_action_id". Handle it as a sibling of action completion
                # so arrival observations cannot be skipped.
                if '__npc_travel_id' in item['payload'] and self.knowledge_enabled:
                    travel_id = item['payload']['__npc_travel_id']
                    travel = current.travels.get(travel_id) if isinstance(travel_id, str) else None
                    if (travel is not None and travel['status'] == 'arrived'
                            and travel['arrived_at'] == current.time):
                        who = travel['npc_id']
                        site = current.entities[who]['location_id']
                        for event in make_observation_events(current, who, site, current.time, 'arrival'):
                            append(event)
                            if event.event_type == 'NPCInformationDelivered':
                                knowledge_shares.append(event.data['delivery_id'])
                if item['interrupt']:
                    interrupted = True
                    break
                continue

            busy = {a['npc_id'] for a in current.actions.values()
                    if a['status'] == 'running'}
            busy.update(t['npc_id'] for t in current.travels.values()
                        if t['status'] == 'traveling')
            if self.assistance_enabled:
                # The fixed passes are independent of lexical NPC ID ordering:
                # settle old promises, then respond, request, and respond to
                # requests created in this tick. A provider can only make one
                # choice per tick; physical delivery requires a later tick.
                acted: set[str] = set()
                for phase in ('settle', 'respond', 'request', 'respond'):
                    for actor_id in sorted(current.npcs):
                        if actor_id in acted:
                            continue
                        intent = choose_assistance_intent(
                            current, actor_id, phase,
                            scarcity_enabled=self.scarcity_enabled)
                        if intent is None:
                            continue
                        append(DomainEvent(intent.event_type, actor_id,
                            'autonomous assistance: ' + intent.reason, current.time,
                            {'id': intent.request_id, **intent.fields}),
                            assistance_capability=True)
                        acted.add(actor_id)
                        assistance_transitions.append((intent.request_id,
                                                       current.obligations[intent.request_id]['status']))
            if self.consumption_enabled:
                # An actual meal debits food and relieves that NPC's hunger in
                # one event. Do not mistake inventory ownership for eating.
                for npc_id in sorted(current.npcs):
                    quantity = choose_food_consumption(current, npc_id)
                    if quantity is None:
                        continue
                    meal_id = _meal_id(npc_id, current.time)
                    append(DomainEvent('NPCFoodConsumed', npc_id,
                                       'NPC ate owned food to relieve personal hunger',
                                       current.time,
                                       {'id': meal_id, 'npc_id': npc_id, 'quantity': quantity}),
                           consumption_capability=True)
                    meals_consumed.append(meal_id)
            if self.knowledge_enabled:
                # Bounded, deterministic food-knowledge sharing pass. Never
                # touches next_decision_at, never adds to busy, never emits a
                # decision; it is a pure sharing limit, not a decision delay.
                busy_now = {a['npc_id'] for a in current.actions.values()
                            if a['status'] == 'running'}
                busy_now.update(t['npc_id'] for t in current.travels.values()
                                if t['status'] == 'traveling')
                # One frozen per-round proposal, one recipient/site delivery.
                # No instantaneous re-sharing of newly acquired hearsay.
                for event in choose_food_sharing_round(current):
                    append(event)
                    if event.event_type == "NPCInformationDelivered":
                        knowledge_shares.append(event.data["delivery_id"])
            # Deterministic tie breaking between independently eligible NPCs.
            for npc_id in sorted(current.npcs):
                if npc_id in busy:
                    continue
                existing = current.npcs[npc_id]['last_decision']
                pending_action = existing is not None and existing['at'] == current.time
                # A social exchange is an instantaneous *speech act*, not an
                # executed favor. Both events share this one authorized command.
                if self.social_enabled and not pending_action:
                    intent = choose_social_intent(current, npc_id,
                                                  cooldown=self.social_cooldown)
                    if intent is not None:
                        message_id = f'auto-social:{npc_id}:{current.time}'
                        if message_id in current.social_messages:
                            raise InvalidEvent('autonomous social message ID collision')
                        append(DomainEvent('SocialMessageSent', npc_id,
                            f'autonomous social initiative: {intent.reason}', current.time,
                            {'id': message_id, 'recipient': intent.recipient_id,
                             'kind': intent.kind, 'text': intent.text}), social_capability=True)
                        append(DomainEvent('SocialMessageReceived', intent.recipient_id,
                            'autonomous local recipient acknowledges the speech act',
                            current.time, {'id': message_id}), social_capability=True)
                        social_messages.append(message_id)
                # New 01-S survival intent must be considered before starting
                # optional autonomous exploration/travel. Otherwise a hungry
                # NPC ignores visible food here whenever a road is available.
                # The same pure predicate is used later by choose_action and
                # event replay; it inspects this NPC plus this site only.
                local_forage_wins = False
                if self.foraging_enabled and not pending_action:
                    from .foraging import choose_local_foraging
                    local_site = current.entities[npc_id]['location_id']
                    local_forage_wins = choose_local_foraging(
                        npc_id, current.npcs[npc_id], local_site,
                        current.resources) is not None
                if self.navigation_enabled and not pending_action and not local_forage_wins:
                    if needs_survey(current, npc_id):
                        append(DomainEvent('NPCNavigationSurveyed', npc_id,
                            'NPC surveys locally observable roads', current.time,
                            {'npc_id': npc_id}), movement_capability=True)
                    food_intent = (
                        choose_food_route(current, npc_id,
                                          scarcity_enabled=self.scarcity_enabled)
                        if self.food_navigation_enabled else None
                    )
                    if (self.food_navigation_enabled
                            and current.time < current.npcs[npc_id]['next_decision_at']):
                        # U-3: both fallback exploration and hungry food travel
                        # respect the previous decision cooldown in opt-in mode.
                        continue
                    route_id = food_intent.route_id if food_intent is not None else next_route(current, npc_id)
                    if route_id is not None:
                        route = current.routes[route_id]
                        here = current.entities[npc_id]['location_id']
                        there = route['b'] if route['a'] == here else route['a']
                        travel_id = f'auto-nav:{npc_id}:{current.time}'
                        if travel_id in current.travels:
                            raise InvalidEvent('autonomous journey identifier collision')
                        due_at = current.time + route['seconds']
                        schedule_id = 'npc-travel:' + travel_id
                        travel_reason = 'autonomous movement over a learned road'
                        if food_intent is not None:
                            travel_reason = (
                                f'autonomous food journey; belief_site={food_intent.destination}; '
                                f'source={food_intent.source}; observed_at={food_intent.observed_at}; '
                                f'effective_confidence={food_intent.confidence}; '
                                f'known_cost_seconds={food_intent.total_seconds}'
                            )
                        append(DomainEvent('ScheduledEventCreated', None,
                            'scheduled autonomous travel arrival', current.time,
                            {'id': schedule_id, 'due': due_at,
                             'order': current.next_schedule_order, 'kind': 'signal',
                             'payload': {'__npc_travel_id': travel_id}, 'interrupt': False}),
                             movement_capability=True)
                        append(DomainEvent('NPCTravelStarted', npc_id,
                            travel_reason, current.time,
                            {'id': travel_id, 'npc_id': npc_id, 'route_id': route_id,
                             'origin': here, 'destination': there, 'due': due_at,
                             'schedule_id': schedule_id}), movement_capability=True)
                        busy.add(npc_id)
                        continue
                # A prior NPCService.decide call can leave a valid, unstarted
                # intention at this exact tick. Execute it rather than waiting
                # for its decision cooldown and silently leaving the NPC idle.
                profile = current.npcs[npc_id]
                pending = profile['last_decision']
                if pending is not None and pending['at'] == current.time:
                    verb = pending['action']
                else:
                    decision = choose_action(current, npc_id, survival_enabled=self.survival_enabled,
                                             foraging_enabled=self.foraging_enabled)
                    if decision is None:
                        continue
                    verb = decision.action
                # The deterministic ID may not be reused, even after completion.
                action_id = f'auto:{npc_id}:{current.time}'
                if action_id in current.actions:
                    raise InvalidEvent('autonomous action identifier collision')
                if pending is None or pending['at'] != current.time:
                    append(DomainEvent('NPCDecisionRecorded', npc_id,
                                       'deterministic autonomous NPC policy', current.time,
                                       {'npc_id': npc_id, 'action': decision.action,
                                        'score': decision.score, 'reason': decision.reason,
                                        'next_decision_at': current.time + self.decision_cooldown,
                                        **({'policy': 'local-forage-v1'}
                                           if decision.action == 'forage' else {})}),
                           survival_capability=self.survival_enabled,
                           action_capability=decision.action == 'forage')
                schedule_id = 'npc-action:' + action_id
                action_due = current.time + DURATIONS[verb]
                append(DomainEvent('ScheduledEventCreated', None,
                                   'autonomous NPC action completion appointment', current.time,
                                   {'id': schedule_id, 'due': action_due,
                                    'order': current.next_schedule_order, 'kind': 'signal',
                                    'payload': {'__npc_action_id': action_id},
                                    'interrupt': False}), action_capability=True)
                append(DomainEvent('NPCActionStarted', npc_id,
                                   'autonomous NPC action began', current.time,
                                   {'action_id': action_id, 'npc_id': npc_id,
                                    'action': verb, 'schedule_id': schedule_id,
                                    'due': action_due}), action_capability=True)
                started.append(action_id)
                busy.add(npc_id)

            if current.time >= target:
                break
            # Schedule both completed actions and re-evaluations of idle NPCs.
            next_ticks = [target]
            next_ticks.extend(item['due'] for item in current.scheduled.values())
            next_ticks.extend(profile['next_decision_at'] for npc_id, profile
                              in current.npcs.items()
                              if npc_id not in busy
                              and profile['next_decision_at'] > current.time)
            next_tick = min(t for t in next_ticks if t > current.time)
            append(DomainEvent('TimeAdvanced', None, 'authorized player time',
                               next_tick, {'from': current.time, 'to': next_tick}),
                   survival_capability=self.survival_enabled)

        # A complete unit of work: no partial SQLite commits for multiple NPCs.
        committed = self.store.append(world_id, command_id, expected_revision, events,
                                      clock_authorized=True, npc_authorized=True,
                                      action_authorized=True, movement_authorized=self.navigation_enabled,
                                      social_authorized=self.social_enabled,
                                      assistance_authorized=self.assistance_enabled,
                                      consumption_authorized=self.consumption_enabled,
                                      survival_authorized=self.survival_enabled)
        elapsed = committed.time - original.time
        return LivingAdvanceResult(committed, seconds, elapsed, seconds - elapsed,
                                   tuple(started), tuple(completed), tuple(fired),
                                   interrupted, len(events), tuple(social_messages),
                                   tuple(assistance_transitions), tuple(meals_consumed),
                                   tuple(gathered_actions), tuple(knowledge_shares))
