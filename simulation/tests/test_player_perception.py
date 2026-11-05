"""01-X: local knowledge, unverified rumor, replay and adversarial boundaries."""
from __future__ import annotations

import pytest

from carlos_sim import (
    PlayerGateway, SQLiteEventStore, TimeEngine, DomainEvent,
    NPCSocialService, apply_event,
)
from carlos_sim.knowledge import make_observation_events
from carlos_sim.store import InvalidEvent, DuplicateCommand, RevisionConflict
from carlos_sim.time_engine import SessionClosed
from test_player_gateway import setup_player_demo_world


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / 'player-01x.sqlite') as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session('world')
        yield db, clock, PlayerGateway(
            db, clock, world_id='world', player_id='carlos')


def test_inspect_is_still_read_only_and_does_not_invent_sightings(world):
    db, clock, gw = world
    before = db.load('world').to_dict()
    assert gw.inspect().details['location_id'] == 'market'
    assert gw.recall().details == {'observations': (), 'hearsay': ()}
    assert db.load('world').to_dict() == before


def test_observation_local_only_and_survives_departure(world):
    db, clock, gw = world
    view = gw.observe(command_id='look1', expected_revision=db.load('world').revision)
    assert view.status == 'present'
    assert len(gw.recall().details['observations']) == 1
    seen_market = gw.recall().details['observations'][0]
    assert seen_market['location_id'] == 'market'
    assert {x['id'] for x in seen_market['occupants']} == {'carlos', 'basim', 'nora'}
    assert 'sara' not in str(gw.recall().details)
    gw.move('road', command_id='trip', expected_revision=db.load('world').revision)
    gw.wait(90, command_id='arrive', expected_revision=db.load('world').revision)
    assert gw.inspect().details['location_id'] == 'forest'
    assert len(gw.recall().details['observations']) == 1
    gw.observe(command_id='look2', expected_revision=db.load('world').revision)
    memories = gw.recall().details['observations']
    assert {x['location_id'] for x in memories} == {'market', 'forest'}
    forest = next(x for x in memories if x['location_id'] == 'forest')
    assert {x['id'] for x in forest['occupants']} == {'carlos', 'sara'}
    assert db.verify('world').to_dict() == db.load('world').to_dict()


def test_fake_sightings_and_untrusted_capabilities_rejected_atomically(world):
    db, clock, gw = world
    state = db.load('world')
    bad = [
        DomainEvent('PlayerObserved', 'nora', 'impersonate', 0,
                    {'location_id': 'market',
                     'occupants': ['basim', 'carlos', 'nora']}),
        DomainEvent('PlayerObserved', 'carlos', 'remote', 0,
                    {'location_id': 'forest', 'occupants': ['carlos', 'sara']}),
        DomainEvent('PlayerObserved', 'carlos', 'fabrication', 0,
                    {'location_id': 'market', 'occupants': ['carlos']}),
    ]
    for i, event in enumerate(bad):
        with pytest.raises(InvalidEvent):
            db.append('world', f'forged-{i}', state.revision,
                      [event], movement_authorized=True)
    with pytest.raises(InvalidEvent):
        db.append('world', 'unauthorized', state.revision,
                  [DomainEvent('PlayerObserved', 'carlos', 'untrusted', 0,
                      {'location_id': 'market',
                       'occupants': ['basim', 'carlos', 'nora']})])
    with pytest.raises(ValueError):
        apply_event(state, bad[1], movement_authorized=True)
    assert db.load('world').to_dict() == state.to_dict()


def test_travel_and_stale_revision_block_observation(world):
    db, clock, gw = world
    original = db.load('world')
    with pytest.raises(RevisionConflict):
        gw.observe(command_id='stale', expected_revision=-1)
    gw.move('road', command_id='travel', expected_revision=original.revision)
    state = db.load('world').to_dict()
    with pytest.raises(ValueError, match='travelling'):
        gw.observe(command_id='midway', expected_revision=state['revision'])
    assert db.load('world').to_dict() == state
    gw.wait(90, command_id='arrival', expected_revision=state['revision'])
    gw.observe(command_id='once', expected_revision=db.load('world').revision)
    with pytest.raises(DuplicateCommand):
        gw.observe(command_id='once', expected_revision=db.load('world').revision)


def prepare_food_belief(db):
    db.append('world', 'food-start', db.load('world').revision, [
        DomainEvent('ResourceChanged', None, 'finite source', 0, {
            'owner_id': 'market', 'resource': 'wild_food', 'previous': None,
            'current': 4, 'source': 'initialization'})
    ], bootstrap=True)
    state = db.load('world')
    events = make_observation_events(state, 'basim', 'market', state.time, '01x-test')
    assert len(events) == 2
    db.append('world', 'basim-verified', state.revision, events, npc_authorized=True)


