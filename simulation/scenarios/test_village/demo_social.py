"""An isolated social interaction sequence; not a Carlos story event."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCSocialService


def run():
    with TemporaryDirectory() as directory, SQLiteEventStore(Path(directory) / 'test.sqlite') as db:
        db.create_world('demo')
        init = [DomainEvent('LocationCreated', None, 'fixture', 0,
                            {'id': 'market', 'name': 'Market'})]
        for name in ('nora', 'basim'):
            init.extend([
                DomainEvent('EntityCreated', None, 'fixture', 0,
                    {'id': name, 'name': name, 'location_id': 'market', 'controller': 'npc'}),
                DomainEvent('NPCConfigured', None, 'fixture', 0,
                    {'npc_id': name, 'role': 'resident',
                     'needs': {'fatigue': 5, 'hunger': 10, 'safety': 0},
                     'goals': {'earn': 20, 'explore': 10, 'survive': 20}}),
            ])
        db.append('demo', 'setup', 0, init, bootstrap=True)
        clock = TimeEngine(db); clock.open_session('demo')
        social = NPCSocialService(db, clock)
        log = []
        for i, (who, recipient, kind) in enumerate([
            ('nora', 'basim', 'greeting'),
            ('nora', 'basim', 'threat'),
            ('nora', 'basim', 'request_help'),
            ('basim', 'nora', 'offer_help'),
        ]):
            event = social.interact('demo', who, recipient, kind=kind,
                   text=kind, message_id=f'exchange-{i}',
                   expected_revision=db.load('demo').revision)
            log.append({'sender': who, 'recipient': recipient, 'kind': kind,
                        'reaction': event.reaction, 'trust_after': event.trust_after})
        assert db.verify('demo').to_dict() == db.load('demo').to_dict()
        return {'events': log, 'relations': db.load('demo').to_dict()['relations']}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
