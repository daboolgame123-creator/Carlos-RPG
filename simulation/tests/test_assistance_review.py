"""Phase 01-J review: explicit session and local withdrawal invariants."""
import pytest
from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCAssistanceService, NPCMovementService
from carlos_sim.store import InvalidEvent
from test_assistance import setup, request, full_request


def test_inventory_consumption_cannot_happen_after_play_session_closed(tmp_path):
    with SQLiteEventStore(tmp_path / 'offline.sqlite') as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session('w')
        clock.close_session('w')
        old = db.load('w')
        consume = DomainEvent('ResourceChanged', 'basim', 'eat food', old.time, {
            'owner_id': 'basim', 'resource': 'food', 'previous': 10,
            'current': 9, 'source': 'consumption'})
        with pytest.raises(InvalidEvent, match='active play session'):
            db.append('w', 'offline-food', old.revision, [consume])
        assert db.load('w').to_dict() == old.to_dict()


def test_active_player_consumption_remains_permitted(tmp_path):
    with SQLiteEventStore(tmp_path / 'active.sqlite') as db:
        setup(db)
        clock=TimeEngine(db)
        clock.open_session('w')
        old=db.load('w')
        consumed=db.append('w','eat',old.revision,[DomainEvent('ResourceChanged','basim',
            'eat food', old.time, {'owner_id':'basim','resource':'food',
                                    'previous':10,'current':9,'source':'consumption'})])
        assert consumed.resources['basim']['food']==9
        assert db.verify('w').to_dict()==consumed.to_dict()


def test_provider_cannot_silently_cancel_promise_while_traveling(tmp_path):
    with SQLiteEventStore(tmp_path / 'remote.sqlite') as db:
        setup(db)
        clock=TimeEngine(db);clock.open_session('w')
        service=NPCAssistanceService(db,clock)
        full_request(db,service)
        mover=NPCMovementService(db,clock)
        departure=mover.start('w','basim','road','departure',expected_revision=db.load('w').revision)
        with pytest.raises(InvalidEvent, match='local'):
            service.cancel('w','basim','help1',reason='promise_withdrawn',
                command_id='invisible-revoke',expected_revision=departure.state.revision)
        assert db.load('w').obligations['help1']['status']=='promised'


def test_provider_can_cancel_promise_after_reuniting_elsewhere(tmp_path):
    with SQLiteEventStore(tmp_path / 'reunion.sqlite') as db:
        setup(db)
        clock=TimeEngine(db);clock.open_session('w')
        svc=NPCAssistanceService(db,clock)
        full_request(db,svc)
        mover=NPCMovementService(db,clock)
        mover.start('w','basim','road','basim-travel',expected_revision=db.load('w').revision)
        mover.start('w','nora','road','nora-travel',expected_revision=db.load('w').revision)
        clock.advance('w', seconds=20, command_id='arrive', expected_revision=db.load('w').revision)
        cancelled=svc.cancel('w','basim','help1',reason='promise_withdrawn',
                             command_id='revoke-in-person', expected_revision=db.load('w').revision)
        assert cancelled.status=='cancelled'
        assert cancelled.state.resources['basim']['food']==10
        assert cancelled.state.relations=={}
        assert db.verify('w').to_dict()==cancelled.state.to_dict()


def test_requester_cannot_withdraw_unanswered_request_from_the_road(tmp_path):
    with SQLiteEventStore(tmp_path / 'requester-on-road.sqlite') as db:
        setup(db)
        clock = TimeEngine(db); clock.open_session('w')
        service = NPCAssistanceService(db, clock)
        request(db, service)
        mover = NPCMovementService(db, clock)
        departed = mover.start('w', 'nora', 'road', 'requester-leaves',
                               expected_revision=db.load('w').revision)
        with pytest.raises(InvalidEvent, match='local'):
            service.cancel('w', 'nora', 'help1', reason='request_withdrawn',
                           command_id='remote-withdraw', expected_revision=departed.state.revision)
        assert db.load('w').obligations['help1']['status'] == 'requested'


def test_provider_cannot_cancel_promise_from_different_location(tmp_path):
    with SQLiteEventStore(tmp_path / 'different-locations.sqlite') as db:
        setup(db)
        clock=TimeEngine(db); clock.open_session('w')
        svc=NPCAssistanceService(db, clock)
        full_request(db, svc)
        departed=NPCMovementService(db,clock).start('w', 'basim', 'road', 'provider-leaves',
                                   expected_revision=db.load('w').revision)
        arrived=clock.advance('w',seconds=20,command_id='reach-forest',
                              expected_revision=departed.state.revision)
        assert arrived.state.entities['basim']['location_id'] == 'forest'
        assert arrived.state.entities['nora']['location_id'] == 'market'
        with pytest.raises(InvalidEvent, match='local'):
            svc.cancel('w','basim','help1',reason='promise_withdrawn',
                       command_id='remote-withdraw',expected_revision=arrived.state.revision)
        assert db.verify('w').obligations['help1']['status']=='promised'
