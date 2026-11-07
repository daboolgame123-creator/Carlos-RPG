"""01-X: event-backed player-visible evidence, not hidden NPC world state."""
from __future__ import annotations

import json
from typing import Any

from .domain import DomainEvent, WorldState
from .store import SQLiteEventStore
from .movement import _visible, _in_transit


def validate_player_perception_event(state: dict[str, Any], event: DomainEvent,
                                     *, movement_authorized: bool,
                                     social_authorized: bool) -> None:
    """Validate exactly what is local and recorded at this simulation tick."""
    p = event.data
    if event.event_type == 'PlayerObserved':
        who = event.actor_id
        if (not movement_authorized or who not in state['entities']
                or state['entities'][who]['controller'] != 'player'):
            raise ValueError('player observation requires trusted player perception')
        place = state['entities'][who]['location_id']
        if _in_transit(state, who):
            raise ValueError('cannot observe while travelling')
        if (set(p) != {'location_id', 'occupants'}
                or p['location_id'] != place
                or not isinstance(p['occupants'], (list, tuple))
                or list(p['occupants']) != _visible(state, place)):
            raise ValueError('player observation must match actual local presence')
    elif event.event_type == 'PlayerHearsayReceived':
        speaker = event.actor_id
        if not social_authorized or speaker not in state['npcs']:
            raise ValueError('player hearsay requires trusted NPC speech')
        if set(p) != {'player_id', 'key', 'text'}:
            raise ValueError('invalid player hearsay fields')
        player = p['player_id']
        if (not isinstance(player, str) or player not in state['entities']
                or state['entities'][player]['controller'] != 'player'
                or _in_transit(state, player) or _in_transit(state, speaker)
                or state['entities'][speaker]['location_id'] !=
                    state['entities'][player]['location_id']):
            raise ValueError('player hearsay requires present, co-located participants')
        from .knowledge import is_food_key, parse_food_claim, is_observation_source
        if not is_food_key(p['key']) or not isinstance(p['text'], str):
            raise ValueError('only bounded food claims can be shared in 01-X')
        claim = state['npcs'][speaker]['beliefs'].get(p['key'])
        if claim is None or claim['text'] != p['text']:
            raise ValueError('NPC cannot report a claim not in its own knowledge')
        parsed = parse_food_claim(p['text'])
        if parsed is None or parsed[1] > state['time']:
            raise ValueError('malformed or future-dated food hearsay')
        if (not is_observation_source(claim['source'])
                and claim['received_at'] >= state['time']):
            raise ValueError('hearsay cannot be forwarded in its arrival tick')
    else:
        raise ValueError('unsupported player perception event')


def recall_player_events(store: SQLiteEventStore, state: WorldState,
                         player_id: str) -> dict[str, Any]:
    """Read-only verified sightings, hearsay and bounded witnessed meals.

    A meal requires the immediately preceding, actor-bound PlayerObserved
    in the SAME authorized wait command at the SAME physical site/tick.
    A remote consumption is never memory merely because it exists in SQLite.
    """
    verified = store.verify(state.world_id)
    if verified.revision != state.revision:
        raise ValueError('world changed while reading player memory')
    visited: dict[str, dict[str, Any]] = {}
    heard: list[dict[str, Any]] = []
    witnessed: list[dict[str, Any]] = []
    pending_witness: tuple[str, DomainEvent] | None = None
    rows = store.db.execute(
        'SELECT payload, command_id FROM events WHERE world_id=? ORDER BY seq',
        (state.world_id,))
    for raw, command_id in rows:
        obj = json.loads(raw)
        if obj.get('event_type') not in ('PlayerObserved', 'PlayerHearsayReceived',
                                         'NPCFoodConsumed'):
            pending_witness = None
            continue
        evt = DomainEvent.from_dict(obj)
        if evt.event_type == 'NPCFoodConsumed':
            if pending_witness is not None and pending_witness[0] == command_id:
                observed = pending_witness[1]
                meal = state.consumptions.get(evt.data['id'])
                if (meal is not None and meal['npc_id'] == evt.actor_id
                        and evt.actor_id == evt.data['npc_id']
                        and meal['consumed_at'] == evt.time == observed.time
                        and meal['location_id'] == observed.data['location_id']
                        and evt.actor_id in observed.data['occupants']):
                    witnessed.append({
                        'actor_id': evt.actor_id, 'activity': 'eating',
                        'location_id': meal['location_id'], 'at': evt.time,
                    })
                    # Only the most recent 20 local memories are projected.
                    if len(witnessed) > 20:
                        witnessed.pop(0)
            pending_witness = None
            continue
        pending_witness = None
        if evt.event_type == 'PlayerObserved' and evt.actor_id == player_id:
            place = evt.data['location_id']
            visited[place] = {
                'location_id': place, 'location_name': state.locations[place]['name'],
                'observed_at': evt.time,
                'occupants': tuple({
                    'id': who, 'name': state.entities[who]['name']}
                    for who in evt.data['occupants']),
            }
            if (command_id.startswith('player-wait:')
                    and evt.cause == 'player witnessed a nearby NPC eating'):
                pending_witness = (command_id, evt)
        elif (evt.event_type == 'PlayerHearsayReceived'
              and evt.data['player_id'] == player_id):
            heard.append({
                'speaker_id': evt.actor_id,
                'speaker_name': state.entities[evt.actor_id]['name'],
                'key': evt.data['key'], 'claim': evt.data['text'],
                'heard_at': evt.time, 'status': 'unverified',
            })
    memory = {'observations': tuple(sorted(
                  visited.values(), key=lambda x: (x['observed_at'], x['location_id']))),
              'hearsay': tuple(heard)}
    if witnessed:
        memory['witnessed_events'] = tuple(witnessed)
    return memory
