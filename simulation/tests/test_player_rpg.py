"""01-Y: event-backed player RPG metadata, strict rights and replay."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, PlayerGateway, SQLiteEventStore, TimeEngine, WorldState,
    apply_event,
)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION
from carlos_sim.rpg_state import unknown_profile
from carlos_sim.store import (
    DuplicateCommand, InvalidEvent, RevisionConflict, IntegrityError,
)
from test_player_gateway import setup_player_demo_world


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / 'rpg-y.sqlite') as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session('world')
        yield db, clock, PlayerGateway(
            db, clock, world_id='world', player_id='carlos')


def fixture_profile():
    p = unknown_profile()
    p['vitals']['hp'] = {'current': 12, 'max': 12}
    p['vitals']['st'] = {'current': 7, 'max': 10}
    p['xp_current'] = 3
    p['xp_goal'] = None  # unknown != zero; no invented leveling rule
    p['attributes'] = {'focus': 5}
    return p


def initialize(db, *, player='carlos', profile=None, cid='rpg-init'):
    if profile is None:
        profile = fixture_profile()
    return db.append('world', cid, db.load('world').revision, [
        DomainEvent('PlayerRPGInitialized', None, 'disposable scenario setup', 0,
                    {'player_id': player, 'profile': profile}),
    ], bootstrap=True)


def vital_change(db, before, after, *, source='test-scenario', player='carlos',
                 vital='hp', cid='rpg-change', authorized=True):
    return db.append('world', cid, db.load('world').revision, [
        DomainEvent('PlayerVitalChanged', None, 'explicit test-only change',
                    db.load('world').time, {
            'player_id': player, 'vital': vital, 'previous': before,
            'current': after, 'source': source,
        }),
    ], rpg_authorized=authorized)


def test_01y_version_and_fresh_world_remains_unconfigured(world):
    db, clock, gw = world
    assert (SCHEMA_VERSION, RULES_VERSION) == (41, 56)
    assert gw.status().status == 'rpg_uninitialized'
    assert gw.status().details == {'configured': False}
    assert db.load('world').rpg_profiles == {}
    assert db.verify('world').to_dict() == db.load('world').to_dict()


def test_bootstrap_is_opt_in_known_vs_unknown_player_only(world):
    db, clock, gw = world
    saved = initialize(db)
    result = gw.status()
    assert result.status == 'rpg_status'
    assert result.details['configured'] is True
    p = result.details['profile']
    assert p['vitals']['hp'] == {'current': 12, 'max': 12}
    assert p['vitals']['st'] == {'current': 7, 'max': 10}
    assert p['vitals']['mp'] == {'current': None, 'max': None}
    assert p['xp_current'] == 3 and p['xp_goal'] is None
    assert p['level'] is None
    assert p['attributes'] == {'focus': 5}
    assert p['inventory'] == {} and p['equipment'] == {}
    assert saved.rpg_profiles['carlos']['vitals']['hp']['current'] == 12
    assert db.verify('world').to_dict() == saved.to_dict()


def test_mutating_read_result_cannot_mutate_replay_projection(world):
    db, clock, gw = world
    initialize(db)
    details = gw.status().details
    details['profile']['vitals']['hp']['current'] = 0
    details['profile']['attributes']['focus'] = 999
    assert gw.status().details['profile']['vitals']['hp']['current'] == 12
    assert gw.status().details['profile']['attributes']['focus'] == 5
    assert db.verify('world').to_dict() == db.load('world').to_dict()


def test_invalid_initializer_cannot_invent_items_or_impersonate_npc(world):
    db, clock, gw = world
    old = db.load('world').to_dict()
    bad_profiles = []
    a = fixture_profile()
    a['inventory'] = {'coin': 100}
    bad_profiles.append(a)
    a = fixture_profile()
    a['equipment'] = {'weapon': 'sword'}
    bad_profiles.append(a)
    a = fixture_profile()
    a['vitals']['hp'] = {'current': 15, 'max': 12}
    bad_profiles.append(a)
    a = fixture_profile()
    a['vitals']['mp'] = {'current': 3, 'max': None}
    bad_profiles.append(a)
    a = fixture_profile()
    a['attributes'] = {'bad': True}
    bad_profiles.append(a)
    a = fixture_profile()
    a['vitals']['hp'] = {'current': -1, 'max': 12}
    bad_profiles.append(a)
    for i, p in enumerate(bad_profiles):
        with pytest.raises(InvalidEvent):
            initialize(db, profile=p, cid=f'invalid-init-{i}')
        assert db.load('world').to_dict() == old
    with pytest.raises(InvalidEvent, match='player'):
        initialize(db, player='nora', cid='npc-spoof')
    assert db.load('world').to_dict() == old


def test_duplicate_init_and_bootstrap_false_rejected_atomically(world):
    db, clock, gw = world
    saved = initialize(db)
    with pytest.raises(InvalidEvent):
        initialize(db, cid='second-init')
    with pytest.raises(InvalidEvent):
        db.append('world', 'untrusted-init', db.load('world').revision, [
            DomainEvent('PlayerRPGInitialized', None, 'no bootstrap', 0, {
                'player_id': 'carlos', 'profile': fixture_profile()})
        ])
    assert db.load('world').to_dict() == saved.to_dict()


def test_vital_change_requires_distinct_trusted_capability_and_session(world):
    db, clock, gw = world
    initialize(db)
    original = db.load('world').to_dict()
    with pytest.raises(InvalidEvent, match='trusted'):
        vital_change(db, 12, 10, authorized=False)
    assert db.load('world').to_dict() == original
    result = vital_change(db, 12, 10)
    assert result.rpg_profiles['carlos']['vitals']['hp']['current'] == 10
    assert gw.status().details['profile']['vitals']['hp']['current'] == 10
    assert db.verify('world').to_dict() == result.to_dict()
    clock.close_session('world')
    with pytest.raises(InvalidEvent, match='active'):
        vital_change(db, 10, 9, cid='closed')
    assert db.load('world').to_dict() == result.to_dict()


def test_vital_change_rejects_forgery_overflow_unknown_and_noop(world):
    db, clock, gw = world
    initialize(db)
    old = db.load('world').to_dict()
    cases = [
        (11, 9, 'test-scenario', 'carlos', 'hp'),
        (12, 13, 'test-scenario', 'carlos', 'hp'),
        (12, -1, 'test-scenario', 'carlos', 'hp'),
        (12, 12, 'test-scenario', 'carlos', 'hp'),
        (12, 11, 'fake-combat', 'carlos', 'hp'),
        (12, 11, 'test-scenario', 'nora', 'hp'),
        (0, 1, 'test-scenario', 'carlos', 'mp'),
        (12, 11, 'test-scenario', 'carlos', 'xp_current'),
        (True, 11, 'test-scenario', 'carlos', 'hp'),
    ]
    for i, (prev, cur, src, player, vital) in enumerate(cases):
        with pytest.raises(InvalidEvent):
            vital_change(db, prev, cur, source=src, player=player,
                         vital=vital, cid=f'bad-change-{i}')
        assert db.load('world').to_dict() == old


def test_atomic_multi_event_rollback_and_duplicate_id(world):
    db, clock, gw = world
    initialize(db)
    before = db.load('world').to_dict()
    event1 = DomainEvent('PlayerVitalChanged', None, 'first change', 0, {
        'player_id':'carlos', 'vital':'hp', 'previous':12,
        'current':10, 'source':'test-scenario'})
    invalid = DomainEvent('PlayerVitalChanged', None, 'invalid second', 0, {
        'player_id':'carlos', 'vital':'hp', 'previous':12,
        'current':8, 'source':'test-scenario'})
    with pytest.raises(InvalidEvent):
        db.append('world', 'partial', before['revision'],
                  [event1, invalid], rpg_authorized=True)
    assert db.load('world').to_dict() == before
    vital_change(db, 12, 10, cid='once')
    stable = db.load('world').to_dict()
    with pytest.raises(DuplicateCommand):
        vital_change(db, 10, 9, cid='once')
    assert db.load('world').to_dict() == stable
    with pytest.raises(RevisionConflict):
        db.append('world', 'old-revision', before['revision'],
                  [event1], rpg_authorized=True)


def test_incapable_of_arbitrary_xp_level_and_inventory_changes(world):
    db, clock, gw = world
    initialize(db)
    old = db.load('world').to_dict()
    for i, event_type in enumerate(('PlayerXPChanged', 'PlayerLevelChanged',
                                    'PlayerItemCreated', 'PlayerEquipmentChanged')):
        with pytest.raises(InvalidEvent):
            db.append('world', f'unsupported-{i}', old['revision'], [
                DomainEvent(event_type, None, 'not implemented', 0, {
                    'player_id': 'carlos', 'value': 999})], rpg_authorized=True)
    assert db.load('world').to_dict() == old


def test_owner_only_no_npc_leak_and_two_players(world):
    db, clock, gw = world
    initialize(db)
    db.append('world', 'player2', db.load('world').revision, [
        DomainEvent('EntityCreated', None, 'second player', 0, {
            'id': 'second', 'name':'Second', 'location_id':'market',
            'controller':'player'})], bootstrap=True)
    second = PlayerGateway(db, clock, world_id='world', player_id='second')
    assert second.status().status == 'rpg_uninitialized'
    initialize(db, player='second', profile=unknown_profile(), cid='init2')
    assert second.status().details['profile']['vitals']['hp']['current'] is None
    assert gw.status().details['profile']['vitals']['hp']['current'] == 12
    with pytest.raises(PermissionError):
        PlayerGateway(db, clock, world_id='world', player_id='basim').status()


def test_snapshot_reopen_verify_and_integrity_check(tmp_path):
    path = tmp_path / 'rpg-reopen.sqlite'
    with SQLiteEventStore(path) as db:
        setup_player_demo_world(db)
        clock = TimeEngine(db)
        clock.open_session('world')
        gw = PlayerGateway(db, clock, world_id='world', player_id='carlos')
        initialize(db)
        vital_change(db, 12, 9)
        expected = gw.status().details
        db.snapshot('world')
        assert db.verify('world').to_dict() == db.load('world').to_dict()
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session('world')
        gw = PlayerGateway(db, clock, world_id='world', player_id='carlos')
        assert gw.status().details == expected
        assert db.verify('world').to_dict() == db.load('world').to_dict()
        assert db.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_untrusted_rpg_event_cannot_apply_directly(world):
    db, clock, gw = world
    before = db.load('world')
    event = DomainEvent('PlayerRPGInitialized', None, 'must be bootstrap', 0, {
        'player_id': 'carlos', 'profile': fixture_profile()})
    with pytest.raises(ValueError):
        apply_event(before, event)
    assert db.load('world').to_dict() == before.to_dict()
