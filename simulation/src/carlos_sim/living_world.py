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
                 social_cooldown: int = MIN_SOCIAL_COOLDOWN):
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

        def append(event: DomainEvent, *, action_capability: bool = False,
                   movement_capability: bool = False,
                   social_capability: bool = False) -> None:
            nonlocal current
            # Keep the entire high-level command fail-closed and bounded.
            if len(events) >= self.max_events_per_advance:
                raise AdvanceLimitExceeded('autonomous simulation event budget exhausted')
            try:
                current = apply_event(current, event, action_authorized=action_capability,
                                      movement_authorized=movement_capability,
                                      social_authorized=social_capability)
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
                    completed.append(item['payload']['__npc_action_id'])
                if item['interrupt']:
                    interrupted = True
                    break
                continue

            busy = {a['npc_id'] for a in current.actions.values()
                    if a['status'] == 'running'}
            busy.update(t['npc_id'] for t in current.travels.values()
                        if t['status'] == 'traveling')
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
                if self.navigation_enabled and not pending_action:
                    if needs_survey(current, npc_id):
                        append(DomainEvent('NPCNavigationSurveyed', npc_id,
                            'NPC surveys locally observable roads', current.time,
                            {'npc_id': npc_id}), movement_capability=True)
                    route_id = next_route(current, npc_id)
                    if route_id is not None:
                        route = current.routes[route_id]
                        here = current.entities[npc_id]['location_id']
                        there = route['b'] if route['a'] == here else route['a']
                        travel_id = f'auto-nav:{npc_id}:{current.time}'
                        if travel_id in current.travels:
                            raise InvalidEvent('autonomous journey identifier collision')
                        due_at = current.time + route['seconds']
                        schedule_id = 'npc-travel:' + travel_id
                        append(DomainEvent('ScheduledEventCreated', None,
                            'scheduled autonomous travel arrival', current.time,
                            {'id': schedule_id, 'due': due_at,
                             'order': current.next_schedule_order, 'kind': 'signal',
                             'payload': {'__npc_travel_id': travel_id}, 'interrupt': False}),
                             movement_capability=True)
                        append(DomainEvent('NPCTravelStarted', npc_id,
                            'autonomous movement over a learned road', current.time,
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
                    decision = choose_action(current, npc_id)
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
                                        'next_decision_at': current.time + self.decision_cooldown}))
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
                               next_tick, {'from': current.time, 'to': next_tick}))

        # A complete unit of work: no partial SQLite commits for multiple NPCs.
        committed = self.store.append(world_id, command_id, expected_revision, events,
                                      clock_authorized=True, npc_authorized=True,
                                      action_authorized=True, movement_authorized=self.navigation_enabled,
                                      social_authorized=self.social_enabled)
        elapsed = committed.time - original.time
        return LivingAdvanceResult(committed, seconds, elapsed, seconds - elapsed,
                                   tuple(started), tuple(completed), tuple(fired),
                                   interrupted, len(events), tuple(social_messages))
