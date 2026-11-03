"""Phase 01-J: real resource conservation, promises, refusals, audit and replay."""
from pathlib import Path
import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine,
                        NPCAssistanceService, NPCMovementService, NPCSocialService)
from carlos_sim.store import (InvalidEvent, RevisionConflict, DuplicateCommand)


def e(kind, data, actor=None, at=0):
    return DomainEvent(kind, actor, 'assistance-test', at, data)


def setup(db, *, food_a=1, food_b=10, water_a=0, water_b=8, initialize=True):
    db.create_world('w')
    events = [e('LocationCreated', {'id':'market','name':'Market'}),
              e('LocationCreated', {'id':'forest','name':'Forest'}),
              e('RouteCreated', {'id':'road','a':'market','b':'forest','seconds':20})]
    for name, place, controller in (
        ('nora','market','npc'), ('basim','market','npc'),
        ('sara','forest','npc'), ('carlos','market','player')):
        events.append(e('EntityCreated', {'id':name,'name':name,'location_id':place,
                                          'controller':controller}))
        if controller == 'npc':
            events.append(e('NPCConfigured', {'npc_id':name, 'role':'resident',
                     'needs':{'fatigue':5,'hunger':25,'safety':0},
                     'goals':{'earn':20,'explore':10,'survive':20}}))
    if initialize:
        for person, qty_food, qty_water in (('nora',food_a,water_a),
                                            ('basim',food_b,water_b),('sara',0,0)):
            for name, qty in [('food',qty_food),('water',qty_water),('labor_units',0),('investigation_attempts',0)]:
                events.append(e('ResourceChanged',{'owner_id':person,'resource':name,
                     'previous':None,'current':qty,'source':'initialization'}))
    db.append('w','bootstrap',0,events,bootstrap=True)


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path/'help.sqlite') as db:
        setup(db)
        clock=TimeEngine(db); clock.open_session('w')
        yield db, clock, NPCAssistanceService(db,clock)


def request(db,svc,ident='help1',qty=3,resource='food',requester='nora',provider='basim'):
    return svc.request('w',requester,provider,resource,qty,ident,
                       expected_revision=db.load('w').revision)


def respond(db,svc,ident='help1',accept=True,actor='basim',cmd='answer'):
    return svc.respond('w',actor,ident,accept=accept,command_id=cmd,
                       expected_revision=db.load('w').revision)


def deliver(db,svc,ident='help1',actor='basim',cmd='deliver'):
    return svc.deliver('w',actor,ident,command_id=cmd,
                       expected_revision=db.load('w').revision)


def full_request(db,svc,ident='help1',qty=3):
    request(db,svc,ident,qty)
    return respond(db,svc,ident,cmd=f'response-{ident}')


def test_request_is_not_a_transfer_or_a_promise(world):
    db,_,svc=world
    before=db.load('w')
    result=request(db,svc)
    assert result.status=='requested'
    assert result.state.obligations['help1']['trust_before'] is None
    assert result.state.resources==before.resources
    assert result.state.relations==before.relations
    assert db.verify('w').to_dict()==result.state.to_dict()


def test_promise_is_not_a_transfer_and_no_free_trust(world):
    db,_,svc=world
    result=full_request(db,svc)
    assert result.status=='promised'
    assert result.state.resources['nora']['food']==1
    assert result.state.resources['basim']['food']==10
    assert result.state.relations=={}
    assert result.state.obligations['help1']['responded_at']==0


def test_physical_delivery_conserves_goods_and_rewards_receiver_trust_once(world):
    db,_,svc=world
    full_request(db,svc)
    result=deliver(db,svc)
    assert result.status=='fulfilled'
    assert (result.state.resources['nora']['food'],result.state.resources['basim']['food'])==(4,7)
    assert result.state.resources['nora']['food']+result.state.resources['basim']['food']==11
    assert result.state.resources['basim']['water']==8
    assert result.state.relations['nora']['basim']==5
    assert result.state.relations.get('basim',{})=={}
    assert result.state.obligations['help1']['trust_before']==0
    assert result.state.obligations['help1']['trust_after']==5
    assert result.state.obligations['help1']['transfer']=={
        'provider_before':10,'provider_after':7,
        'requester_before':1,'requester_after':4}
    assert db.verify('w').to_dict()==result.state.to_dict()


def test_same_promise_cannot_be_delivered_twice(world):
    db,_,svc=world
    full_request(db,svc)
    first=deliver(db,svc)
    with pytest.raises(InvalidEvent,match='fulfil a valid promise once'):
        deliver(db,svc,cmd='deliver-again')
    assert db.load('w').to_dict()==first.state.to_dict()


