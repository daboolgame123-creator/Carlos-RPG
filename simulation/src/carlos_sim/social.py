"""Deterministic, locally delivered NPC social exchanges with asymmetric trust.

An offered favor is a *speech act*, not a completed favor or resource transfer.
Only an addressed, co-located recipient can acknowledge it. All effects are
pure domain projections; no NPC can access another's undisclosed intentions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain import DomainEvent, WorldState
from .store import RevisionConflict, SQLiteEventStore
from .time_engine import TimeEngine

KINDS = frozenset({'greeting', 'offer_help', 'request_help', 'threat'})
TRUST_MIN, TRUST_MAX = -100, 100


def decision(kind: str, current_trust: int) -> tuple[str, int]:
    """Receiver's deterministic interpretation, not an objective truth claim."""
    if kind == 'greeting':
        return 'acknowledged', 1
    if kind == 'offer_help':
        return ('welcomed', 3) if current_trust >= -20 else ('distrusted', -1)
    if kind == 'request_help':
        return ('considered', 1) if current_trust >= 0 else ('refused', -2)
    if kind == 'threat':
        return 'alarmed', -12
    raise ValueError('unsupported social kind')


def _present(state: dict[str, Any], entity_id: str) -> bool:
    if entity_id not in state['entities']:
        return False
    from .movement import _in_transit
    return not _in_transit(state, entity_id)


def _co_located(state: dict[str, Any], sender: str, recipient: str) -> bool:
    return (_present(state, sender) and _present(state, recipient)
            and state['entities'][sender]['location_id'] == state['entities'][recipient]['location_id'])


def validate_social(state: dict[str, Any]) -> None:
    for npc_id, peer_map in state['relations'].items():
        if npc_id not in state['npcs'] or not isinstance(peer_map, dict):
            raise ValueError('invalid relationship owner')
        for peer, value in peer_map.items():
            if (peer not in state['entities'] or peer == npc_id or type(value) is not int
                    or not TRUST_MIN <= value <= TRUST_MAX):
                raise ValueError('invalid asymmetric trust value')
    for ident, msg in state['social_messages'].items():
        if (not isinstance(ident, str) or not ident or not isinstance(msg, dict)
                or set(msg) != {'sender', 'recipient', 'kind', 'text', 'location_id',
                                'sent_at', 'status', 'reaction', 'trust_before', 'trust_after'}):
            raise ValueError('invalid social exchange')
        if (msg['sender'] not in state['entities'] or msg['recipient'] not in state['npcs']
                or msg['sender'] == msg['recipient'] or msg['kind'] not in KINDS
                or not isinstance(msg['text'], str) or not 1 <= len(msg['text']) <= 500
                or msg['location_id'] not in state['locations']
                or type(msg['sent_at']) is not int or not 0 <= msg['sent_at'] <= state['time']):
            raise ValueError('invalid social sender/recipient/payload')
        if msg['status'] == 'pending':
            if any(msg[k] is not None for k in ('reaction', 'trust_before', 'trust_after')):
                raise ValueError('pending exchange cannot have relationship effects')
        elif msg['status'] == 'received':
            before, after = msg['trust_before'], msg['trust_after']
            if (type(before) is not int or type(after) is not int
                    or not TRUST_MIN <= before <= TRUST_MAX
                    or not TRUST_MIN <= after <= TRUST_MAX):
                raise ValueError('invalid social outcome')
            reaction, change = decision(msg['kind'], before)
            if msg['reaction'] != reaction or after != max(TRUST_MIN, min(TRUST_MAX, before + change)):
                raise ValueError('forged social reaction')
        else:
            raise ValueError('invalid social status')


