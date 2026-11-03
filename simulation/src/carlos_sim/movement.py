"""Time-bound NPC movement and strictly local observation for isolated test worlds.

Routes are explicit world topology. Observations are dated *snapshots*, never a
source of global omniscience. All state changes are deterministic domain events.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine


def _visible(state: dict[str, Any], location: str) -> list[str]:
    return sorted(ident for ident, entity in state['entities'].items()
                  if entity['location_id'] == location)


def _observe(state: dict[str, Any], npc_id: str, time: int) -> None:
    location = state['entities'][npc_id]['location_id']
    state['observations'].setdefault(npc_id, {})[location] = {
        'at': time, 'occupants': _visible(state, location)
    }


def validate_movement(state: dict[str, Any]) -> None:
    routes = state['routes']
    for ident, route in routes.items():
        if not isinstance(ident, str) or not ident or not isinstance(route, dict) or set(route) != {'a', 'b', 'seconds'}:
            raise ValueError('invalid route')
        if (route['a'] not in state['locations'] or route['b'] not in state['locations']
                or route['a'] == route['b'] or type(route['seconds']) is not int or route['seconds'] <= 0):
            raise ValueError('route has invalid endpoint or duration')
    busy = set()
    for travel_id, travel in state['travels'].items():
        if not isinstance(travel_id, str) or not travel_id or not isinstance(travel, dict) or set(travel) != {
                'npc_id', 'route_id', 'origin', 'destination', 'start', 'due', 'schedule_id', 'status', 'arrived_at'}:
            raise ValueError('invalid travel record')
        who, route_id = travel['npc_id'], travel['route_id']
        if who not in state['npcs'] or route_id not in routes:
            raise ValueError('invalid travel actor or route')
        route = routes[route_id]
        if {travel['origin'], travel['destination']} != {route['a'], route['b']}:
            raise ValueError('travel endpoints do not match route')
        if (type(travel['start']) is not int or type(travel['due']) is not int
                or travel['start'] < 0 or travel['due'] - travel['start'] != route['seconds']
                or travel['schedule_id'] != 'npc-travel:' + travel_id):
            raise ValueError('invalid travel timing')
        if travel['status'] == 'traveling':
            if who in busy or travel['arrived_at'] is not None or state['time'] > travel['due']:
                raise ValueError('invalid concurrent or overdue travel')
            if state['entities'][who]['location_id'] != travel['origin']:
                raise ValueError('traveler moved before arrival')
            busy.add(who)
        elif travel['status'] == 'arrived':
            if (travel['arrived_at'] != travel['due'] or state['time'] < travel['due']
                    or state['entities'][who]['location_id'] not in state['locations']):
                raise ValueError('invalid arrived travel')
        else:
            raise ValueError('invalid travel status')
    for who, places in state['observations'].items():
        if who not in state['npcs'] or not isinstance(places, dict):
            raise ValueError('observation belongs to unknown NPC')
        for location, obs in places.items():
            if location not in state['locations'] or not isinstance(obs, dict) or set(obs) != {'at', 'occupants'}:
                raise ValueError('invalid observation')
            if (type(obs['at']) is not int or obs['at'] < 0 or obs['at'] > state['time']
                    or not isinstance(obs['occupants'], list)
                    or obs['occupants'] != sorted(set(obs['occupants']))
                    or any(ident not in state['entities'] for ident in obs['occupants'])):
                raise ValueError('invalid observation contents')


def validate_travel_reservations(state: WorldState) -> None:
    for ident, scheduled in state.scheduled.items():
        payload = scheduled['payload']
        if '__npc_travel_id' not in payload:
            continue
        travel_id = payload['__npc_travel_id']
        travel = state.travels.get(travel_id) if isinstance(travel_id, str) else None
        if (travel is None or travel['status'] != 'traveling'
                or travel['schedule_id'] != ident or travel['due'] != scheduled['due']):
            raise ValueError('orphaned NPC travel completion schedule')
    for ident, travel in state.travels.items():
        if travel['status'] == 'traveling':
            scheduled = state.scheduled.get(travel['schedule_id'])
            if scheduled is None or scheduled['payload'] != {'__npc_travel_id': ident}:
                raise ValueError('travel lacks a matching completion schedule')


def project_movement_event(state: dict[str, Any], event: DomainEvent, *,
                           bootstrap: bool, movement_authorized: bool) -> None:
    data = event.data
    if event.event_type == 'RouteCreated':
        if (not bootstrap or state['time'] != 0 or event.actor_id is not None
                or set(data) != {'id', 'a', 'b', 'seconds'}):
            raise ValueError('routes may only be created during trusted bootstrap')
        ident = data['id']
        if not isinstance(ident, str) or not ident or ident in state['routes']:
            raise ValueError('invalid or duplicate route ID')
        if (not isinstance(data['a'], str) or not isinstance(data['b'], str)
                or data['a'] not in state['locations'] or data['b'] not in state['locations']
                or data['a'] == data['b'] or type(data['seconds']) is not int or data['seconds'] <= 0):
            raise ValueError('invalid route endpoints or duration')
        state['routes'][ident] = {k: data[k] for k in ('a', 'b', 'seconds')}
        return
    if not movement_authorized:
        raise ValueError('movement and perception require a trusted capability')
    if event.event_type == 'NPCTravelStarted':
        if set(data) != {'id', 'npc_id', 'route_id', 'origin', 'destination', 'due', 'schedule_id'}:
            raise ValueError('invalid travel start fields')
        ident, npc_id = data['id'], data['npc_id']
        if not isinstance(ident, str) or not ident or ident in state['travels']:
            raise ValueError('duplicate or invalid travel ID')
        if (not isinstance(npc_id, str) or npc_id not in state['npcs'] or event.actor_id != npc_id):
            raise ValueError('only existing NPCs can travel')
        route = state['routes'].get(data['route_id']) if isinstance(data['route_id'], str) else None
        if route is None or {data['origin'], data['destination']} != {route['a'], route['b']}:
            raise ValueError('traveler must use an existing adjacent route')
        if (state['entities'][npc_id]['location_id'] != data['origin']
                or type(data['due']) is not int or data['due'] != state['time'] + route['seconds']
                or data['schedule_id'] != 'npc-travel:' + ident):
            raise ValueError('travel origin, duration or schedule mismatch')
        if any(a['npc_id'] == npc_id and a['status'] == 'running' for a in state['actions'].values()):
            raise ValueError('NPC is busy with an existing action')
        if any(t['npc_id'] == npc_id and t['status'] == 'traveling' for t in state['travels'].values()):
            raise ValueError('NPC is already traveling')
        scheduled = state['scheduled'].get(data['schedule_id'])
        if (scheduled is None or scheduled['due'] != data['due']
                or scheduled['payload'] != {'__npc_travel_id': ident}
                or scheduled['interrupt']):
            raise ValueError('travel requires matching noninterrupting completion signal')
        state['travels'][ident] = {'npc_id': npc_id, 'route_id': data['route_id'],
                                  'origin': data['origin'], 'destination': data['destination'],
                                  'start': state['time'], 'due': data['due'],
                                  'schedule_id': data['schedule_id'], 'status': 'traveling',
                                  'arrived_at': None}
    elif event.event_type == 'NPCObserved':
        if set(data) != {'npc_id'} or data['npc_id'] not in state['npcs'] or event.actor_id != data['npc_id']:
            raise ValueError('only the observing NPC may record its local perception')
        if any(t['npc_id'] == data['npc_id'] and t['status'] == 'traveling' for t in state['travels'].values()):
            raise ValueError('no local observation while in transit')
        _observe(state, data['npc_id'], state['time'])
    else:
        raise ValueError('unsupported movement event')


def complete_travel(state: dict[str, Any], travel_id: str, schedule_id: str, time: int) -> None:
    travel = state['travels'].get(travel_id) if isinstance(travel_id, str) else None
    if (travel is None or travel['status'] != 'traveling'
            or travel['schedule_id'] != schedule_id or travel['due'] != time):
        raise ValueError('travel cannot complete without valid journey and due time')
    who = travel['npc_id']
    if state['entities'][who]['location_id'] != travel['origin']:
        raise ValueError('traveler moved before completion')
    state['entities'][who]['location_id'] = travel['destination']
    travel['status'] = 'arrived'
    travel['arrived_at'] = time
    _observe(state, who, time)


@dataclass(frozen=True)
class TravelStart:
    id: str
    npc_id: str
    due: int
    state: WorldState


class NPCMovementService:
    """Trusted local movement and observation. Does not impersonate the player."""
    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError('movement and clock must share a store')
        self.store, self.clock = store, clock

    def start(self, world_id: str, npc_id: str, route_id: str, travel_id: str, *,
              expected_revision: int) -> TravelStart:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict('stale movement request')
        if not isinstance(travel_id, str) or not travel_id:
            raise ValueError('travel ID required')
        if npc_id not in state.npcs or route_id not in state.routes:
            raise ValueError('NPC or route missing')
        route = state.routes[route_id]
        current = state.entities[npc_id]['location_id']
        if current == route['a']:
            dest = route['b']
        elif current == route['b']:
            dest = route['a']
        else:
            raise ValueError('NPC must be at a route endpoint')
        due = state.time + route['seconds']
        schedule_id = 'npc-travel:' + travel_id
        events = [
            DomainEvent('ScheduledEventCreated', None, 'NPC movement appointment', state.time,
                        {'id': schedule_id, 'due': due, 'order': state.next_schedule_order,
                         'kind': 'signal', 'payload': {'__npc_travel_id': travel_id}, 'interrupt': False}),
            DomainEvent('NPCTravelStarted', npc_id, 'NPC begins moving on an adjacent route', state.time,
                        {'id': travel_id, 'npc_id': npc_id, 'route_id': route_id, 'origin': current,
                         'destination': dest, 'due': due, 'schedule_id': schedule_id}),
        ]
        committed = self.store.append(world_id, 'travel-start:' + travel_id, expected_revision,
                                      events, movement_authorized=True)
        return TravelStart(travel_id, npc_id, due, committed)

    def observe(self, world_id: str, npc_id: str, *, command_id: str,
                expected_revision: int) -> WorldState:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict('stale perception request')
        if npc_id not in state.npcs:
            raise ValueError('only NPCs can observe')
        return self.store.append(world_id, command_id, expected_revision, [
            DomainEvent('NPCObserved', npc_id, 'NPC observes only co-located entities',
                        state.time, {'npc_id': npc_id})], movement_authorized=True)


def perceive_local(state: WorldState, npc_id: str) -> dict[str, Any] | None:
    """Read only a previously recorded observation, not a fresh omniscient lookup."""
    if npc_id not in state.npcs:
        return None
    place = state.entities[npc_id]['location_id']
    observation = state.observations.get(npc_id, {}).get(place)
    if observation is None:
        return None
    return {'location_id': place, 'at': observation['at'],
            'occupants': list(observation['occupants'])}
