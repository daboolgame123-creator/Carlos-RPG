"""Demonstrate repeated autonomous action cycles in a disposable five-NPC village."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine


def run(seconds: int = 720) -> dict:
    data = json.loads(Path(__file__).with_name('characters.json').read_text(encoding='utf-8'))
    with TemporaryDirectory() as temp, SQLiteEventStore(Path(temp) / 'village.sqlite') as db:
        db.create_world('test-village')
        events = [DomainEvent('LocationCreated', None, 'test setup', 0, data['location'])]
        for npc in data['npcs']:
            entity = {'id': npc['id'], 'name': npc['name'],
                      'location_id': 'village', 'controller': 'npc'}
            events.extend([
                DomainEvent('EntityCreated', None, 'test setup', 0, entity),
                DomainEvent('NPCConfigured', None, 'test setup', 0,
                            {'npc_id': npc['id'], 'role': npc['role'],
                             'needs': npc['needs'], 'goals': npc['goals']}),
            ])
            for counter in ('labor_units', 'investigation_attempts'):
                events.append(DomainEvent('ResourceChanged', None, 'test initialization', 0,
                              {'owner_id': npc['id'], 'resource': counter,
                               'previous': None, 'current': 0, 'source': 'initialization'}))
        db.append('test-village', 'bootstrap', 0, events, bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('test-village')
        result = LivingWorldEngine(db, clock).advance('test-village', seconds=seconds,
                         command_id='player-explicit-time',
                         expected_revision=db.load('test-village').revision)
        assert db.verify('test-village').to_dict() == result.state.to_dict()
        state = result.state
        return {
            'elapsed': result.elapsed_seconds,
            'started': len(result.started_action_ids),
            'completed': len(result.completed_action_ids),
            'people': {npc['name']: {
                'needs': dict(state.npcs[npc['id']]['needs']),
                'last_action': state.npcs[npc['id']]['last_decision']['action'],
                'completed_actions': sum(1 for a in state.actions.values()
                    if a['npc_id'] == npc['id'] and a['status'] == 'completed')}
                for npc in data['npcs']},
        }


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, ensure_ascii=False))
