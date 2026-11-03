"""01-G navigation and knowledge-isolation regression tests."""
import pytest
from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine,
                        NPCNavigationService, shortest_known_route)
from carlos_sim.store import InvalidEvent, RevisionConflict


def event(kind, data, actor=None, at=0):
    return DomainEvent(kind, actor, 'test world', at, data)


def setup(db, *, explore=90, fatigue=5, second=False):
    db.create_world('village')
    events = []
    for loc in ('market', 'forest', 'castle', 'island', 'secret'):
        events.append(event('LocationCreated', {'id':loc, 'name':loc}))
    for rid, a, b, cost in (
        ('market-forest', 'market','forest',50),
        ('forest-castle','forest','castle',70),
        ('castle-island','castle','island',100),
        ('forest-island','forest','island',200),
        ('island-secret','island','secret',30),
    ):
        events.append(event('RouteCreated', {'id':rid, 'a':a,'b':b,'seconds':cost}))
    for ident, here in [('nora','market')] + ([('basim','castle')] if second else []):
        events.extend([
            event('EntityCreated', {'id':ident,'name':ident,'controller':'npc','location_id':here}),
            event('NPCConfigured', {'npc_id':ident,'role':'explorer',
                   'needs':{'fatigue':fatigue,'hunger':20,'safety':0},
                   'goals':{'earn':15,'explore':explore,'survive':25}}),
        ])
        for counter in ('labor_units','investigation_attempts'):
            events.append(event('ResourceChanged', {'owner_id':ident,'resource':counter,
                'previous':None,'current':0,'source':'initialization'}))
    db.append('village','setup',0,events,bootstrap=True)


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path/'navigation.db') as db:
        setup(db)
        clock=TimeEngine(db);clock.open_session('village')
        yield db, clock, NPCNavigationService(db,clock)


def live(db,clock,seconds,command):
    return LivingWorldEngine(db,clock,navigation_enabled=True).advance('village',
        seconds=seconds,command_id=command,expected_revision=db.load('village').revision)


def test_survey_learns_only_incident_routes(world):
    db,clock,service=world
    state=service.survey('village','nora',command_id='look',expected_revision=db.load('village').revision)
    assert state.navigation['nora']['known_routes']==('market-forest',)
    assert state.navigation['nora']['visited']==('market',)
    assert 'forest-castle' not in state.navigation['nora']['known_routes']
    assert 'castle' not in state.navigation['nora']['visited']


def test_no_omniscient_target(world):
    db,clock,service=world
    first=service.survey('village','nora',command_id='look',expected_revision=db.load('village').revision)
    with pytest.raises(InvalidEvent,match='not known'):
        service.target('village','nora','castle',command_id='omniscient',expected_revision=first.revision)
    assert db.load('village').to_dict()==first.to_dict()


def test_select_adjoining_known_destination(world):
    db,clock,service=world
    first=service.survey('village','nora',command_id='look',expected_revision=db.load('village').revision)
    result=service.target('village','nora','forest',command_id='goal',expected_revision=first.revision)
    assert result.path==('market-forest',)


def test_first_autonomous_step_plans_and_moves_without_teleporting(world):
    db,clock,_=world
    result=live(db,clock,10,'start')
    assert result.state.time==10
    assert result.state.entities['nora']['location_id']=='market'
    assert result.state.travels['auto-nav:nora:0']['status']=='traveling'
    assert result.state.navigation['nora']['known_routes']==('market-forest',)
    assert not result.started_action_ids
    assert db.verify('village').to_dict()==result.state.to_dict()


def test_arrival_reveals_more_roads_only_when_at_endpoint(world):
    db,clock,_=world
    first=live(db,clock,49,'before')
    assert 'forest-castle' not in first.state.navigation['nora']['known_routes']
    second=live(db,clock,1,'reach')
    assert second.state.entities['nora']['location_id']=='forest'
    assert set(second.state.navigation['nora']['known_routes'])=={'market-forest','forest-castle','forest-island'}
    assert 'castle-island' not in second.state.navigation['nora']['known_routes']


