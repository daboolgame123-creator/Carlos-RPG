import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCMovementService
from carlos_sim.store import InvalidEvent

def e(kind,data,actor=None,t=0):
    return DomainEvent(kind,actor,'review',t,data)

def setup(db):
    db.create_world('w')
    events=[e('LocationCreated',{'id':'a','name':'A'}), e('LocationCreated',{'id':'b','name':'B'}),e('RouteCreated',{'id':'road','a':'a','b':'b','seconds':10})]
    for npc in ('alice','bob'):
        events.extend([e('EntityCreated',{'id':npc,'name':npc,'location_id':'a','controller':'npc'}),e('NPCConfigured',{'npc_id':npc,'role':'test','needs':{'fatigue':0,'hunger':0,'safety':0},'goals':{'earn':0,'explore':0,'survive':0}})])
    db.append('w','init',0,events,bootstrap=True)
    TimeEngine(db).open_session('w')

def test_pending_local_message_cannot_be_accepted_at_different_location(tmp_path):
    with SQLiteEventStore(tmp_path/'review.db') as db:
        setup(db)
        first=db.append('w','send',db.load('w').revision,[e('SocialMessageSent',{'id':'m1','recipient':'bob','kind':'threat','text':'stay here'},'alice')],social_authorized=True)
        mover=NPCMovementService(db,TimeEngine(db))
        mover.start('w','alice','road','alice-trip',expected_revision=db.load('w').revision)
        mover.start('w','bob','road','bob-trip',expected_revision=db.load('w').revision)
        TimeEngine(db).advance('w',seconds=10,command_id='arrive',expected_revision=db.load('w').revision)
        before=db.load('w')
        assert before.entities['alice']['location_id']=='b' and before.entities['bob']['location_id']=='b'
        with pytest.raises(InvalidEvent,match='original.*location'):
            db.append('w','receipt',before.revision,[e('SocialMessageReceived',{'id':'m1'},'bob',10)],social_authorized=True)
        assert db.load('w').relations=={}
        assert db.verify('w').to_dict()==before.to_dict()

def test_same_location_delayed_receipt_remains_valid(tmp_path):
    with SQLiteEventStore(tmp_path/'valid.db') as db:
        setup(db)
        db.append('w','send',db.load('w').revision,[e('SocialMessageSent',{'id':'m1','recipient':'bob','kind':'greeting','text':'hi'},'alice')],social_authorized=True)
        TimeEngine(db).advance('w',seconds=10,command_id='advance',expected_revision=db.load('w').revision)
        result=db.append('w','receipt',db.load('w').revision,[e('SocialMessageReceived',{'id':'m1'},'bob',10)],social_authorized=True)
        assert result.relations['bob']['alice']==1
        assert db.verify('w').to_dict()==result.to_dict()

def test_duplicate_same_tick_social_kind_cannot_farm_trust(tmp_path):
    from carlos_sim import NPCSocialService
    with SQLiteEventStore(tmp_path/'spam.db') as db:
        setup(db)
        svc=NPCSocialService(db,TimeEngine(db))
        first=svc.interact('w','alice','bob',kind='offer_help',text='help?',message_id='one',expected_revision=db.load('w').revision)
        before=first.state.to_dict()
        with pytest.raises(InvalidEvent,match='duplicate social act'):
            svc.interact('w','alice','bob',kind='offer_help',text='help!',message_id='two',expected_revision=first.state.revision)
        assert db.load('w').to_dict()==before
        TimeEngine(db).advance('w',seconds=1,command_id='tick',expected_revision=first.state.revision)
        later=svc.interact('w','alice','bob',kind='offer_help',text='again',message_id='two',expected_revision=db.load('w').revision)
        assert later.trust_after==6
        assert db.verify('w').to_dict()==later.state.to_dict()

def test_multiple_different_social_acts_same_tick_are_still_possible(tmp_path):
    from carlos_sim import NPCSocialService
    with SQLiteEventStore(tmp_path/'kinds.db') as db:
        setup(db)
        svc=NPCSocialService(db,TimeEngine(db))
        first=svc.interact('w','alice','bob',kind='greeting',text='hello',message_id='g',expected_revision=db.load('w').revision)
        second=svc.interact('w','alice','bob',kind='threat',text='stay',message_id='t',expected_revision=first.state.revision)
        assert second.trust_after == -11
        assert db.verify('w').to_dict()==second.state.to_dict()
