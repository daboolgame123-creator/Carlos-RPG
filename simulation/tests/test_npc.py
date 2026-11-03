import pytest
from carlos_sim import SQLiteEventStore, DomainEvent, NPCService, choose_action, TimeEngine
from carlos_sim.store import InvalidEvent, RevisionConflict


def event(kind, data, *, actor=None, time=0):
    return DomainEvent(kind, actor, 'fixture', time, data)


def config(ident, role='merchant', *, fatigue=5, hunger=20, safety=0, earn=60, explore=5, survive=25):
    return event('NPCConfigured', {'npc_id': ident, 'role': role,
                 'needs': {'fatigue': fatigue, 'hunger': hunger, 'safety': safety},
                 'goals': {'earn': earn, 'explore': explore, 'survive': survive}})


def setup(store, player=False):
    events = [event('LocationCreated', {'id':'village','name':'Test Village'})]
    for ident in ['nora','basil'] + (['carlos'] if player else []):
        events.append(event('EntityCreated', {'id':ident, 'name':ident,
                       'location_id':'village','controller':'player' if ident=='carlos' else 'npc'}))
    events.extend([config('nora'), config('basil', fatigue=90, earn=10)])
    return store.append('test', 'setup', 0, events, bootstrap=True)




def active_service(store, *, decision_cooldown=60):
    clock=TimeEngine(store)
    clock.open_session('test')
    return NPCService(store, clock, decision_cooldown=decision_cooldown)


@pytest.fixture
def db(tmp_path):
    with SQLiteEventStore(tmp_path/'village.sqlite') as s:
        s.create_world('test')
        yield s


def test_creation_and_replay(db):
    state = setup(db)
    assert state.npcs['nora']['role'] == 'merchant'
    assert db.verify('test').to_dict() == state.to_dict()


def test_decision_differs_by_personality_and_needs(db):
    state = setup(db)
    assert choose_action(state, 'nora').action == 'work'
    assert choose_action(state, 'basil').action == 'rest'


def test_private_knowledge_affects_only_receiver(db):
    state = setup(db)
    before = choose_action(state, 'nora')
    received = event('NPCBeliefReceived', {'npc_id':'nora','key':'danger','claim':{
        'text':'bridge is unsafe', 'source':'messenger', 'received_at':0, 'confidence':100}})
    state = db.append('test','message',state.revision,[received])
    after = choose_action(state,'nora')
    assert before.action == 'work' and after.action == 'wait'
    assert choose_action(state,'basil').action == 'rest'
    assert 'danger' not in state.npcs['basil']['beliefs']


def test_belief_does_not_change_world_truth(db):
    state = setup(db)
    e = event('NPCBeliefReceived', {'npc_id':'nora','key':'danger','claim':{
        'text':'false alarm','source':'rumor','received_at':0,'confidence':100}})
    state = db.append('test','rumor',state.revision,[e])
    assert state.npcs['nora']['beliefs']['danger']['text'] == 'false alarm'
    assert 'danger' not in state.locations['village']


def test_player_cannot_be_npc(db):
    state=setup(db, player=True)
    assert choose_action(state,'carlos') is None
    with pytest.raises(InvalidEvent):
        db.append('test','fake',state.revision,[config('carlos')],bootstrap=True)


def test_no_repeated_decision_before_cooldown(db):
    state=setup(db)
    service=active_service(db,decision_cooldown=60)
    decision=service.decide('test','nora',command_id='choose',expected_revision=state.revision)
    assert decision.action=='work'
    state=db.load('test')
    assert state.npcs['nora']['next_decision_at']==60
    assert service.decide('test','nora',command_id='early',expected_revision=state.revision) is None
    assert db.load('test').revision==state.revision
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='early'").fetchone()[0]==0


def test_time_advance_then_next_decision(db):
    state=setup(db)
    svc=active_service(db)
    svc.decide('test','nora',command_id='first',expected_revision=state.revision)
    state=db.load('test')
    state=db.append('test','clock',state.revision,[event('TimeAdvanced',{'from':0,'to':60},time=60)],clock_authorized=True)
    assert svc.decide('test','nora',command_id='second',expected_revision=state.revision).action=='work'


def test_decision_records_intention_not_resource_or_time(db):
    state=setup(db)
    svc=active_service(db)
    svc.decide('test','nora',command_id='first',expected_revision=state.revision)
    after=db.load('test')
    assert after.time == state.time and after.resources == state.resources
    assert after.npcs['nora']['last_decision']['action']=='work'