def test_provider_cannot_deliver_more_than_owned(world):
    db,_,svc=world
    full_request(db,svc,qty=11)
    before=db.load('w')
    with pytest.raises(InvalidEvent,match='insufficient real stock'):
        deliver(db,svc)
    assert db.load('w').to_dict()==before.to_dict()
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='deliver'").fetchone()[0]==0


def test_physical_stock_loss_after_promise_prevents_delivery(world):
    db,_,svc=world
    full_request(db,svc,qty=8)
    before=db.load('w')
    used=e('ResourceChanged',{'owner_id':'basim','resource':'food','previous':10,
              'current':2,'source':'consumption'},actor='basim')
    spent=db.append('w','eat',before.revision,[used])
    with pytest.raises(InvalidEvent,match='insufficient'):
        deliver(db,svc)
    assert db.load('w').to_dict()==spent.to_dict()
    cancelled=svc.cancel('w','basim','help1',reason='promise_withdrawn',command_id='cancel',expected_revision=spent.revision)
    assert cancelled.status=='cancelled' and cancelled.state.relations=={}


def test_explicit_refusal_does_not_transfer_or_change_trust(world):
    db,_,svc=world
    request(db,svc)
    declined=respond(db,svc,accept=False)
    assert declined.status=='declined'
    assert declined.state.resources['basim']['food']==10
    assert declined.state.relations=={}
    with pytest.raises(InvalidEvent):deliver(db,svc)


def test_requester_can_withdraw_unanswered_request(world):
    db,_,svc=world
    request(db,svc)
    cancelled=svc.cancel('w','nora','help1',reason='request_withdrawn',command_id='withdraw',expected_revision=db.load('w').revision)
    assert cancelled.status=='cancelled'
    with pytest.raises(InvalidEvent):respond(db,svc)


def test_provider_can_withdraw_promise_but_requester_cannot(world):
    db,_,svc=world
    full_request(db,svc)
    with pytest.raises(InvalidEvent,match='promisor'):
        svc.cancel('w','nora','help1',reason='promise_withdrawn',command_id='bad',expected_revision=db.load('w').revision)
    stopped=svc.cancel('w','basim','help1',reason='promise_withdrawn',command_id='stop',expected_revision=db.load('w').revision)
    assert stopped.status=='cancelled'
    with pytest.raises(InvalidEvent):deliver(db,svc)


def test_no_unknown_inventory_and_explicit_initialization(tmp_path):
    with SQLiteEventStore(tmp_path/'unknown.sqlite') as db:
        setup(db, initialize=False)
        clock=TimeEngine(db);clock.open_session('w')
        service=NPCAssistanceService(db,clock)
        before=db.load('w')
        with pytest.raises(InvalidEvent,match='explicitly initialized'):
            request(db,service)
        assert db.load('w').to_dict()==before.to_dict()


def test_unsupported_resource_rejected(world):
    db,_,svc=world
    for resource in ('gold','labor_units','investigation_attempts','',None):
        with pytest.raises(InvalidEvent):request(db,svc,resource=resource)


def test_invalid_quantities_rejected(world):
    db,_,svc=world
    for qty in (0,-1,1001,True,1.5,'3'):
        with pytest.raises(InvalidEvent):request(db,svc,qty=qty)


def test_no_player_automated_as_requester_or_provider(world):
    db,_,svc=world
    for requester,provider in (('carlos','basim'),('nora','carlos'),('nora','nora')):
        with pytest.raises(InvalidEvent):request(db,svc,requester=requester,provider=provider)


def test_request_must_be_local_and_not_during_travel(world):
    db,clock,svc=world
    with pytest.raises(InvalidEvent):request(db,svc,provider='sara')
    trip=NPCMovementService(db,clock).start('w','nora','road','journey',expected_revision=db.load('w').revision)
    with pytest.raises(InvalidEvent):request(db,svc)
    assert db.load('w').to_dict()==trip.state.to_dict()


def test_request_while_actively_working_rejected(world):
    db,clock,svc=world
    from carlos_sim import NPCService,NPCActionService
    NPCService(db,clock).decide('w','nora',command_id='choose',expected_revision=db.load('w').revision)
    NPCActionService(db,clock).start('w','nora','active',expected_revision=db.load('w').revision)
    with pytest.raises(InvalidEvent):request(db,svc)