def test_explorer_reaches_two_new_locations(world):
    db,clock,_=world
    result=live(db,clock,120,'two-hops')
    assert result.state.entities['nora']['location_id']=='castle'
    assert result.state.navigation['nora']['visited']==('castle','forest','market')
    assert 'castle-island' in result.state.navigation['nora']['known_routes']
    assert db.verify('village').to_dict()==result.state.to_dict()


def test_explicit_goal_uses_multihop_known_path(world):
    db,clock,service=world
    live(db,clock,119,'almost-castle')
    arrived=clock.advance('village',seconds=1,command_id='arrive-castle',
                          expected_revision=db.load('village').revision)
    goal=service.target('village','nora','market',command_id='go-home',expected_revision=arrived.state.revision)
    assert goal.path==('forest-castle','market-forest')
    result=live(db,clock,120,'return')
    assert result.state.entities['nora']['location_id']=='market'
    assert result.state.navigation['nora']['target']=='market'


def test_known_shortest_path_is_weighted(world):
    db,clock,_=world
    state=live(db,clock,120,'reveal')
    assert shortest_known_route(state.state,'nora','island')==('castle-island',)


def test_low_exploration_interest_does_not_trigger_travel(tmp_path):
    with SQLiteEventStore(tmp_path/'low.db') as db:
        setup(db,explore=10)
        clock=TimeEngine(db);clock.open_session('village')
        result=live(db,clock,70,'idle')
        assert result.state.travels=={}
        assert result.state.actions


def test_high_fatigue_prevents_unprompted_exploration(tmp_path):
    with SQLiteEventStore(tmp_path/'tired.db') as db:
        setup(db,fatigue=90)
        clock=TimeEngine(db);clock.open_session('village')
        result=live(db,clock,20,'rest')
        assert result.state.travels=={}
        assert result.state.actions['auto:nora:0']['action']=='rest'


def test_opt_in_preserves_previous_living_engine(world):
    db,clock,_=world
    result=LivingWorldEngine(db,clock).advance('village',seconds=30,
        command_id='old',expected_revision=db.load('village').revision)
    assert result.state.navigation=={} and result.state.travels=={}
    assert result.started_action_ids


def test_interrupt_pauses_mid_route(world):
    db,clock,_=world
    clock.schedule_signal('village','warning',due=20,interrupt=True,
                          expected_revision=db.load('village').revision)
    first=live(db,clock,60,'walk')
    assert first.interrupted and first.state.time==20
    assert first.state.travels['auto-nav:nora:0']['status']=='traveling'
    second=live(db,clock,first.remaining_seconds,'continue')
    assert second.state.entities['nora']['location_id']=='forest'


def test_navigation_does_not_advance_offline(world):
    db,clock,_=world
    first=live(db,clock,10,'start')
    clock.close_session('village')
    with pytest.raises(PermissionError):
        live(db,clock,80,'offline')
    assert db.load('village').to_dict()==first.state.to_dict()


def test_replay_restart_preserves_knowledge_and_travel(tmp_path):
    path=tmp_path/'save.db'
    with SQLiteEventStore(path) as db:
        setup(db)
        clock=TimeEngine(db);clock.open_session('village')
        live(db,clock,20,'first')
        db.snapshot('village')
    with SQLiteEventStore(path) as db:
        assert db.verify('village').navigation['nora']['known_routes']==('market-forest',)
        clock=TimeEngine(db);clock.open_session('village')
        done=live(db,clock,100,'resume')
        assert done.state.entities['nora']['location_id']=='castle'
        assert db.verify('village').to_dict()==done.state.to_dict()


def test_direct_navigation_event_rejected_without_capability(world):
    db,clock,_=world
    s=db.load('village')
    with pytest.raises(InvalidEvent,match='trusted movement'):
        db.append('village','cheat',s.revision,[event('NPCNavigationSurveyed',{'npc_id':'nora'},actor='nora')])