def test_cannot_reconfigure_or_mutate_player(db):
    state=setup(db, player=True)
    with pytest.raises(InvalidEvent):db.append('test','duplicate',state.revision,[config('nora')],bootstrap=True)
    with pytest.raises(InvalidEvent):db.append('test','player-need',state.revision,[event('NPCNeedChanged',{'npc_id':'carlos','need':'hunger','previous':0,'current':99})])


def test_need_updates_require_previous_value(db):
    state=setup(db)
    valid=event('NPCNeedChanged',{'npc_id':'nora','need':'fatigue','previous':5,'current':90},actor='nora')
    after=db.append('test','tired',state.revision,[valid])
    assert choose_action(after,'nora').action == 'rest'
    with pytest.raises(InvalidEvent):db.append('test','invalid',after.revision,[valid])


def test_unauthorized_cross_actor_need_change_rejected(db):
    state=setup(db)
    bad=event('NPCNeedChanged',{'npc_id':'nora','need':'fatigue','previous':5,'current':99},actor='basil')
    with pytest.raises(InvalidEvent):db.append('test','hijack',state.revision,[bad])


def test_malformed_claim_fails_atomically(db):
    state=setup(db)
    bad=event('NPCBeliefReceived',{'npc_id':'nora','key':'danger','claim':{'text':'rumor','source':'market','received_at':0,'confidence':101}})
    with pytest.raises(InvalidEvent):db.append('test','bad',state.revision,[bad])
    assert db.load('test').revision==state.revision


def test_replay_snapshot_carries_beliefs_decisions(db):
    state=setup(db)
    state=db.append('test','message',state.revision,[event('NPCBeliefReceived',{'npc_id':'nora','key':'danger','claim':{'text':'rumor','source':'hunter','received_at':0,'confidence':80}})])
    db.snapshot('test')
    service=active_service(db)
    service.decide('test','nora',command_id='decision',expected_revision=state.revision)
    assert db.verify('test').to_dict()==db.load('test').to_dict()


def test_deterministic_across_independent_databases(tmp_path):
    outputs=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path/f'world{i}.db') as s:
            s.create_world('test')
            state=setup(s)
            active_service(s).decide('test','nora',command_id='d1',expected_revision=state.revision)
            outputs.append(s.verify('test').to_dict())
    assert outputs[0]==outputs[1]


def test_stale_revision_does_not_choose(db):
    state=setup(db)
    active_service(db).decide('test','nora',command_id='first',expected_revision=state.revision)
    with pytest.raises(RevisionConflict):active_service(db).decide('test','basil',command_id='stale',expected_revision=state.revision)


def test_no_omniscient_action_when_no_knowledge(db):
    state=setup(db)
    assert 'danger' not in state.npcs['nora']['beliefs']
    assert 'belief_danger=0' in choose_action(state,'nora').reason


def test_immutable_nested_claim(db):
    state=setup(db)
    with pytest.raises(TypeError):state.npcs['nora']['needs']['fatigue']=99


def test_invalid_next_decision_rejected(db):
    state=setup(db)
    chosen=event('NPCDecisionRecorded',{'npc_id':'nora','action':'work','score':20,'reason':'test','next_decision_at':0},actor='nora')
    with pytest.raises(InvalidEvent):db.append('test','no-delay',state.revision,[chosen])


def test_no_npc_decision_when_session_is_closed(db):
    state=setup(db)
    clock=TimeEngine(db)
    svc=NPCService(db,clock)
    from carlos_sim import SessionClosed
    with pytest.raises(SessionClosed):
        svc.decide('test','nora',command_id='unauthorized',expected_revision=state.revision)
    assert db.load('test').revision==state.revision


def test_direct_npc_decision_rejected_even_with_valid_payload(db):
    state=setup(db)
    d=choose_action(state,'nora')
    ev=event('NPCDecisionRecorded', {'npc_id':'nora','action':d.action,'score':d.score,'reason':d.reason,'next_decision_at':60},actor='nora')
    with pytest.raises(InvalidEvent,match='planner capability'):
        db.append('test','spoof',state.revision,[ev])


def test_forged_score_rejected_even_with_capability(db):
    state=setup(db)
    ev=event('NPCDecisionRecorded',{'npc_id':'nora','action':'rest','score':999,'reason':'fake','next_decision_at':60},actor='nora')
    with pytest.raises(InvalidEvent,match='utility policy'):
        db.append('test','forged',state.revision,[ev],npc_authorized=True)


def test_five_person_demo_is_reproducible():
    import importlib.util
    from pathlib import Path
    module_path=Path(__file__).resolve().parents[1]/'scenarios'/'test_village'/'demo.py'
    spec=importlib.util.spec_from_file_location('carlos_npc_demo', module_path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first=module.run()
    assert len(first)==5 and len({x[0] for x in first})==5
    assert first==module.run()
