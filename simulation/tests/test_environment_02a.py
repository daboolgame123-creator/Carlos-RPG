"""02-A finite environmental replenishment: clock, authorization and replay."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, WorldState, SQLiteEventStore, TimeEngine, LivingWorldEngine
)
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION, apply_event
from carlos_sim.store import (
    InvalidEvent, RevisionConflict, DuplicateCommand, UnsupportedVersion,
)
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded
from carlos_sim.backup import create_backup_bundle, verify_backup_bundle, restore_backup_bundle
from test_gathering_autonomy import make_world


def ev(kind, data, at=0):
    return DomainEvent(kind, None, 'finite test environment', at, data)


def setup(db, *, wild=0, reserve=2, period=60, capacity=2,
          configure=True, second=False):
    db.create_world('world')
    events = [ev('LocationCreated', {'id': 'grove', 'name': 'Grove'})]
    if wild is not None:
        events.append(ev('ResourceChanged', {
            'owner_id': 'grove', 'resource': 'wild_food',
            'previous': None, 'current': wild, 'source': 'initialization',
        }))
    if reserve is not None:
        events.append(ev('ResourceChanged', {
            'owner_id': 'grove', 'resource': 'regrowth_reserve',
            'previous': None, 'current': reserve, 'source': 'initialization',
        }))
    if configure:
        events.append(ev('EnvironmentalCycleConfigured', {
            'id': 'grove-cycle', 'site_id': 'grove',
            'period_seconds': period, 'capacity': capacity,
        }))
    if second:
        events.extend([
            ev('LocationCreated', {'id': 'woods', 'name': 'Woods'}),
            ev('ResourceChanged', {
                'owner_id':'woods', 'resource':'wild_food','previous':None,
                'current':0,'source':'initialization'}),
            ev('ResourceChanged', {
                'owner_id':'woods','resource':'regrowth_reserve',
                'previous':None,'current':1,'source':'initialization'}),
            ev('EnvironmentalCycleConfigured', {
                'id':'woods-cycle','site_id':'woods','period_seconds':30,'capacity':1}),
        ])
    db.append('world', 'bootstrap', 0, events, bootstrap=True)


def tick(db, clock, seconds, name):
    return clock.advance('world', seconds=seconds, command_id=name,
                         expected_revision=db.load('world').revision).state


@pytest.fixture
def world(tmp_path):
    with SQLiteEventStore(tmp_path / 'environment.sqlite') as db:
        setup(db)
        clock = TimeEngine(db)
        clock.open_session('world')
        yield db, clock


def test_opt_in_is_required_no_missing_stock_is_invented(tmp_path):
    assert (SCHEMA_VERSION, RULES_VERSION) == (36, 48)
    with SQLiteEventStore(tmp_path / 'unconfigured.sqlite') as db:
        setup(db, configure=False, reserve=None, wild=0)
        clock = TimeEngine(db)
        clock.open_session('world')
        original = db.load('world')
        assert original.environment_cycles == {}
        result = tick(db, clock, 300, 'wait')
        assert result.resources['grove']['wild_food'] == 0
        assert result.resources['grove'].get('regrowth_reserve') is None
        assert result.environment_cycles == {}
        assert db.verify('world').to_dict() == result.to_dict()


def test_one_to_one_conservation_and_full_capacity_no_cost(world):
    db, clock = world
    start = db.load('world')
    assert start.resources['grove']['wild_food'] == 0
    assert start.resources['grove']['regrowth_reserve'] == 2
    assert start.scheduled['environment:grove-cycle:1']['due'] == 60
    at_59 = tick(db, clock, 59, '59')
    assert at_59.resources['grove']['wild_food'] == 0
    first = tick(db, clock, 1, '60')
    assert first.resources['grove']['wild_food'] == 1
    assert first.resources['grove']['regrowth_reserve'] == 1
    second = tick(db, clock, 60, '120')
    assert second.resources['grove']['wild_food'] == 2
    assert second.resources['grove']['regrowth_reserve'] == 0
    assert second.environment_cycles['grove-cycle']['converted'] == 2
    full = tick(db, clock, 600, 'full')
    assert full.resources['grove']['wild_food'] == 2
    assert full.resources['grove']['regrowth_reserve'] == 0
    assert full.environment_cycles['grove-cycle']['ticks'] == 2
    assert full.environment_cycles['grove-cycle']['next_due'] is None
    assert not any('__environment_cycle' in x['payload'] for x in full.scheduled.values())
    assert full.environment_cycles['grove-cycle']['converted'] == 2
    assert db.verify('world').to_dict() == full.to_dict()


def test_exhaustion_stops_noop_tick_storm_and_source_zero_is_quiet(tmp_path):
    with SQLiteEventStore(tmp_path / 'empty.sqlite') as db:
        setup(db, wild=0, reserve=0, period=1)
        clock = TimeEngine(db, max_events_per_advance=3)
        clock.open_session('world')
        initial = db.load('world')
        assert initial.environment_cycles['grove-cycle']['next_due'] is None
        assert initial.scheduled == {}
        after = tick(db, clock, 10_000, 'long-time')
        assert after.time == 10_000
        assert after.environment_cycles['grove-cycle']['ticks'] == 0
        assert after.resources['grove']['wild_food'] == 0
        assert db.verify('world').to_dict() == after.to_dict()

    with SQLiteEventStore(tmp_path / 'spent.sqlite') as db:
        setup(db, wild=0, reserve=1, period=1)
        clock = TimeEngine(db, max_events_per_advance=5)
        clock.open_session('world')
        after = tick(db, clock, 1_000, 'long-time')
        assert after.environment_cycles['grove-cycle']['ticks'] == 1
        assert after.environment_cycles['grove-cycle']['converted'] == 1
        assert after.environment_cycles['grove-cycle']['next_due'] is None
        assert not after.scheduled
        assert after.resources['grove']['wild_food'] == 1
        assert after.resources['grove']['regrowth_reserve'] == 0
        assert db.verify('world').to_dict() == after.to_dict()


def test_full_site_does_not_spend_reserve_and_no_offline_time(tmp_path):
    with SQLiteEventStore(tmp_path / 'pause.sqlite') as db:
        setup(db, wild=2, reserve=3)
        clock = TimeEngine(db)
        clock.open_session('world')
        clock.close_session('world')
        with pytest.raises(SessionClosed):
            tick(db, clock, 60, 'closed')
        assert db.load('world').time == 0
        clock.open_session('world')
        full = tick(db, clock, 180, 'full')
        assert full.environment_cycles['grove-cycle']['ticks'] == 3
        assert full.resources['grove']['regrowth_reserve'] == 3
        assert full.resources['grove']['wild_food'] == 2


def test_unknown_or_invalid_source_blocks_configuration_atomically(tmp_path):
    for i, (wild, reserve, period, cap) in enumerate((
        (None, 2, 60, 2),
        (0, None, 60, 2),
        (3, 3, 60, 2),
        (0, 2, 0, 2),
        (0, 2, True, 2),
        (0, 2, 60, 0),
        (0, 2, 60, True),
        (0, 2, 2**31, 2),
    )):
        with SQLiteEventStore(tmp_path / f'bad-{i}.sqlite') as db:
            db.create_world('world')
            old = db.load('world').to_dict()
            events = [ev('LocationCreated', {'id': 'grove','name':'Grove'})]
            if wild is not None:
                events.append(ev('ResourceChanged', {
                    'owner_id':'grove','resource':'wild_food',
                    'previous':None,'current':wild,'source':'initialization'}))
            if reserve is not None:
                events.append(ev('ResourceChanged', {
                    'owner_id':'grove','resource':'regrowth_reserve',
                    'previous':None,'current':reserve,'source':'initialization'}))
            events.append(ev('EnvironmentalCycleConfigured', {
                'id':'bad','site_id':'grove',
                'period_seconds':period,'capacity':cap}))
            with pytest.raises(InvalidEvent):
                db.append('world', 'bad', 0, events, bootstrap=True)
            assert db.load('world').to_dict() == old
            assert db.db.execute('SELECT count(*) FROM commands').fetchone()[0] == 0


def test_forged_late_or_second_environment_config_rejected(world):
    db, clock = world
    baseline = db.load('world').to_dict()
    config = ev('EnvironmentalCycleConfigured', {
        'id':'new','site_id':'grove','period_seconds':60,'capacity':2})
    with pytest.raises(InvalidEvent):
        db.append('world', 'duplicate-site', baseline['revision'], [config], bootstrap=True)
    with pytest.raises(InvalidEvent):
        db.append('world', 'no-bootstrap', baseline['revision'], [config])
    assert db.load('world').to_dict() == baseline
    tick(db, clock, 10, 'time')
    with pytest.raises(InvalidEvent):
        db.append('world', 'late-bootstrap', db.load('world').revision,
                  [config], bootstrap=True)


def test_generic_schedule_forgery_or_cancel_and_early_fire_blocked(world):
    db, clock = world
    base = db.load('world')
    wrong = ev('ScheduledEventCreated', {
        'id':'fake','due':20, 'order':base.next_schedule_order,
        'kind':'signal','interrupt':False,
        'payload':{'__environment_cycle':'grove-cycle','tick':1},
    })
    with pytest.raises(InvalidEvent):
        db.append('world', 'forgery', base.revision, [wrong])
    with pytest.raises(InvalidEvent):
        clock.cancel('world', 'environment:grove-cycle:1',
                     command_id='cancel', expected_revision=base.revision)
    with pytest.raises(InvalidEvent):
        db.append('world', 'early', base.revision, [
            ev('ScheduledEventFired', {'id':'environment:grove-cycle:1'})
        ], clock_authorized=True)
    assert db.load('world').to_dict() == base.to_dict()


def test_two_sites_have_independent_known_reserves(tmp_path):
    with SQLiteEventStore(tmp_path / 'two.sqlite') as db:
        setup(db, second=True)
        clock = TimeEngine(db)
        clock.open_session('world')
        result = tick(db, clock, 90, 'advance')
        assert result.resources['woods']['wild_food'] == 1
        assert result.resources['woods']['regrowth_reserve'] == 0
        assert result.resources['grove']['wild_food'] == 1
        assert result.resources['grove']['regrowth_reserve'] == 1
        assert result.environment_cycles['woods-cycle']['ticks'] == 1
        assert result.environment_cycles['woods-cycle']['next_due'] is None
        assert result.environment_cycles['grove-cycle']['ticks'] == 1
        assert db.verify('world').to_dict() == result.to_dict()


def test_split_vs_lumped_time_and_restart_replay(tmp_path):
    results = []
    for suffix, durations in (('lumped',(240,)),('split',(5,55,60,60,60))):
        path = tmp_path / f'{suffix}.sqlite'
        with SQLiteEventStore(path) as db:
            setup(db)
            clock = TimeEngine(db)
            clock.open_session('world')
            for i, seconds in enumerate(durations):
                tick(db, clock, seconds, f'{suffix}-{i}')
            last = db.load('world').to_dict()
            db.snapshot('world')
            assert db.verify('world').to_dict() == last
        with SQLiteEventStore(path) as reopened:
            assert reopened.verify('world').to_dict() == last
            results.append({
                'time': last['time'],
                'resources': last['resources'],
                'environment_cycles': last['environment_cycles'],
                'scheduled_due': tuple(sorted(last['scheduled'])),
            })
    assert results[0] == results[1]


def test_duplicate_clock_request_stale_revision_and_max_events_roll_back(world):
    db, clock = world
    base = db.load('world').to_dict()
    limited = TimeEngine(db, max_events_per_advance=3)
    with pytest.raises(AdvanceLimitExceeded):
        limited.advance('world', seconds=600, command_id='overflow',
                        expected_revision=base['revision'])
    assert db.load('world').to_dict() == base
    result = tick(db, clock, 60, 'once')
    with pytest.raises(DuplicateCommand):
        clock.advance('world', seconds=60, command_id='once',
                      expected_revision=result.revision)
    with pytest.raises(RevisionConflict):
        clock.advance('world', seconds=60, command_id='stale',
                      expected_revision=base['revision'])
    assert db.load('world').to_dict() == result.to_dict()


def test_invalid_snapshot_rejected_without_guessing_or_silent_normalizing(world):
    db, clock = world
    base = db.load('world').to_dict()
    for mode in ('absent','negative','bad-id','fake-appointment','bad-capacity'):
        corrupt = db.load('world').to_dict()
        if mode == 'absent':
            del corrupt['environment_cycles']
        elif mode == 'negative':
            corrupt['environment_cycles']['grove-cycle']['converted'] = -1
        elif mode == 'bad-id':
            corrupt['environment_cycles']['grove-cycle']['next_due'] = 999
        elif mode == 'fake-appointment':
            corrupt['scheduled']['environment:grove-cycle:1']['payload']['tick'] = 2
        else:
            corrupt['environment_cycles']['grove-cycle']['capacity'] = 0
        with pytest.raises(ValueError):
            WorldState.from_dict(corrupt)
    assert db.load('world').to_dict() == base


def test_living_world_gathering_competes_for_replenished_food_in_seven_npcs(tmp_path):
    with SQLiteEventStore(tmp_path / 'village.sqlite') as db:
        make_world(db, grove_stock=0, square_stock=0)
        db.append('r','env-init',db.load('r').revision,[
            ev('ResourceChanged',{
                'owner_id':'grove','resource':'regrowth_reserve',
                'previous':None,'current':2,'source':'initialization'}),
            ev('EnvironmentalCycleConfigured',{
                'id':'grove-cycle','site_id':'grove',
                'period_seconds':60,'capacity':2}),
        ], bootstrap=True)
        clock = TimeEngine(db)
        clock.open_session('r')
        s = tick_village(db, clock, 120)
        assert s.resources['grove']['wild_food'] == 2
        assert s.resources['grove']['regrowth_reserve'] == 0
        run = LivingWorldEngine(db, clock, gathering_enabled=True).advance(
            'r', seconds=90, command_id='gather',
            expected_revision=db.load('r').revision)
        end = run.state
        assert len(end.npcs) == 7
        assert len(end.gatherings) >= 1
        assert end.resources['grove']['wild_food'] == 0
        assert end.resources['grove']['regrowth_reserve'] == 0
        assert sum(end.resources[x]['food'] for x in end.npcs) + end.resources['grove']['wild_food'] == 4
        assert db.verify('r').to_dict() == end.to_dict()


def tick_village(db, clock, seconds):
    return clock.advance('r', seconds=seconds, command_id='prepare-food',
                         expected_revision=db.load('r').revision).state


def test_backup_restore_15_22_replay_remains_exact(world, tmp_path):
    db, clock = world
    original = tick(db, clock, 180, 'advance').to_dict()
    bundle = tmp_path / 'environment-backup'
    git_ref = '1225ae066f22bc2688a583d46e63ceda80558a07'
    manifest = create_backup_bundle(db, 'world', bundle, code_commit=git_ref)
    assert manifest["schema"] == 36 and manifest["rules"] == 48
    assert verify_backup_bundle(bundle) == manifest
    restored = tmp_path / 'restored.sqlite'
    restore_backup_bundle(bundle, restored)
    with SQLiteEventStore(restored) as recovered:
        assert recovered.verify('world').to_dict() == original
        assert recovered.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_raw_untrusted_config_event_never_changes_projection(world):
    db, clock = world
    before = db.load('world')
    with pytest.raises(ValueError):
        apply_event(before, ev('EnvironmentalCycleConfigured', {
            'id':'fake','site_id':'grove','period_seconds':5,'capacity':2}))
    assert db.load('world').to_dict() == before.to_dict()