def test_cannot_reply_after_moving_to_new_place_even_if_both_reunite(world):
    db,clock,svc=world
    request(db,svc)
    mover=NPCMovementService(db,clock)
    mover.start('w','nora','road','n-trip',expected_revision=db.load('w').revision)
    mover.start('w','basim','road','b-trip',expected_revision=db.load('w').revision)
    TimeEngine(db).advance('w',seconds=20,command_id='finish',expected_revision=db.load('w').revision)
    with pytest.raises(InvalidEvent,match='original request location'):
        respond(db,svc)


def test_delivery_after_both_travel_reunite_is_allowed(world):
    db,clock,svc=world
    full_request(db,svc)
    mover=NPCMovementService(db,clock)
    mover.start('w','nora','road','n-trip',expected_revision=db.load('w').revision)
    mover.start('w','basim','road','b-trip',expected_revision=db.load('w').revision)
    clock.advance('w',seconds=20,command_id='finish',expected_revision=db.load('w').revision)
    result=deliver(db,svc)
    assert result.status=='fulfilled'
    assert result.state.entities['nora']['location_id']=='forest'


def test_no_delivery_when_parties_separated(world):
    db,clock,svc=world
    full_request(db,svc)
    first=NPCMovementService(db,clock).start('w','nora','road','leave',expected_revision=db.load('w').revision)
    with pytest.raises(InvalidEvent,match='physically present'):
        deliver(db,svc)
    clock.advance('w',seconds=20,command_id='travel',expected_revision=first.state.revision)
    with pytest.raises(InvalidEvent,match='physically present'):
        deliver(db,svc)


def test_provider_must_authorize_response_and_transfer(world):
    db,_,svc=world
    request(db,svc)
    with pytest.raises(InvalidEvent,match='only the provider'):
        respond(db,svc,actor='nora')
    respond(db,svc)
    with pytest.raises(InvalidEvent,match='only the provider'):
        deliver(db,svc,actor='nora')


def test_social_words_alone_do_not_change_inventory_or_create_obligation(world):
    db,clock,_=world
    before=db.load('w')
    spoken=NPCSocialService(db,clock).interact('w','basim','nora',kind='offer_help',text='I offer food',message_id='say',expected_revision=before.revision)
    assert spoken.state.resources==before.resources
    assert spoken.state.obligations=={}
    assert spoken.state.social_messages['say']['kind']=='offer_help'


def test_open_request_blocks_duplicate_and_different_resource_allowed(world):
    db,_,svc=world
    request(db,svc)
    with pytest.raises(InvalidEvent,match='open assistance request'):
        request(db,svc,ident='same-topic')
    second=request(db,svc,ident='water',resource='water',qty=2)
    assert len(second.state.obligations)==2


def test_same_tick_request_replay_spam_blocked_even_after_declining(world):
    db,_,svc=world
    request(db,svc)
    respond(db,svc,accept=False)
    with pytest.raises(InvalidEvent,match='duplicate'):
        request(db,svc,ident='new')


def test_new_request_allowed_on_later_tick_after_resolution(world):
    db,clock,svc=world
    request(db,svc)
    respond(db,svc,accept=False)
    clock.advance('w',seconds=1,command_id='tick',expected_revision=db.load('w').revision)
    again=request(db,svc,ident='after-tick')
    assert again.status=='requested'


def test_low_level_event_without_assistance_capability_refused(world):
    db,_,_=world
    state=db.load('w')
    event=e('AssistanceRequested',{'id':'forged','provider':'basim','resource':'food','quantity':2},actor='nora')
    with pytest.raises(InvalidEvent,match='trusted assistance capability'):
        db.append('w','forged',state.revision,[event],social_authorized=True)
    assert db.load('w').to_dict()==state.to_dict()


def test_low_level_nonexistent_promise_cannot_create_goods(world):
    db,_,_=world
    original=db.load('w')
    with pytest.raises(InvalidEvent,match='unknown'):
        db.append('w','forge',original.revision,[e('AssistanceFulfilled',{'id':'nonexistent'},actor='basim')],assistance_authorized=True)
    assert db.load('w').to_dict()==original.to_dict()


def test_atomic_batch_rolls_back_valid_request_followed_by_fake_delivery(world):
    db,_,_=world
    before=db.load('w')
    events=[e('AssistanceRequested',{'id':'batch','provider':'basim','resource':'food','quantity':2},actor='nora'),
            e('AssistanceFulfilled',{'id':'batch'},actor='basim')]
    with pytest.raises(InvalidEvent):
        db.append('w','bad-batch',before.revision,events,assistance_authorized=True)
    assert db.load('w').to_dict()==before.to_dict()
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='bad-batch'").fetchone()[0]==0