def project_social_event(state: dict[str, Any], event: DomainEvent, *, social_authorized: bool) -> None:
    if not social_authorized:
        raise ValueError('social events require trusted local capability')
    p = event.data
    if event.event_type == 'SocialMessageSent':
        if set(p) != {'id', 'recipient', 'kind', 'text'}:
            raise ValueError('invalid message fields')
        mid, sender, recipient = p['id'], event.actor_id, p['recipient']
        if (not isinstance(mid, str) or not mid or len(mid) > 128
                or mid in state['social_messages'] or not isinstance(sender, str)
                or not isinstance(recipient, str) or sender == recipient
                or recipient not in state['npcs'] or p['kind'] not in KINDS
                or not isinstance(p['text'], str) or not 1 <= len(p['text']) <= 500):
            raise ValueError('invalid message identity or content')
        # Repeating the same speech act between the same pair at one tick
        # cannot fabricate unlimited trust without any simulated time passing.
        if any(m['sender'] == sender and m['recipient'] == recipient
               and m['kind'] == p['kind'] and m['sent_at'] == state['time']
               for m in state['social_messages'].values()):
            raise ValueError('duplicate social act in the same simulation tick')
        if not _co_located(state, sender, recipient):
            raise ValueError('social message requires both participants present locally')
        state['social_messages'][mid] = {
            'sender': sender, 'recipient': recipient, 'kind': p['kind'], 'text': p['text'],
            'location_id': state['entities'][recipient]['location_id'], 'sent_at': state['time'],
            'status': 'pending', 'reaction': None, 'trust_before': None, 'trust_after': None,
        }
    elif event.event_type == 'SocialMessageReceived':
        if set(p) != {'id'} or not isinstance(p['id'], str):
            raise ValueError('invalid receipt fields')
        msg = state['social_messages'].get(p['id'])
        if msg is None or msg['status'] != 'pending' or event.actor_id != msg['recipient']:
            raise ValueError('social receipt must belong to pending message recipient')
        if not _co_located(state, msg['sender'], msg['recipient']):
            raise ValueError('social exchange must still be locally deliverable')
        if state['entities'][msg['recipient']]['location_id'] != msg['location_id']:
            raise ValueError('social receipt must occur at the original message location')
        recipient, sender = msg['recipient'], msg['sender']
        trust = state['relations'].setdefault(recipient, {}).get(sender, 0)
        reaction, delta = decision(msg['kind'], trust)
        updated = max(TRUST_MIN, min(TRUST_MAX, trust + delta))
        state['relations'][recipient][sender] = updated
        msg.update(status='received', reaction=reaction, trust_before=trust, trust_after=updated)
    else:
        raise ValueError('unsupported social event')


@dataclass(frozen=True)
class SocialResult:
    message_id: str
    reaction: str
    trust_before: int
    trust_after: int
    state: WorldState


class NPCSocialService:
    """A trusted local call sends and records reception as one atomic interaction."""

    def __init__(self, store: SQLiteEventStore, clock: TimeEngine):
        if clock.store is not store:
            raise ValueError('social service and clock must share store')
        self.store, self.clock = store, clock

    def interact(self, world_id: str, sender: str, recipient: str, *, kind: str,
                 text: str, message_id: str, expected_revision: int) -> SocialResult:
        self.clock._require_session(world_id)
        state = self.store.load(world_id)
        if state.revision != expected_revision:
            raise RevisionConflict('stale social interaction revision')
        if not isinstance(message_id, str) or not message_id:
            raise ValueError('social message ID required')
        events = [
            DomainEvent('SocialMessageSent', sender, 'local interaction', state.time,
                        {'id': message_id, 'recipient': recipient, 'kind': kind, 'text': text}),
            DomainEvent('SocialMessageReceived', recipient, 'recipient interpreted message', state.time,
                        {'id': message_id}),
        ]
        saved = self.store.append(world_id, 'social:' + message_id, expected_revision,
                                  events, social_authorized=True)
        msg = saved.social_messages[message_id]
        return SocialResult(message_id, msg['reaction'], msg['trust_before'], msg['trust_after'], saved)