def test_stale_target_revision_rejected(world):
    db,clock,service=world
    before=db.load('village')
    service.survey('village','nora',command_id='known',expected_revision=before.revision)
    with pytest.raises(RevisionConflict):
        service.target('village','nora','forest',command_id='stale',expected_revision=before.revision)


def test_determinism_across_two_isolated_worlds(tmp_path):
    outputs=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path/f'{i}.db') as db:
            setup(db)
            clock=TimeEngine(db);clock.open_session('village')
            out=live(db,clock,150,'explore')
            outputs.append((out.state.to_dict(),out.fired_ids))
    assert outputs[0]==outputs[1]


def test_budget_failure_rolls_back_completely(world):
    from carlos_sim import AdvanceLimitExceeded
    db,clock,_=world
    prior=db.load('village').to_dict()
    with pytest.raises(AdvanceLimitExceeded):
        LivingWorldEngine(db,clock,navigation_enabled=True,max_events_per_advance=2).advance(
            'village',seconds=200,command_id='too-big',expected_revision=prior['revision'])
    assert db.load('village').to_dict()==prior


def test_navigation_knowledge_is_private(tmp_path):
    with SQLiteEventStore(tmp_path/'two.db') as db:
        setup(db,second=True)
        c=TimeEngine(db);c.open_session('village')
        nav=NPCNavigationService(db,c)
        state=nav.survey('village','nora',command_id='survey',expected_revision=db.load('village').revision)
        assert 'basim' not in state.navigation
        with pytest.raises(InvalidEvent):
            nav.target('village','basim','forest',command_id='borrow',expected_revision=state.revision)


def test_preexisting_decision_takes_priority_over_navigation(world):
    from carlos_sim import NPCService
    db,clock,_=world
    NPCService(db,clock).decide('village','nora',command_id='prior',
                                expected_revision=db.load('village').revision)
    result=live(db,clock,10,'prefer-prior')
    assert result.started_action_ids==('auto:nora:0',)
    assert result.state.travels=={}


def test_busy_npc_cannot_survey(world):
    from carlos_sim import NPCService, NPCActionService
    db,clock,service=world
    NPCService(db,clock).decide('village','nora',command_id='prior',
                                expected_revision=db.load('village').revision)
    NPCActionService(db,clock).start('village','nora','action',
                                     expected_revision=db.load('village').revision)
    before=db.load('village')
    with pytest.raises(InvalidEvent,match='busy'):
        service.survey('village','nora',command_id='busy',expected_revision=before.revision)
    assert db.load('village').to_dict()==before.to_dict()


def test_repeat_survey_creates_no_unnecessary_event(world):
    db,clock,service=world
    first=service.survey('village','nora',command_id='once',expected_revision=db.load('village').revision)
    second=service.survey('village','nora',command_id='again',expected_revision=first.revision)
    assert first.revision==second.revision


def test_manual_survey_requires_active_session(world):
    db,clock,service=world
    clock.close_session('village')
    with pytest.raises(PermissionError):
        service.survey('village','nora',command_id='offline',expected_revision=db.load('village').revision)


def test_actor_cannot_impersonate_another_npc_during_survey(world):
    db,clock,_=world
    state=db.load('village')
    with pytest.raises(InvalidEvent):
        db.append('village','impersonate',state.revision,[
            event('NPCNavigationSurveyed',{'npc_id':'nora'},actor='basim')
        ],movement_authorized=True)


def test_target_cannot_be_set_without_road_knowledge(world):
    db,clock,service=world
    with pytest.raises(InvalidEvent):
        service.target('village','nora','forest',command_id='unknown',
                       expected_revision=db.load('village').revision)


def test_paused_survey_does_not_consume_command_identifier(world):
    db,clock,service=world
    before=db.load('village')
    clock.close_session('village')
    with pytest.raises(PermissionError):
        service.survey('village','nora',command_id='recover',expected_revision=before.revision)
    clock.open_session('village')
    result=service.survey('village','nora',command_id='recover',expected_revision=before.revision)
    assert result.navigation['nora']['visited']==('market',)
