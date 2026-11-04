"""Isolated baseline metabolism demonstration, not Carlos story canon."""
import json
from tempfile import TemporaryDirectory
from pathlib import Path
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine


def ev(kind, data):
    return DomainEvent(kind, None, 'isolated survival fixture', 0, data)


def run():
    with TemporaryDirectory() as folder, SQLiteEventStore(Path(folder) / 'survival.db') as db:
        db.create_world('village')
        db.append('village', 'setup', 0, [
            ev('LocationCreated', {'id': 'square', 'name': 'Square'}),
            ev('EntityCreated', {'id': 'nora', 'name': 'Nora',
                                 'location_id': 'square', 'controller': 'npc'}),
            ev('NPCConfigured', {'npc_id': 'nora', 'role': 'villager',
                'needs': {'hunger': 20, 'fatigue': 5, 'safety': 0},
                'goals': {'earn': 30, 'explore': 5, 'survive': 50}}),
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('village')
        changes = []
        for seconds in (299, 1, 300):
            state = db.load('village')
            advanced = db.append('village', f'elapsed-{state.time}', state.revision,
                [DomainEvent('TimeAdvanced', None, 'explicit play time',
                  state.time + seconds, {'from': state.time,
                    'to': state.time + seconds})],
                clock_authorized=True, survival_authorized=True)
            changes.append({
                'time': advanced.time,
                'hunger': advanced.npcs['nora']['needs']['hunger'],
                'fatigue': advanced.npcs['nora']['needs']['fatigue'],
                'residual': dict(advanced.survival_progress['nora']),
            })
        assert db.verify('village').to_dict() == advanced.to_dict()
        return {'world': 'fictional test world', 'samples': changes,
                'verified_replay': True}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
