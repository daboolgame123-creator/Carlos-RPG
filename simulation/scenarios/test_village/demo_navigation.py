"""Autonomous exploration of locally surveyed roads in a disposable test world."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine


def run():
    with TemporaryDirectory() as tmp, SQLiteEventStore(Path(tmp)/'navigation.db') as db:
        db.create_world('demo')
        events = []
        for loc in ('home','forest','crossroads','tower','hidden'):
            events.append(DomainEvent('LocationCreated',None,'fixture',0,{'id':loc,'name':loc}))
        for ident,a,b,seconds in (
            ('home-forest','home','forest',45),
            ('forest-crossroads','forest','crossroads',60),
            ('crossroads-tower','crossroads','tower',75),
            ('tower-hidden','tower','hidden',90)):
            events.append(DomainEvent('RouteCreated',None,'fixture',0,
                {'id':ident,'a':a,'b':b,'seconds':seconds}))
        for ident,interest in (('nora',90),('basim',10)):
            events.extend([
                DomainEvent('EntityCreated',None,'fixture',0,
                    {'id':ident,'name':ident,'controller':'npc','location_id':'home'}),
                DomainEvent('NPCConfigured',None,'fixture',0,
                    {'npc_id':ident,'role':'resident',
                     'needs':{'fatigue':10,'hunger':20,'safety':0},
                     'goals':{'earn':70,'explore':interest,'survive':20}})])
            for counter in ('labor_units','investigation_attempts'):
                events.append(DomainEvent('ResourceChanged',None,'fixture',0,
                    {'owner_id':ident,'resource':counter,'previous':None,
                     'current':0,'source':'initialization'}))
        db.append('demo','setup',0,events,bootstrap=True)
        clock=TimeEngine(db);clock.open_session('demo')
        engine=LivingWorldEngine(db,clock,navigation_enabled=True)
        first=engine.advance('demo',seconds=44,command_id='walk1',
                              expected_revision=db.load('demo').revision)
        assert 'crossroads-tower' not in first.state.navigation['nora']['known_routes']
        second=engine.advance('demo',seconds=136,command_id='walk2',
                               expected_revision=first.state.revision)
        assert second.state.entities['nora']['location_id']=='tower'
        assert db.verify('demo').to_dict()==second.state.to_dict()
        return {'time':second.state.time,'explorer_location':second.state.entities['nora']['location_id'],
                'explorer_visited':list(second.state.navigation['nora']['visited']),
                'explorer_known_roads':list(second.state.navigation['nora']['known_routes']),
                'non_explorer_location':second.state.entities['basim']['location_id']}


if __name__=='__main__':
    print(json.dumps(run(),indent=2,ensure_ascii=False))
