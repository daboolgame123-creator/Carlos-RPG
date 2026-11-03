"""NPC-local road knowledge, deterministic pathfinding and autonomous exploration.

A surveyed road is known because its endpoint touches the NPC's *current*
location. A hidden remote road is never added to an NPC's memory. Journey
completion is managed by the existing movement reducer; no teleportation.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore, RevisionConflict
from .time_engine import TimeEngine


def _connected(state: dict[str, Any], here: str) -> list[str]:
    return sorted(name for name, r in state['routes'].items()
                  if here in (r['a'], r['b']))


def _traveling(state: dict[str, Any], npc: str) -> bool:
    return any(t['npc_id'] == npc and t['status'] == 'traveling'
               for t in state['travels'].values())


def validate_navigation(state: dict[str, Any]) -> None:
    for npc_id, nav in state['navigation'].items():
        if npc_id not in state['npcs'] or not isinstance(nav, dict) or set(nav) != {
                'known_routes', 'visited', 'target'}:
            raise ValueError('invalid NPC navigation profile')
        if (not isinstance(nav['known_routes'], list)
                or nav['known_routes'] != sorted(set(nav['known_routes']))
                or any(r not in state['routes'] for r in nav['known_routes'])):
            raise ValueError('invalid known route list')
        if (not isinstance(nav['visited'], list)
                or nav['visited'] != sorted(set(nav['visited']))
                or any(x not in state['locations'] for x in nav['visited'])):
            raise ValueError('invalid visited place list')
        if nav['target'] is not None and (not isinstance(nav['target'], str)
                or nav['target'] not in state['locations']):
            raise ValueError('invalid navigator destination')
        known_places = set(nav['visited'])
        for r in nav['known_routes']:
            known_places.update((state['routes'][r]['a'], state['routes'][r]['b']))
        if nav['target'] is not None and nav['target'] not in known_places:
            raise ValueError('navigation target cannot be an unseen place')


def project_navigation_event(state: dict[str, Any], event: DomainEvent, *,
                             movement_authorized: bool) -> None:
    p = event.data
    npc_id = p.get('npc_id')
    if (not movement_authorized or not isinstance(npc_id, str)
            or npc_id not in state['npcs'] or event.actor_id != npc_id):
        raise ValueError('navigation needs a trusted NPC-local actor')
    if _traveling(state, npc_id):
        raise ValueError('traveling NPC cannot inspect a local route')
    if any(a['npc_id'] == npc_id and a['status'] == 'running'
           for a in state['actions'].values()):
        raise ValueError('busy NPC cannot survey or choose a travel target')
    nav = state['navigation'].setdefault(npc_id, {
        'known_routes': [], 'visited': [], 'target': None})
    if event.event_type == 'NPCNavigationSurveyed':
        if set(p) != {'npc_id'}:
            raise ValueError('invalid route survey')
        here = state['entities'][npc_id]['location_id']
        nav['known_routes'] = sorted(set(nav['known_routes']) | set(_connected(state, here)))
        nav['visited'] = sorted(set(nav['visited']) | {here})
    elif event.event_type == 'NPCNavigationTargetSet':
        if set(p) != {'npc_id', 'target'} or not isinstance(p['target'], str):
            raise ValueError('invalid destination request')
        known = set(nav['visited'])
        for rid in nav['known_routes']:
            known.update((state['routes'][rid]['a'], state['routes'][rid]['b']))
        if p['target'] not in known:
            raise ValueError('target is not known to this NPC')
        current = state['entities'][npc_id]['location_id']
        if p['target'] != current and not _shortest(state['routes'], nav['known_routes'], current, p['target']):
            raise ValueError('target cannot be reached using known roads')
        nav['target'] = p['target']
    else:
        raise ValueError('unsupported navigation event')


def _shortest(routes: Any, known_routes: Any, origin: str, destination: str) -> tuple[str, ...]:
    """Dijkstra: minimum total *known* route seconds; stable lexical tie."""
    if origin == destination:
        return ()
    graph: dict[str, list[tuple[str, str, int]]] = {}
    for ident in known_routes:
        edge = routes[ident]
        a, b, seconds = edge['a'], edge['b'], edge['seconds']
        graph.setdefault(a, []).append((b, ident, seconds))
        graph.setdefault(b, []).append((a, ident, seconds))
    q = [(0, (), origin)]
    best: dict[str, tuple[int, tuple[str, ...]]] = {origin: (0, ())}
    while q:
        cost, path, place = heapq.heappop(q)
        if best[place] != (cost, path):
            continue
        if place == destination:
            return path
        for nxt, route_id, seconds in sorted(graph.get(place, [])):
            candidate = (cost + seconds, path + (route_id,))
            if nxt not in best or candidate < best[nxt]:
                best[nxt] = candidate
                heapq.heappush(q, (*candidate, nxt))
    return ()


def shortest_known_route(state: WorldState, npc_id: str, destination: str) -> tuple[str, ...]:
    nav = state.navigation.get(npc_id)
    if nav is None or destination not in state.locations:
        return ()
    origin = state.entities[npc_id]['location_id']
    return _shortest(state.routes, nav['known_routes'], origin, destination)


def needs_survey(state: WorldState, npc_id: str) -> bool:
    if npc_id not in state.npcs:
        return False
    if any(t['npc_id'] == npc_id and t['status'] == 'traveling' for t in state.travels.values()):
        return False
    here = state.entities[npc_id]['location_id']
    nav = state.navigation.get(npc_id)
    if nav is None or here not in nav['visited']:
        return True
    return any(ident not in nav['known_routes'] for ident, r in state.routes.items()
               if here in (r['a'], r['b']))


def next_route(state: WorldState, npc_id: str) -> str | None:
    """Return the first step of an independently chosen, *known* itinerary.

    An assigned known target takes precedence; autonomous exploration only
    runs when the NPC values exploration and has sufficient stamina/food.
    Unexplored known endpoints are ranked by shortest journey cost then ID.
    """
    if npc_id not in state.npcs:
        return None
    if any(t['npc_id'] == npc_id and t['status'] == 'traveling' for t in state.travels.values()):
        return None
    nav = state.navigation.get(npc_id)
    if nav is None:
        return None
    npc = state.npcs[npc_id]
    current = state.entities[npc_id]['location_id']
    target = nav['target']
    if target is not None:
        if target == current:
            return None
        path = _shortest(state.routes, nav['known_routes'], current, target)
        return path[0] if path else None
    if (npc['goals']['explore'] < 50 or npc['needs']['fatigue'] >= 70
            or npc['needs']['hunger'] >= 75):
        return None
    endpoints = set()
    for rid in nav['known_routes']:
        r = state.routes[rid]
        endpoints.update((r['a'], r['b']))
    candidates = []
    for place in endpoints - set(nav['visited']):
        path = _shortest(state.routes, nav['known_routes'], current, place)
        if path:
            cost = sum(state.routes[r]['seconds'] for r in path)
            candidates.append((cost, place, path))
    if not candidates:
        return None
    return min(candidates)[2][0]


@dataclass(frozen=True)
class NavigationResult:
    npc_id: str
    target: str
    known_route_ids: tuple[str, ...]
    path: tuple[str, ...]
    state: WorldState


class NPCNavigationService:
    """Trusted local API; neither remote authentication nor map omniscience."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError('navigation and clock must share an event store')
        self.store, self.clock = store, clock

    def survey(self, world_id: str, npc_id: str, *, command_id: str,
               expected_revision: int) -> WorldState:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict('outdated survey revision')
        if not needs_survey(state, npc_id):
            return state
        event = DomainEvent('NPCNavigationSurveyed', npc_id,
                            'NPC examines adjacent routes', state.time, {'npc_id': npc_id})
        return self.store.append(world_id, command_id, expected_revision,
                                 [event], movement_authorized=True)

    def target(self, world_id: str, npc_id: str, destination: str, *,
               command_id: str, expected_revision: int) -> NavigationResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict('outdated destination revision')
        event = DomainEvent('NPCNavigationTargetSet', npc_id,
                            'NPC selects previously learned destination', state.time,
                            {'npc_id': npc_id, 'target': destination})
        new = self.store.append(world_id, command_id, expected_revision,
                                [event], movement_authorized=True)
        return NavigationResult(npc_id, destination,
                                tuple(new.navigation[npc_id]['known_routes']),
                                shortest_known_route(new, npc_id, destination), new)
