"""Five test NPCs work concurrently; this does NOT change Carlos story."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, NPCService, SQLiteEventStore, TimeEngine
from carlos_sim.actions import NPCActionService, DURATIONS


def run():
    fixture = json.loads(Path(__file__).with_name('characters.json').read_text(encoding='utf-8'))
    with TemporaryDirectory() as directory, SQLiteEventStore(Path(directory) / 'actions.sqlite') as db:
        db.create_world('demo')
        initial = [DomainEvent('LocationCreated', None, 'fixture', 0, fixture['location'])]
        for npc in fixture['npcs']:
            ident = npc['id']
            initial.extend([
                DomainEvent('EntityCreated', None, 'fixture', 0,
                            {'id':ident,'name':npc['name'],'location_id':'village','controller':'npc'}),
                DomainEvent('NPCConfigured', None, 'fixture', 0,
                            {'npc_id':ident, 'role':npc['role'],'needs':npc['needs'],'goals':npc['goals']}),
            ])
            for metric in ('labor_units', 'investigation_attempts'):
                initial.append(DomainEvent('ResourceChanged', None, 'test initialization', 0,
                               {'owner_id':ident,'resource':metric,'previous':None,
                                'current':0,'source':'initialization'}))
        db.append('demo','setup',0,initial,bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('demo')
        planner = NPCService(db, clock)
        executor = NPCActionService(db, clock)
        for npc in fixture['npcs']:
            ident = npc['id']
            planner.decide('demo',ident,command_id='plan:'+ident,expected_revision=db.load('demo').revision)
            executor.start('demo',ident,'action:'+ident,expected_revision=db.load('demo').revision)
        duration = max(DURATIONS.values())
        clock.advance('demo',seconds=duration,command_id='simulated-work',expected_revision=db.load('demo').revision)
        state = db.verify('demo')
        return [(n['id'],state.actions['action:'+n['id']]['action'],
                 state.actions['action:'+n['id']]['status'],
                 state.npcs[n['id']]['needs']['fatigue'],
                 state.resources[n['id']]['labor_units']) for n in fixture['npcs']]


if __name__ == '__main__':
    for ident, action, status, fatigue, work_units in run():
        print(f'{ident}: {action}; {status}; fatigue={fatigue}; labor_units={work_units}')
