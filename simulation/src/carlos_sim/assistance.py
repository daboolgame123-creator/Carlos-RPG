"""Phase 01-J: auditable promises and physically delivered, conserved assistance.

This trusted-local prototype requires explicit initiation/acceptance/fulfilment.
Speech acts alone never transfer resources. A transfer is one atomic event.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import RevisionConflict, SQLiteEventStore
from .time_engine import TimeEngine

ASSISTANCE_RESOURCES = frozenset({'food', 'water'})
_STATUSES = frozenset({'requested', 'promised', 'declined', 'fulfilled', 'cancelled'})
_FIELDS = {'requester', 'provider', 'resource', 'quantity', 'location_id',
           'created_at', 'status', 'responded_at', 'resolved_at', 'reason',
           'trust_before', 'trust_after', 'transfer'}
MAX_ASSISTANCE_QUANTITY = 1000
TRUST_REWARD = 5


def _on_site(state: dict[str, Any], actor_id: str) -> bool:
    return actor_id in state['npcs'] and not any(
        trip['npc_id'] == actor_id and trip['status'] == 'traveling'
        for trip in state['travels'].values()) and not any(
        action['npc_id'] == actor_id and action['status'] == 'running'
        for action in state['actions'].values())


def _together(state: dict[str, Any], requester: str, provider: str) -> bool:
    return (_on_site(state, requester) and _on_site(state, provider)
            and requester != provider
            and state['entities'][requester]['location_id']
            == state['entities'][provider]['location_id'])


def validate_obligations(state: dict[str, Any]) -> None:
    """Validate every event-sourced contract, not only the latest change."""
    seen = set()
    for oid, item in state['obligations'].items():
        if (not isinstance(oid, str) or not oid or len(oid) > 128
                or not isinstance(item, dict) or set(item) != _FIELDS):
            raise ValueError('invalid assistance obligation record')
        requester, provider, resource = (item['requester'], item['provider'], item['resource'])
        if (requester not in state['npcs'] or provider not in state['npcs']
                or requester == provider or resource not in ASSISTANCE_RESOURCES
                or item['location_id'] not in state['locations']
                or type(item['quantity']) is not int
                or not 1 <= item['quantity'] <= MAX_ASSISTANCE_QUANTITY
                or type(item['created_at']) is not int
                or not 0 <= item['created_at'] <= state['time']):
            raise ValueError('invalid assistance parties or requested goods')
        key = (requester, provider, resource, item['created_at'])
        if key in seen:
            raise ValueError('duplicate same-tick assistance request')
        seen.add(key)
        status = item['status']
        if status not in _STATUSES:
            raise ValueError('invalid assistance state')
        responded, resolved = item['responded_at'], item['resolved_at']
        if (responded is not None and
                (type(responded) is not int or not item['created_at'] <= responded <= state['time'])):
            raise ValueError('invalid assistance response time')
        if (resolved is not None and
                (type(resolved) is not int or not item['created_at'] <= resolved <= state['time'])):
            raise ValueError('invalid assistance resolution time')
        if status == 'requested':
            if responded is not None or resolved is not None or item['reason'] is not None:
                raise ValueError('unanswered request has unexpected outcome')
        elif status == 'promised':
            if responded is None or resolved is not None or item['reason'] is not None:
                raise ValueError('promise has unexpected outcome')
        elif status == 'declined':
            if responded is None or resolved != responded or item['reason'] != 'declined':
                raise ValueError('refusal has invalid resolution')
        elif status == 'fulfilled':
            if responded is None or resolved is None or resolved < responded or item['reason'] != 'delivered':
                raise ValueError('fulfilment has invalid resolution')
        elif status == 'cancelled':
            if (resolved is None or (responded is not None and resolved < responded)
                    or item['reason'] not in ('request_withdrawn', 'promise_withdrawn')):
                raise ValueError('cancellation has invalid resolution')
        if status == 'fulfilled':
            transfer = item['transfer']
            if not isinstance(transfer, dict) or set(transfer) != {
                    'provider_before', 'provider_after', 'requester_before', 'requester_after'}:
                raise ValueError('fulfilled assistance needs recorded transfer evidence')
            a, b, c, d = (transfer[x] for x in (
                'provider_before', 'provider_after', 'requester_before', 'requester_after'))
            if (any(type(x) is not int or x < 0 for x in (a, b, c, d))
                    or a - b != item['quantity'] or d - c != item['quantity']
                    or a + c != b + d):
                raise ValueError('assistance transfer must conserve initialized goods')
            before, after = item['trust_before'], item['trust_after']
            if (type(before) is not int or type(after) is not int
                    or not -100 <= before <= 100
                    or after != min(100, before + TRUST_REWARD)):
                raise ValueError('invalid fulfilled-help trust outcome')
        elif (item['trust_before'] is not None or item['trust_after'] is not None
                or item['transfer'] is not None):
            raise ValueError('unfulfilled help cannot earn trust or transfer goods')
        if (requester not in state['resources'] or provider not in state['resources']
                or type(state['resources'][requester].get(resource)) is not int
                or type(state['resources'][provider].get(resource)) is not int):
            raise ValueError('assistance resource must remain explicitly initialized')


def project_assistance_event(state: dict[str, Any], event: DomainEvent, *,
                             assistance_authorized: bool) -> None:
    if not assistance_authorized:
        raise ValueError('assistance events need a separate trusted capability')
    data = event.data
    kind = event.event_type
    oid = data.get('id')
    if not isinstance(oid, str) or not 0 < len(oid) <= 128:
        raise ValueError('assistance request ID invalid')
    if kind == 'AssistanceRequested':
        if set(data) != {'id', 'provider', 'resource', 'quantity'}:
            raise ValueError('invalid assistance request fields')
        requester, provider = event.actor_id, data['provider']
        resource, quantity = data['resource'], data['quantity']
        if (oid in state['obligations'] or not isinstance(requester, str)
                or not isinstance(provider, str) or not _together(state, requester, provider)
                or resource not in ASSISTANCE_RESOURCES or type(quantity) is not int
                or not 1 <= quantity <= MAX_ASSISTANCE_QUANTITY):
            raise ValueError('assistance requires distinct, present NPCs and valid goods')
        if (type(state['resources'].get(requester, {}).get(resource)) is not int
                or type(state['resources'].get(provider, {}).get(resource)) is not int):
            raise ValueError('both assistance inventories must be explicitly initialized')
        if any(o['requester'] == requester and o['provider'] == provider and o['resource'] == resource
               and (o['status'] in ('requested', 'promised') or o['created_at'] == state['time'])
               for o in state['obligations'].values()):
            raise ValueError('duplicate or currently open assistance request')
        state['obligations'][oid] = {
            'requester': requester, 'provider': provider, 'resource': resource,
            'quantity': quantity,
            'location_id': state['entities'][requester]['location_id'],
            'created_at': state['time'], 'status': 'requested',
            'responded_at': None, 'resolved_at': None, 'reason': None,
            'trust_before': None, 'trust_after': None, 'transfer': None,
        }
        return
    if set(data) not in ({'id', 'accept'}, {'id'}, {'id', 'reason'}):
        raise ValueError('invalid assistance transition fields')
    item = state['obligations'].get(oid)
    if item is None:
        raise ValueError('unknown assistance request')
    requester, provider = item['requester'], item['provider']
    if kind == 'AssistanceResponded':
        if set(data) != {'id', 'accept'} or type(data['accept']) is not bool:
            raise ValueError('response must be an explicit boolean')
        if item['status'] != 'requested' or event.actor_id != provider:
            raise ValueError('only the provider can respond to an open request')
        if not _together(state, requester, provider) or state['entities'][requester]['location_id'] != item['location_id']:
            raise ValueError('local response must occur at the original request location')
        item['responded_at'] = state['time']
        if data['accept']:
            item['status'] = 'promised'
        else:
            item.update(status='declined', resolved_at=state['time'], reason='declined')
        return
    if kind == 'AssistanceFulfilled':
        if set(data) != {'id'} or item['status'] != 'promised' or event.actor_id != provider:
            raise ValueError('only the provider can fulfil a valid promise once')
        if not _together(state, requester, provider):
            raise ValueError('delivery requires both parties physically present together')
        resource, quantity = item['resource'], item['quantity']
        stock = state['resources'][provider][resource]
        recipient_stock = state['resources'][requester][resource]
        if type(stock) is not int or type(recipient_stock) is not int or stock < quantity:
            raise ValueError('provider has insufficient real stock to deliver')
        state['resources'][provider][resource] = stock - quantity
        state['resources'][requester][resource] = recipient_stock + quantity
        previous = state['relations'].setdefault(requester, {}).get(provider, 0)
        item.update(status='fulfilled', resolved_at=state['time'], reason='delivered',
                    trust_before=previous, trust_after=min(100, previous + TRUST_REWARD),
                    transfer={'provider_before': stock, 'provider_after': stock - quantity,
                              'requester_before': recipient_stock,
                              'requester_after': recipient_stock + quantity})
        state['relations'][requester][provider] = item['trust_after']
        return
    if kind == 'AssistanceCancelled':
        if set(data) != {'id', 'reason'}:
            raise ValueError('invalid assistance cancellation')
        if (item['status'] == 'requested' and event.actor_id == requester
                and data['reason'] == 'request_withdrawn'):
            item.update(status='cancelled', resolved_at=state['time'], reason=data['reason'])
        elif (item['status'] == 'promised' and event.actor_id == provider
                and data['reason'] == 'promise_withdrawn'):
            item.update(status='cancelled', resolved_at=state['time'], reason=data['reason'])
        else:
            raise ValueError('only request owner or promisor may withdraw an active obligation')
        return
    raise ValueError('unknown assistance event')


@dataclass(frozen=True)
class AssistanceResult:
    id: str
    status: str
    state: WorldState


class NPCAssistanceService:
    """Trusted local workflow. Each transition is an atomic SQLite command."""
    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError('assistance service and clock must share a store')
        self.store, self.clock = store, clock

    def _commit(self, world_id: str, ident: str, command_id: str, expected_revision: int,
                event_type: str, actor: str, fields: dict[str, Any]) -> AssistanceResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict('stale assistance revision')
        saved = self.store.append(world_id, command_id, expected_revision,
            [DomainEvent(event_type, actor, 'traceable physical assistance', state.time,
                         {'id': ident, **fields})], assistance_authorized=True)
        return AssistanceResult(ident, saved.obligations[ident]['status'], saved)

    def request(self, world_id: str, requester: str, provider: str, resource: str,
                quantity: int, request_id: str, *, expected_revision: int) -> AssistanceResult:
        return self._commit(world_id, request_id, 'help-request:' + request_id,
            expected_revision, 'AssistanceRequested', requester,
            {'provider': provider, 'resource': resource, 'quantity': quantity})

    def respond(self, world_id: str, provider: str, request_id: str, *,
                accept: bool, command_id: str, expected_revision: int) -> AssistanceResult:
        return self._commit(world_id, request_id, command_id, expected_revision,
                            'AssistanceResponded', provider, {'accept': accept})

    def deliver(self, world_id: str, provider: str, request_id: str, *,
                command_id: str, expected_revision: int) -> AssistanceResult:
        return self._commit(world_id, request_id, command_id, expected_revision,
                            'AssistanceFulfilled', provider, {})

    def cancel(self, world_id: str, actor: str, request_id: str, *,
               reason: str, command_id: str, expected_revision: int) -> AssistanceResult:
        return self._commit(world_id, request_id, command_id, expected_revision,
                            'AssistanceCancelled', actor, {'reason': reason})
