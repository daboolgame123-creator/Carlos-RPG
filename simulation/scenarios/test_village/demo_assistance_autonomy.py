"""Unscripted, locally justified food aid; not an event in Carlos's story."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine


def ev(kind, payload, actor=None):
    return DomainEvent(kind, actor, 'isolated aid fixture', 0, payload)


def run():
    with TemporaryDirectory() as tmp, SQLiteEventStore(Path(tmp)/'living-aid.sqlite') as db:
        db.create_world('test-village')
        setup = [ev('LocationCreated', {'id':'market','name':'Village Market'})]
        for person, food, hunger in (('nora', 1, 85), ('basim', 10, 20)):
            setup.extend([
                ev('EntityCreated', {'id':person,'name':person,'controller':'npc',
                                     'location_id':'market'}),
                ev('NPCConfigured', {'npc_id':person,'role':'villager',
                     'needs':{'fatigue':5,'hunger':hunger,'safety':0},
                     'goals':{'earn':90,'explore':5,'survive':20}}),
            ])
            for resource, qty in (('food',food), ('water',0),
                                  ('labor_units',0), ('investigation_attempts',0)):
                setup.append(ev('ResourceChanged', {
                    'owner_id':person,'resource':resource,'previous':None,
                    'current':qty,'source':'initialization'}))
        db.append('test-village','setup',0,setup,bootstrap=True)
        clock=TimeEngine(db);clock.open_session('test-village')
        engine=LivingWorldEngine(db,clock,assistance_enabled=True)
        early=engine.advance('test-village',seconds=1,command_id='first',
                              expected_revision=db.load('test-village').revision)
        assert early.state.obligations['auto-help:nora:0']['status']=='promised'
        assert early.state.resources['nora']['food']==1
        assert early.state.resources['basim']['food']==10
        later=engine.advance('test-village',seconds=400,command_id='later',
                              expected_revision=early.state.revision)
        assert later.state.obligations['auto-help:nora:0']['status']=='fulfilled'
        assert db.verify('test-village').to_dict()==later.state.to_dict()
        return {
            'before':{'nora_food':1,'basim_food':10},
            'after_request_and_promise':{'nora_food':1,'basim_food':10},
            'after_actual_delivery':{'nora_food':later.state.resources['nora']['food'],
                                     'basim_food':later.state.resources['basim']['food']},
            'total_food':later.state.resources['nora']['food']+later.state.resources['basim']['food'],
            'automated_transitions':list(early.assistance_transitions+later.assistance_transitions),
            'nora_trust_basim':later.state.relations['nora']['basim'],
            'simulated_seconds':later.state.time,
        }


if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
