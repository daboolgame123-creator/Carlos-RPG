"""Phase 01-F: topology, time-dependent NPC travel and scoped perception."""
import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine,
                        NPCMovementService, perceive_local)
from carlos_sim.store import InvalidEvent, RevisionConflict


def ev(kind, data, actor=None, time=0):
    return DomainEvent(kind, actor, 'test setup', time, data)


def build(db):
    db.create_world('village')
    events = [ev('LocationCreated', {'id':'market','name':'Market'}),
              ev('LocationCreated', {'id':'forest','name':'Forest'}),
              ev('LocationCreated', {'id':'castle','name':'Castle'}),
              ev('LocationCreated', {'id':'island','name':'Island'}),
              ev('RouteCreated', {'id':'path', 'a':'market','b':'forest','seconds':120}),
              ev('RouteCreated', {'id':'road', 'a':'forest','b':'castle','seconds':80})]
    for ident, location, controller in (
        ('nora','market','npc'),('basim','market','npc'),('guard','forest','npc'),
        ('king','castle','npc'),('carlos','market','player')):
        events.append(ev('EntityCreated',{'id':ident,'name':ident,'location_id':location,
                                         'controller':controller}))
        if controller=='npc':
            events.append(ev('NPCConfigured', {'npc_id':ident,'role':'worker',
                'needs':{'fatigue':5,'hunger':20,'safety':0},
                'goals':{'earn':90,'explore':5,'survive':30}}))
            for metric in ('labor_units','investigation_attempts'):
                events.append(ev('ResourceChanged',{'owner_id':ident,'resource':metric,
                    'previous':None,'current':0,'source':'initialization'}))
    return db.append('village','seed',0,events,bootstrap=True)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path/'world.sqlite') as db:
        build(db)
        clock=TimeEngine(db);clock.open_session('village')
        yield db, clock, NPCMovementService(db,clock)


def test_only_same_location_visible_and_observation_is_snapshotted(village):
    db,_,movement=village
    state=movement.observe('village','nora',command_id='observe',expected_revision=db.load('village').revision)
    obs=perceive_local(state,'nora')
    assert obs=={'location_id':'market','at':0,'occupants':['basim','carlos','nora']}
    assert 'guard' not in obs['occupants'] and 'king' not in obs['occupants']
    assert perceive_local(state,'guard') is None
    assert state.observations['nora'].get('forest') is None


def test_route_duration_and_location_change_only_on_arrival(village):
    db,clock,movement=village
    trip=movement.start('village','nora','path','trip1',expected_revision=db.load('village').revision)
    assert trip.due==120 and trip.state.entities['nora']['location_id']=='market'
    mid=clock.advance('village',seconds=119,command_id='before',expected_revision=trip.state.revision)
    assert mid.state.entities['nora']['location_id']=='market'
    done=clock.advance('village',seconds=1,command_id='arrival',expected_revision=mid.state.revision)
    assert done.state.entities['nora']['location_id']=='forest'
    assert done.state.travels['trip1']['status']=='arrived'
    assert done.state.observations['nora']['forest']=={'at':120,'occupants':('guard','nora')}
    assert db.verify('village').to_dict()==done.state.to_dict()


def test_no_instant_transport_or_nonadjacent_travel(village):
    db,clock,movement=village
    old=db.load('village').to_dict()
    with pytest.raises(ValueError,match='endpoint'):
        movement.start('village','nora','road','teleport',expected_revision=old['revision'])
    assert db.load('village').to_dict()==old


def test_two_hop_travel_requires_separate_actions(village):
    db,clock,movement=village
    first=movement.start('village','nora','path','t1',expected_revision=db.load('village').revision)
    result=clock.advance('village',seconds=120,command_id='first',expected_revision=first.state.revision)
    second=movement.start('village','nora','road','t2',expected_revision=result.state.revision)
    assert second.due==200
    final=clock.advance('village',seconds=80,command_id='second',expected_revision=second.state.revision)
    assert final.state.entities['nora']['location_id']=='castle'
    assert perceive_local(final.state,'nora')['occupants']==['king','nora']
    assert db.verify('village').to_dict()==final.state.to_dict()


def test_traveler_not_allowed_second_trip(village):
    db,_,movement=village
    started=movement.start('village','nora','path','one',expected_revision=db.load('village').revision)
    with pytest.raises(InvalidEvent,match='already traveling'):
        movement.start('village','nora','path','two',expected_revision=started.state.revision)
    assert db.load('village').travels['one']['status']=='traveling'


def test_traveler_cannot_observe_in_transit(village):
    db,_,movement=village
    started=movement.start('village','nora','path','one',expected_revision=db.load('village').revision)
    with pytest.raises(InvalidEvent,match='transit'):
        movement.observe('village','nora',command_id='in-transit',expected_revision=started.state.revision)


def test_cannot_cancel_active_travel_signal(village):
    db,clock,movement=village
    started=movement.start('village','nora','path','one',expected_revision=db.load('village').revision)
    with pytest.raises(InvalidEvent,match='cannot cancel'):
        clock.cancel('village','npc-travel:one',command_id='cancel',expected_revision=started.state.revision)


def test_cannot_start_travel_while_action_running(village):
    from carlos_sim import NPCService, NPCActionService
    db,clock,movement=village
    NPCService(db,clock).decide('village','nora',command_id='choose',expected_revision=db.load('village').revision)
    NPCActionService(db,clock).start('village','nora','work',expected_revision=db.load('village').revision)
    with pytest.raises(InvalidEvent,match='busy'):
        movement.start('village','nora','path','conflict',expected_revision=db.load('village').revision)


