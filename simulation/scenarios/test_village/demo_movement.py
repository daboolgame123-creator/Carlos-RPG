"""Purely fictional travel/perception fixture (no Carlos narrative changes)."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        NPCMovementService, perceive_local)


def run():
    with TemporaryDirectory() as directory, SQLiteEventStore(Path(directory) / 'travel.sqlite') as db:
        db.create_world('travel-demo')
        e = lambda kind, payload: DomainEvent(kind, None, 'demo setup', 0, payload)
        init = [e('LocationCreated', {'id':'square','name':'Square'}),
                e('LocationCreated', {'id':'bridge','name':'Bridge'}),
                e('LocationCreated', {'id':'courtyard','name':'Courtyard'}),
                e('RouteCreated', {'id':'square-bridge','a':'square','b':'bridge','seconds':90}),
                e('RouteCreated', {'id':'bridge-courtyard','a':'bridge','b':'courtyard','seconds':60})]
        for ident, loc in [('nora','square'),('basim','square'),('guard','bridge')]:
            init.extend([e('EntityCreated',{'id':ident,'name':ident,'controller':'npc','location_id':loc}),
                         e('NPCConfigured',{'npc_id':ident,'role':'resident',
                             'needs':{'fatigue':10,'hunger':10,'safety':0},
                             'goals':{'earn':10,'explore':10,'survive':10}})])
        db.append('travel-demo','init',0,init,bootstrap=True)
        clock=TimeEngine(db);clock.open_session('travel-demo')
        movement=NPCMovementService(db,clock)
        state=movement.observe('travel-demo','nora',command_id='look',expected_revision=db.load('travel-demo').revision)
        initial=perceive_local(state,'nora')
        start=movement.start('travel-demo','nora','square-bridge','journey',expected_revision=state.revision)
        clock.schedule_signal('travel-demo','stop-and-look',due=40,interrupt=True,
                              expected_revision=start.state.revision)
        result=clock.advance('travel-demo',seconds=90,command_id='walk',
                             expected_revision=db.load('travel-demo').revision)
        assert result.interrupted and result.state.time==40 and result.remaining_seconds==50
        arrived=clock.advance('travel-demo',seconds=result.remaining_seconds,
                              command_id='continue',expected_revision=result.state.revision)
        final=perceive_local(arrived.state,'nora')
        assert arrived.state.entities['nora']['location_id']=='bridge'
        assert db.verify('travel-demo').to_dict()==arrived.state.to_dict()
        return {'start': initial, 'arrival': final, 'interrupted_at':40,
                'arrival_at': arrived.state.time, 'travel_status':arrived.state.travels['journey']['status']}


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=2))
