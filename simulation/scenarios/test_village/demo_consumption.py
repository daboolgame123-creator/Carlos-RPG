"""Separate test world: real food aid can be eaten, without creating food."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        LivingWorldEngine, NPCConsumptionService)


def ev(kind, data, actor=None):
    return DomainEvent(kind, actor, 'isolated consumption fixture', 0, data)


def run() -> dict:
    with TemporaryDirectory() as temp, SQLiteEventStore(Path(temp)/'meals.sqlite') as db:
        db.create_world('demo')
        setup=[ev('LocationCreated',{'id':'market','name':'Test village market'})]
        for who,food,hunger in (('nora',0,95),('basim',10,20)):
            setup.extend([
                ev('EntityCreated',{'id':who,'name':who,'controller':'npc','location_id':'market'}),
                ev('NPCConfigured',{'npc_id':who,'role':'villager',
                    'needs':{'fatigue':5,'hunger':hunger,'safety':0},
                    'goals':{'earn':90,'explore':5,'survive':20}}),
            ])
            for resource,quantity in (('food',food),('water',0),('labor_units',0),('investigation_attempts',0)):
                setup.append(ev('ResourceChanged',{'owner_id':who,'resource':resource,
                    'previous':None,'current':quantity,'source':'initialization'}))
        db.append('demo','setup',0,setup,bootstrap=True)
        clock=TimeEngine(db);clock.open_session('demo')
        world=LivingWorldEngine(db,clock,assistance_enabled=True,consumption_enabled=True)
        first=world.advance('demo',seconds=1,command_id='initial',expected_revision=db.load('demo').revision)
        assert first.state.resources['nora']['food']==0
        assert first.state.obligations['auto-help:nora:0']['status']=='promised'
        second=world.advance('demo',seconds=400,command_id='continue',expected_revision=first.state.revision)
        assert second.state.obligations['auto-help:nora:0']['status']=='fulfilled'
        assert second.state.consumptions
        assert db.verify('demo').to_dict()==second.state.to_dict()
        nora_meals=[dict(meal) for meal in second.state.consumptions.values() if meal['npc_id']=='nora']
        transfer=second.state.obligations['auto-help:nora:0']['transfer']
        assert transfer['requester_after']==3
        return {
            'elapsed_simulation_seconds':second.state.time,
            'promised_without_transfer_at_second_zero':first.state.resources['nora']['food']==0,
            'physical_transfer':dict(transfer),
            'nora_meals':nora_meals,
            'nora_current_food':second.state.resources['nora']['food'],
            'nora_current_hunger':second.state.npcs['nora']['needs']['hunger'],
            'world_replay_verified':True,
        }


if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
