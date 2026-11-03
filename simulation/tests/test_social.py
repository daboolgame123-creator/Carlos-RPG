"""Phase 01-H: independent, asymmetric social relationships and event sourcing."""
from pathlib import Path
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCSocialService, NPCMovementService
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand


def ev(kind, data, actor=None, t=0):
    return DomainEvent(kind, actor, 'test', t, data)


def setup(db):
    db.create_world('world')
    events = [ev('LocationCreated', {'id':'market','name':'Market'}),
              ev('LocationCreated', {'id':'forest','name':'Forest'}),
              ev('RouteCreated', {'id':'road','a':'market','b':'forest','seconds':90})]
    for name, place, role in [('nora','market','npc'),('basim','market','npc'),
                              ('sara','forest','npc'),('carlos','market','player')]:
        events.append(ev('EntityCreated',{'id':name,'name':name,'controller':role,'location_id':place}))
        if role=='npc':
            events.append(ev('NPCConfigured', {'npc_id':name,'role':'resident',
                'needs':{'fatigue':5,'hunger':10,'safety':0},
                'goals':{'earn':30,'explore':10,'survive':20}}))
    return db.append('world','setup',0,events,bootstrap=True)


@pytest.fixture
def setup_world(tmp_path):
    with SQLiteEventStore(tmp_path/'social.db') as db:
        setup(db)
        clock=TimeEngine(db);clock.open_session('world')
        yield db,clock,NPCSocialService(db,clock)


def interact(db,service, sender='nora',recipient='basim',kind='greeting',mid='one'):
    return service.interact('world',sender,recipient,kind=kind,text='Hello',message_id=mid,
                            expected_revision=db.load('world').revision)


def test_greeting_changes_only_recipients_trust(setup_world):
    db,clock,service=setup_world
    result=interact(db,service)
    assert result.reaction=='acknowledged' and (result.trust_before,result.trust_after)==(0,1)
    assert result.state.relations['basim']['nora']==1
    assert 'basim' not in result.state.relations.get('nora',{})
    assert db.verify('world').to_dict()==result.state.to_dict()


def test_repeated_help_offers_are_not_recorded_as_actual_help(setup_world):
    db,_,service=setup_world
    first=interact(db,service,kind='offer_help',mid='offer1')
    second=interact(db,service,kind='offer_help',mid='offer2')
    assert (first.trust_after,second.trust_after)==(3,6)
    assert second.state.resources=={}
    assert second.state.social_messages['offer2']['reaction']=='welcomed'


def test_threat_changes_attitude_without_affecting_sender(setup_world):
    db,_,service=setup_world
    r=interact(db,service,kind='threat')
    assert r.reaction=='alarmed' and r.trust_after==-12
    assert 'basim' not in r.state.relations.get('nora',{})


def test_request_help_can_be_refused_based_on_prior_trust(setup_world):
    db,_,service=setup_world
    interact(db,service,kind='threat',mid='threat')
    r=interact(db,service,kind='request_help',mid='ask')
    assert (r.reaction,r.trust_before,r.trust_after)==('refused',-12,-14)


def test_co_location_required(setup_world):
    db,_,service=setup_world
    state=db.load('world').to_dict()
    with pytest.raises(InvalidEvent,match='locally'):
        interact(db,service,recipient='sara')
    assert db.load('world').to_dict()==state


def test_traveler_cannot_send_or_receive(setup_world):
    db,clock,service=setup_world
    trip=NPCMovementService(db,clock).start('world','nora','road','travel',
        expected_revision=db.load('world').revision)
    with pytest.raises(InvalidEvent,match='locally'):
        interact(db,service)
    with pytest.raises(InvalidEvent,match='locally'):
        interact(db,service,sender='basim',recipient='nora',mid='incoming')
    assert db.load('world').revision==trip.state.revision


def test_delivery_after_arrival_allowed(setup_world):
    db,clock,service=setup_world
    trip=NPCMovementService(db,clock).start('world','nora','road','travel',
        expected_revision=db.load('world').revision)
    clock.advance('world',seconds=90,command_id='arrive',expected_revision=trip.state.revision)
    reply=interact(db,service,sender='sara',recipient='nora')
    assert reply.trust_after==1 and reply.state.time==90


def test_player_sender_can_speak_without_being_npc_controlled(setup_world):
    db,_,service=setup_world
    result=interact(db,service,sender='carlos')
    assert result.state.relations['basim']['carlos']==1
    assert 'carlos' not in result.state.npcs


def test_npc_cannot_automatically_control_player_recipient(setup_world):
    db,_,service=setup_world
    with pytest.raises(InvalidEvent,match='identity'):
        interact(db,service,recipient='carlos')


def test_direct_forged_receipt_disallowed_without_send(setup_world):
    db,_,service=setup_world
    original=db.load('world')
    with pytest.raises(InvalidEvent,match='pending'):
        db.append('world','forged',original.revision,[ev('SocialMessageReceived',{'id':'missing'},'basim')],social_authorized=True)
    assert db.load('world').revision==original.revision


