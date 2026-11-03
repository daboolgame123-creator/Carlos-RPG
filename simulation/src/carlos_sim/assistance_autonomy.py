"""Deterministic, bounded autonomous resource-backed help.

Requesters use only their own hunger, stock and directed trust. A provider
uses only *its own* resources, needs, and directed trust to make the response.
No hidden provider stock quantities influence the requester's partner ranking.

The policy emits existing 01-J assistance events, which enforce inventory
conservation, identity, colocation, and legal transitions at the reducer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import WorldState

MIN_REASK_SECONDS = 900
FOOD_REQUEST_HUNGER = 75
FOOD_REQUEST_STOCK = 2
PROVIDER_RESERVE = 2


@dataclass(frozen=True)
class AssistanceIntent:
    actor_id: str
    event_type: str
    request_id: str
    fields: dict[str, Any]
    reason: str


def _available(state: WorldState, npc_id: str) -> bool:
    """Observable physical availability; never inspect a peer's private plan."""
    if npc_id not in state.npcs:
        return False
    if any(t['npc_id'] == npc_id and t['status'] == 'traveling'
           for t in state.travels.values()):
        return False
    return not any(a['npc_id'] == npc_id and a['status'] == 'running'
                   for a in state.actions.values())


def _ready(state: WorldState, npc_id: str) -> bool:
    if not _available(state, npc_id):
        return False
    pending = state.npcs[npc_id]['last_decision']
    return pending is None or pending['at'] != state.time


def _together(state: WorldState, a: str, b: str) -> bool:
    return (a != b and _available(state, a) and _available(state, b)
            and state.entities[a]['location_id'] == state.entities[b]['location_id'])


def choose_assistance_intent(state: WorldState, npc_id: str, phase: str) -> AssistanceIntent | None:
    """Evaluate one actor for one phase, without mutating world state.

    Phases: settle promised help; respond to existing requests; initiate a
    locally addressed food request. The coordinator runs them in fixed order.
    """
    if phase not in ('settle', 'respond', 'request'):
        raise ValueError('unknown assistance planning phase')
    if not _ready(state, npc_id):
        return None

    if phase == 'settle':
        for oid, item in sorted(state.obligations.items()):
            if item['provider'] != npc_id or item['status'] != 'promised':
                continue
            if state.time <= item['responded_at'] or not _together(state, item['requester'], npc_id):
                continue
            # The provider alone evaluates whether their promise can be kept.
            stock = state.resources[npc_id][item['resource']]
            if stock < item['quantity']:
                return AssistanceIntent(npc_id, 'AssistanceCancelled', oid,
                                        {'reason': 'promise_withdrawn'}, 'insufficient_stock')
            return AssistanceIntent(npc_id, 'AssistanceFulfilled', oid, {}, 'fulfil_promise')
        return None

    if phase == 'respond':
        for oid, item in sorted(state.obligations.items()):
            if item['provider'] != npc_id or item['status'] != 'requested':
                continue
            requester = item['requester']
            if (not _together(state, requester, npc_id)
                    or state.entities[requester]['location_id'] != item['location_id']):
                continue
            # Own stock, own hunger, own trust; never inspect a recipient's hidden needs.
            current_stock = state.resources[npc_id][item['resource']]
            # Honoring existing promises matters. The inventory is not
            # escrowed, but a reasonable NPC must not promise the same stock
            # to multiple people on different ticks.
            committed = sum(o['quantity'] for o in state.obligations.values()
                            if o['provider'] == npc_id and o['resource'] == item['resource']
                            and o['status'] == 'promised')
            trust = state.relations.get(npc_id, {}).get(requester, 0)
            own_hunger = state.npcs[npc_id]['needs']['hunger']
            acceptable = (trust >= 0 and own_hunger <= 60
                          and current_stock - committed - item['quantity'] >= PROVIDER_RESERVE)
            return AssistanceIntent(npc_id, 'AssistanceResponded', oid,
                                    {'accept': acceptable}, 'share_surplus' if acceptable else 'decline')
        return None

    # Only food has a corresponding existing hunger need. There is no
    # water-thirst mechanic yet, so never fabricate one.
    own_need = state.npcs[npc_id]['needs']['hunger']
    own_stock = state.resources.get(npc_id, {}).get('food')
    if own_need < FOOD_REQUEST_HUNGER or type(own_stock) is not int or own_stock > FOOD_REQUEST_STOCK:
        return None
    # One open request per resource, and a 900-second refractory period to
    # prevent repeatedly begging another peer after a quick refusal.
    if any(o['requester'] == npc_id and o['resource'] == 'food' and
           (o['status'] in ('requested', 'promised') or
            state.time - o['created_at'] < MIN_REASK_SECONDS)
           for o in state.obligations.values()):
        return None
    peers: list[tuple[int, str]] = []
    for peer in sorted(state.npcs):
        if peer == npc_id or not _together(state, npc_id, peer):
            continue
        trust = state.relations.get(npc_id, {}).get(peer, 0)
        if trust < -20:
            continue
        # Schema eligibility check ONLY: do not read the peer's food quantity.
        if type(state.resources.get(peer, {}).get('food')) is not int:
            continue
        peers.append((-trust, peer))
    if not peers:
        return None
    _, recipient = min(peers)
    quantity = min(3, 4 - own_stock)
    oid = f'auto-help:{npc_id}:{state.time}'
    if oid in state.obligations:
        return None
    return AssistanceIntent(npc_id, 'AssistanceRequested', oid,
                            {'provider': recipient, 'resource': 'food', 'quantity': quantity},
                            'own_food_shortage')