def test_existing_travel_blocks_autonomous_npc_action(village):
    db,clock,movement=village
    trip=movement.start('village','nora','path','trip',expected_revision=db.load('village').revision)
    result=LivingWorldEngine(db,clock).advance('village',seconds=60,command_id='step',expected_revision=trip.state.revision)
    assert not any(a['npc_id']=='nora' for a in result.state.actions.values())
    assert any(a['npc_id']=='basim' for a in result.state.actions.values())
    result=LivingWorldEngine(db,clock).advance('village',seconds=60,command_id='step2',expected_revision=result.state.revision)
    assert result.state.entities['nora']['location_id']=='forest'
    assert any(a['npc_id']=='nora' for a in result.state.actions.values())


def test_movement_start_rejected_when_session_closed(village):
    db,clock,movement=village
    clock.close_session('village')
    with pytest.raises(PermissionError):
        movement.start('village','nora','path','offline',expected_revision=db.load('village').revision)
    assert db.load('village').time==0


def test_player_not_controlled_by_npc_movement(village):
    db,clock,movement=village
    with pytest.raises(ValueError,match='NPC'):
        movement.start('village','carlos','path','player',expected_revision=db.load('village').revision)
    assert db.load('village').entities['carlos']['location_id']=='market'


def test_orphan_travel_schedule_rollback(village):
    db,clock,movement=village
    state=db.load('village')
    orphan=ev('ScheduledEventCreated',{'id':'npc-travel:ghost','due':50,
        'order':state.next_schedule_order,'kind':'signal',
        'payload':{'__npc_travel_id':'ghost'},'interrupt':False})
    with pytest.raises(InvalidEvent,match='orphaned'):
        db.append('village','ghost',state.revision,[orphan],movement_authorized=True)
    assert db.load('village').to_dict()==state.to_dict()
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='ghost'").fetchone()[0]==0


def test_reserved_travel_signal_requires_capability(village):
    db,clock,movement=village
    state=db.load('village')
    orphan=ev('ScheduledEventCreated',{'id':'npc-travel:ghost','due':50,
        'order':state.next_schedule_order,'kind':'signal',
        'payload':{'__npc_travel_id':'ghost'},'interrupt':False})
    with pytest.raises(InvalidEvent,match='movement capability'):
        db.append('village','ghost',state.revision,[orphan])


def test_stale_revision_and_duplicate_travel_id(village):
    db,clock,movement=village
    old=db.load('village')
    trip=movement.start('village','nora','path','one',expected_revision=old.revision)
    with pytest.raises(RevisionConflict):
        movement.start('village','basim','path','other',expected_revision=old.revision)
    from carlos_sim.store import DuplicateCommand
    with pytest.raises(DuplicateCommand):
        movement.start('village','basim','path','one',expected_revision=trip.state.revision)


def test_explicit_perception_and_travel_are_replayed_after_restart(tmp_path):
    path=tmp_path/'restart.sqlite'
    with SQLiteEventStore(path) as db:
        build(db)
        c=TimeEngine(db);c.open_session('village')
        svc=NPCMovementService(db,c)
        svc.observe('village','nora',command_id='look',expected_revision=db.load('village').revision)
        svc.start('village','nora','path','trip',expected_revision=db.load('village').revision)
        db.snapshot('village')
    with SQLiteEventStore(path) as db:
        assert db.verify('village').travels['trip']['status']=='traveling'
        c=TimeEngine(db)
        with pytest.raises(PermissionError):
            c.advance('village',seconds=120,command_id='offline',expected_revision=db.load('village').revision)
        c.open_session('village')
        end=c.advance('village',seconds=120,command_id='finish',expected_revision=db.load('village').revision)
        assert end.state.entities['nora']['location_id']=='forest'
        assert db.verify('village').to_dict()==end.state.to_dict()


def test_local_perception_is_explicit_and_stale_after_move(village):
    db,clock,movement=village
    movement.observe('village','basim',command_id='look',expected_revision=db.load('village').revision)
    move=movement.start('village','nora','path','trip',expected_revision=db.load('village').revision)
    done=clock.advance('village',seconds=120,command_id='finish',expected_revision=move.state.revision)
    prior=perceive_local(done.state,'basim')
    assert prior['at']==0 and 'nora' in prior['occupants']  # historical sighting, not live position
    updated=movement.observe('village','basim',command_id='look-again',expected_revision=done.state.revision)
    assert 'nora' not in perceive_local(updated,'basim')['occupants']


def test_invalid_route_and_attempted_remote_observation_rejected(village):
    db,clock,movement=village
    current=db.load('village')
    with pytest.raises(InvalidEvent):
        db.append('village','fake-route',current.revision,[ev('RouteCreated',
                  {'id':'bad','a':'market','b':'island','seconds':0})],bootstrap=True)
    with pytest.raises(InvalidEvent):
        db.append('village','fake-observation',current.revision,[ev('NPCObserved',
                  {'npc_id':'nora','location_id':'castle'},actor='nora')],movement_authorized=True)


def test_route_data_survives_snapshot(village):
    db,clock,movement=village
    db.snapshot('village')
    assert db.verify('village').routes['path']['seconds']==120
    assert db.load('village').routes['road']['seconds']==80


def test_two_npcs_arrive_in_deterministic_order(village):
    db,clock,movement=village
    first=movement.start('village','nora','path','one',expected_revision=db.load('village').revision)
    second=movement.start('village','basim','path','two',expected_revision=first.state.revision)
    done=clock.advance('village',seconds=120,command_id='both',expected_revision=second.state.revision)
    assert done.fired_ids==('npc-travel:one','npc-travel:two')
    assert done.state.entities['nora']['location_id']=='forest'
    assert done.state.entities['basim']['location_id']=='forest'
    assert db.verify('village').to_dict()==done.state.to_dict()