def test_capability_cannot_run_without_play_session(world):
    db,clock,svc=world
    clock.close_session('w')
    before=db.load('w')
    with pytest.raises(PermissionError):request(db,svc)
    with pytest.raises(InvalidEvent,match='active play session'):
        db.append('w','offline',before.revision,[e('AssistanceRequested',{
            'id':'offline','provider':'basim','resource':'food','quantity':1},actor='nora')],assistance_authorized=True)
    assert db.load('w').to_dict()==before.to_dict()


def test_revision_conflict_prevents_racing_promises(world):
    db,_,svc=world
    first=request(db,svc)
    respond(db,svc)
    with pytest.raises(RevisionConflict):
        svc.respond('w','basim','help1',accept=False,command_id='late',expected_revision=first.state.revision)


def test_same_command_is_idempotent_not_second_transfer(world):
    db,_,svc=world
    full_request(db,svc)
    before=db.load('w')
    delivered=deliver(db,svc,cmd='one-transfer')
    # A high-level retry with a stale revision is rejected; no double delivery.
    with pytest.raises(RevisionConflict):
        svc.deliver('w','basim','help1',command_id='one-transfer',expected_revision=before.revision)
    assert db.load('w').to_dict()==delivered.state.to_dict()


def test_trust_reward_clamped_and_never_changes_provider_trust(world):
    db,clock,svc=world
    for i in range(40):
        NPCSocialService(db,clock).interact('w','basim','nora',kind='offer_help',text='hello',message_id=f'o{i}',expected_revision=db.load('w').revision)
        if i < 39:
            clock.advance('w',seconds=1,command_id=f'tick{i}',expected_revision=db.load('w').revision)
    assert db.load('w').relations['nora']['basim']==100
    full_request(db,svc)
    result=deliver(db,svc)
    assert result.state.relations['nora']['basim']==100
    assert result.state.obligations['help1']['trust_before']==100
    assert result.state.obligations['help1']['trust_after']==100
    assert result.state.relations.get('basim',{})=={}


def test_snapshots_and_reopen_preserve_unfulfilled_then_fulfilled(tmp_path):
    path=tmp_path/'restart.sqlite'
    with SQLiteEventStore(path) as db:
        setup(db)
        clock=TimeEngine(db);clock.open_session('w')
        service=NPCAssistanceService(db,clock)
        full_request(db,service)
        db.snapshot('w')
    with SQLiteEventStore(path) as db:
        before=db.load('w')
        assert before.obligations['help1']['status']=='promised'
        assert db.verify('w').to_dict()==before.to_dict()
        clock=TimeEngine(db)
        with pytest.raises(PermissionError):
            NPCAssistanceService(db,clock).deliver('w','basim','help1',command_id='offline',expected_revision=before.revision)
        clock.open_session('w')
        done=NPCAssistanceService(db,clock).deliver('w','basim','help1',command_id='resume',expected_revision=before.revision)
        assert done.state.resources['nora']['food']==4
        assert db.verify('w').to_dict()==done.state.to_dict()


def test_trust_and_contract_immutable_in_old_state(world):
    db,_,svc=world
    request(db,svc)
    promised=respond(db,svc)
    with pytest.raises(TypeError):
        promised.state.obligations['help1']['status']='fulfilled'
    delivered=deliver(db,svc)
    assert promised.state.obligations['help1']['status']=='promised'
    assert delivered.state.obligations['help1']['status']=='fulfilled'


def test_time_does_not_advance_on_hand_to_hand_delivery(world):
    db,_,svc=world
    full_request(db,svc)
    delivered=deliver(db,svc)
    assert delivered.state.time==0
    assert delivered.state.obligations['help1']['resolved_at']==0


def test_determinism_across_identical_worlds(tmp_path):
    output=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path/f'{i}.sqlite') as db:
            setup(db)
            clock=TimeEngine(db);clock.open_session('w')
            svc=NPCAssistanceService(db,clock)
            full_request(db,svc)
            deliver(db,svc)
            output.append(db.verify('w').to_dict())
    assert output[0]==output[1]


def test_contracts_are_not_exposed_in_player_view(world):
    db,_,svc=world
    full_request(db,svc)
    view=db.player_view('w')
    assert 'obligations' not in view and 'resources' not in view and 'relations' not in view
