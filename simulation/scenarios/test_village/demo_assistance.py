"""Demonstrate conserved, physically delivered food in a disposable village."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCAssistanceService, NPCSocialService


def ev(kind, data):
    return DomainEvent(kind, None, 'isolated test fixture', 0, data)


def run():
    with TemporaryDirectory() as folder, SQLiteEventStore(Path(folder) / 'assistance.db') as db:
        db.create_world('village')
        init = [ev('LocationCreated', {'id':'square', 'name':'Village Square'})]
        for ident, food in (('nora', 1), ('basim', 8)):
            init.append(ev('EntityCreated', {'id':ident,'name':ident,
                     'location_id':'square','controller':'npc'}))
            init.append(ev('NPCConfigured', {'npc_id':ident,'role':'villager',
                     'needs':{'fatigue':10,'hunger':30,'safety':0},
                     'goals':{'earn':50,'explore':10,'survive':20}}))
            for res, value in (('food',food), ('water',0)):
                init.append(ev('ResourceChanged', {'owner_id':ident,'resource':res,
                        'previous':None,'current':value,'source':'initialization'}))
        db.append('village','setup',0,init,bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('village')
        help_service = NPCAssistanceService(db,clock)
        speech = NPCSocialService(db,clock)
        words = speech.interact('village','basim','nora',kind='offer_help',text='I can help',
                      message_id='only-words',expected_revision=db.load('village').revision)
        spoken_stock = {person:words.state.resources[person]['food'] for person in ('nora','basim')}
        asked = help_service.request('village','nora','basim','food',3,'help-1',
                      expected_revision=db.load('village').revision)
        promised = help_service.respond('village','basim','help-1',accept=True,
                      command_id='promise',expected_revision=asked.state.revision)
        delivered = help_service.deliver('village','basim','help-1',
                      command_id='give-three',expected_revision=promised.state.revision)
        state = delivered.state
        assert db.verify('village').to_dict() == state.to_dict()
        return {
            'before': {'nora_food':1,'basim_food':8},
            'after_words': {'nora_food':spoken_stock['nora'],'basim_food':spoken_stock['basim']},
            'after_delivery': {'nora_food':state.resources['nora']['food'],
                               'basim_food':state.resources['basim']['food']},
            'total_food_before_and_after': [9, sum(state.resources[p]['food'] for p in ('nora','basim'))],
            'obligation_status':state.obligations['help-1']['status'],
            'trust_after_delivery':state.relations['nora']['basim'],
            'world_time':state.time,
        }


if __name__ == '__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