def test_bad_recipient_cannot_receive_someone_elses_message(setup_world):
    db,_,service=setup_world
    original=db.load('world')
    sent=ev('SocialMessageSent',{'id':'pending','recipient':'basim','kind':'greeting','text':'Hi'},'nora')
    saved=db.append('world','sent-only',original.revision,[sent],social_authorized=True)
    with pytest.raises(InvalidEvent,match='recipient'):
        db.append('world','steal',saved.revision,[ev('SocialMessageReceived',{'id':'pending'},'nora')],social_authorized=True)
    assert db.load('world').social_messages['pending']['status']=='pending'


def test_same_message_can_only_be_received_once(setup_world):
    db,_,service=setup_world
    result=interact(db,service)
    with pytest.raises(InvalidEvent,match='pending'):
        db.append('world','twice',result.state.revision,[ev('SocialMessageReceived',{'id':'one'},'basim')],social_authorized=True)
    assert db.load('world').relations['basim']['nora']==1


def test_message_id_collision_and_duplicate_command(setup_world):
    db,_,service=setup_world
    interact(db,service)
    with pytest.raises(DuplicateCommand):
        interact(db,service,mid='one',kind='threat')
    assert db.load('world').relations['basim']['nora']==1


def test_closed_session_rejects_all_social_events(setup_world):
    db,clock,service=setup_world
    clock.close_session('world')
    before=db.load('world')
    with pytest.raises(PermissionError):
        interact(db,service)
    with pytest.raises(InvalidEvent,match='active play session'):
        db.append('world','bypass',before.revision,[ev('SocialMessageSent',{'id':'x','recipient':'basim','kind':'greeting','text':'x'},'nora')],social_authorized=True)
    assert db.load('world').revision==before.revision


def test_without_capability_is_rejected(setup_world):
    db,_,_=setup_world
    with pytest.raises(InvalidEvent,match='trusted'):
        db.append('world','no-cap',db.load('world').revision,[ev('SocialMessageSent',{'id':'x','recipient':'basim','kind':'greeting','text':'hi'},'nora')])


def test_old_relationship_snapshot_immutable(setup_world):
    db,_,service=setup_world
    result=interact(db,service)
    with pytest.raises(TypeError):
        result.state.relations['basim']['nora']=50


def test_replay_survives_restart(tmp_path):
    path=tmp_path/'restart.db'
    with SQLiteEventStore(path) as db:
        setup(db)
        c=TimeEngine(db);c.open_session('world')
        NPCSocialService(db,c).interact('world','nora','basim',kind='threat',text='Stop',message_id='one',expected_revision=db.load('world').revision)
        db.snapshot('world')
    with SQLiteEventStore(path) as db:
        assert db.verify('world').relations['basim']['nora']==-12
        assert db.load('world').social_messages['one']['status']=='received'


def test_stale_revision_rejected(setup_world):
    db,_,service=setup_world
    prior=db.load('world').revision
    interact(db,service)
    with pytest.raises(RevisionConflict):
        service.interact('world','nora','basim',kind='greeting',text='Hi',message_id='two',expected_revision=prior)


def test_two_worlds_produce_same_relationship_projection(tmp_path):
    outputs=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path/f'{i}.db') as db:
            setup(db)
            clock=TimeEngine(db);clock.open_session('world')
            svc=NPCSocialService(db,clock)
            for k in ('greeting','threat','request_help','offer_help'):
                interact(db,svc,mid=k,kind=k)
            outputs.append(db.verify('world').to_dict())
    assert outputs[0]==outputs[1]


def test_recipient_can_change_mind_only_after_new_event(setup_world):
    db,_,service=setup_world
    r1=interact(db,service,kind='threat',mid='t1')
    old=r1.state.to_dict()
    r2=interact(db,service,kind='offer_help',mid='o1')
    assert r2.reaction=='welcomed' and r2.trust_after==-9
    assert old['relations']['basim']['nora']==-12


def test_capped_trust_does_not_overflow(setup_world):
    db,_,service=setup_world
    for i in range(40):
        r=interact(db,service,kind='offer_help',mid=f'o{i}')
    assert r.trust_after==100
    assert db.verify('world').relations['basim']['nora']==100


def test_same_tick_atomic_send_and_receive(setup_world):
    db,_,service=setup_world
    before=db.load('world')
    r=interact(db,service)
    assert r.state.time==before.time
    assert r.state.revision==before.revision+2
    assert r.state.social_messages['one']['status']=='received'


def test_invalid_message_length_rejected(setup_world):
    db,_,service=setup_world
    with pytest.raises(InvalidEvent):
        service.interact('world','nora','basim',kind='greeting',text='x'*501,message_id='too-long',expected_revision=db.load('world').revision)


def test_no_untrusted_social_event_impersonation(setup_world):
    db,_,service=setup_world
    before=db.load('world')
    fake=ev('SocialMessageSent',{'id':'fake','recipient':'basim','kind':'threat','text':'hello'},actor='ghost')
    with pytest.raises(InvalidEvent):
        db.append('world','ghost',before.revision,[fake],social_authorized=True)
    assert db.load('world').to_dict()==before.to_dict()
