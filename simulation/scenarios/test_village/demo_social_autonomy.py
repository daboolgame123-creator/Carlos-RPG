"""A fictional social scene produced by autonomous rules, not a scripted story."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine, NPCSocialService


def event(kind, data):
    return DomainEvent(kind, None, 'test setup', 0, data)


def run() -> dict:
    with TemporaryDirectory() as directory, SQLiteEventStore(Path(directory) / 'social.sqlite') as db:
        db.create_world('test-village')
        events = [event('LocationCreated', {'id': 'village', 'name': 'Village Square'})]
        for who, hunger in (('aaron', 80), ('bella', 10), ('zora', 20)):
            events.extend([
                event('EntityCreated', {'id': who, 'name': who, 'controller': 'npc',
                                        'location_id': 'village'}),
                event('NPCConfigured', {'npc_id': who, 'role': 'villager',
                    'needs': {'fatigue': 5, 'hunger': hunger, 'safety': 10},
                    'goals': {'earn': 80, 'explore': 10, 'survive': 30}}),
            ])
            for metric in ('labor_units', 'investigation_attempts'):
                events.append(event('ResourceChanged', {'owner_id': who, 'resource': metric,
                    'previous': None, 'current': 0, 'source': 'initialization'}))
        db.append('test-village', 'setup', 0, events, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('test-village')
        # Previously witnessed greeting creates an acquaintance; it does not
        # automatically transfer trust back to the speaker.
        NPCSocialService(db, clock).interact('test-village', 'bella', 'aaron',
            kind='greeting', text='Hello!', message_id='prior-greeting',
            expected_revision=db.load('test-village').revision)
        result = LivingWorldEngine(db, clock, social_enabled=True).advance(
            'test-village', seconds=360, command_id='explicit-player-time',
            expected_revision=db.load('test-village').revision)
        assert db.verify('test-village').to_dict() == result.state.to_dict()
        messages = [{'sender': m['sender'], 'recipient': m['recipient'], 'kind': m['kind'],
                     'reaction': m['reaction'], 'time': m['sent_at']} for m in result.state.social_messages.values()]
        return {'simulated_seconds': result.elapsed_seconds,
                'automatic_message_ids': list(result.social_message_ids),
                'messages': messages,
                'relations': result.state.to_dict()['relations'],
                'completed_actions': len(result.completed_action_ids)}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