def test_only_existing_npc_belief_can_reach_local_player_as_hearsay(world):
    db, clock, gw = world
    prepare_food_belief(db)
    before = db.load('world')
    saved = NPCSocialService(db, clock).share_food_claim_to_player(
        'world', 'basim', 'carlos', site_id='market',
        message_id='rumor1', expected_revision=before.revision)
    assert saved.revision == before.revision + 1
    rumors = gw.recall().details['hearsay']
    assert len(rumors) == 1
    assert rumors[0]['speaker_id'] == 'basim'
    assert rumors[0]['status'] == 'unverified'
    assert rumors[0]['key'] == 'food:market'
    assert rumors[0]['claim'] == 'food-state:present; observed_at=0'
    assert 'resources' not in str(gw.recall().details)
    assert 'confidence' not in str(gw.recall().details)
    assert db.verify('world').to_dict() == saved.to_dict()
    with pytest.raises(DuplicateCommand):
        NPCSocialService(db, clock).share_food_claim_to_player(
            'world', 'basim', 'carlos', site_id='market',
            message_id='rumor1', expected_revision=saved.revision)


def test_fake_claims_remote_speech_and_other_player_secrecy(world):
    db, clock, gw = world
    prepare_food_belief(db)
    original = db.load('world').to_dict()
    for i, (speaker, key, claim) in enumerate((
        ('basim', 'food:market', 'food-state:empty; observed_at=0'),
        ('sara', 'food:market', 'food-state:present; observed_at=0'),
        ('basim', 'secret:inventory', 'arbitrary'))):
        event = DomainEvent('PlayerHearsayReceived', speaker, 'forged', 0,
                            {'player_id': 'carlos', 'key': key, 'text': claim})
        with pytest.raises(InvalidEvent):
            db.append('world', f'forged-rumor-{i}', original['revision'],
                      [event], social_authorized=True)
    assert db.load('world').to_dict() == original
    db.append('world', 'second-player', db.load('world').revision, [
        DomainEvent('EntityCreated', None, 'second human', 0, {
            'id': 'other', 'name': 'Other', 'controller': 'player',
            'location_id': 'market'})
    ], bootstrap=True)
    NPCSocialService(db, clock).share_food_claim_to_player(
        'world', 'basim', 'other', site_id='market',
        message_id='only-other', expected_revision=db.load('world').revision)
    assert gw.recall().details['hearsay'] == ()
    other = PlayerGateway(db, clock, world_id='world', player_id='other')
    assert len(other.recall().details['hearsay']) == 1
    gw.move('road', command_id='move', expected_revision=db.load('world').revision)
    old = db.load('world').to_dict()
    with pytest.raises(ValueError, match='co-located'):
        NPCSocialService(db, clock).share_food_claim_to_player(
            'world', 'basim', 'carlos', site_id='market',
            message_id='remote', expected_revision=old['revision'])
    assert db.load('world').to_dict() == old


def test_memory_survives_sqlite_reopen_snapshot_and_verify(tmp_path):
    path = tmp_path / 'replay.sqlite'
    with SQLiteEventStore(path) as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session('world')
        gw = PlayerGateway(db, clock, world_id='world', player_id='carlos')
        gw.observe(command_id='sighting', expected_revision=db.load('world').revision)
        prepare_food_belief(db)
        NPCSocialService(db, clock).share_food_claim_to_player(
            'world', 'basim', 'carlos', site_id='market',
            message_id='gossip', expected_revision=db.load('world').revision)
        remembered = gw.recall().details
        db.snapshot('world')
        assert db.verify('world').to_dict() == db.load('world').to_dict()
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session('world')
        gw = PlayerGateway(db, clock, world_id='world', player_id='carlos')
        assert gw.recall().details == remembered
        assert db.verify('world').to_dict() == db.load('world').to_dict()
        assert db.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_closed_session_blocks_perception_without_deleting_memory(world):
    db, clock, gw = world
    gw.observe(command_id='look', expected_revision=db.load('world').revision)
    before = db.load('world').to_dict()
    clock.close_session('world')
    with pytest.raises(SessionClosed):
        gw.observe(command_id='closed', expected_revision=before['revision'])
    with pytest.raises(SessionClosed):
        gw.recall()
    assert db.load('world').to_dict() == before
