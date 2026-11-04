"""Phase 01-N: optimized immutable state copies retain strict event semantics."""
import json
import math
from types import MappingProxyType

import pytest

from carlos_sim import DomainEvent, WorldState, SQLiteEventStore, TimeEngine, apply_event, canonical_hash
from carlos_sim.store import InvalidEvent, IntegrityError


def event(kind, data, *, time=0, actor=None):
    return DomainEvent(kind, actor, 'performance regression test', time, data)


def state_with_nested_payload():
    first = apply_event(WorldState('test'), event('LocationCreated', {'id':'market','name':'Village'}))
    second = apply_event(first, event('EntityCreated', {'id':'nora', 'name':'Nora',
        'location_id':'market', 'controller':'npc'}))
    return apply_event(second, event('NPCConfigured', {
        'npc_id':'nora', 'role':'worker',
        'needs':{'fatigue':5,'hunger':20,'safety':0},
        'goals':{'earn':10,'explore':5,'survive':20}}), bootstrap=True)


def test_fast_projection_is_immutable_and_copy_is_deep():
    s = state_with_nested_payload()
    assert isinstance(s.npcs, MappingProxyType)
    assert isinstance(s.npcs['nora'], MappingProxyType)
    view = s.to_dict()
    view['npcs']['nora']['needs']['hunger'] = 99
    view['entities']['nora']['name'] = 'ANOTHER PERSON'
    view['locations'].clear()
    assert s.npcs['nora']['needs']['hunger'] == 20
    assert s.entities['nora']['name'] == 'Nora'
    assert s.locations['market']['name'] == 'Village'
    with pytest.raises(TypeError):
        s.npcs['nora']['needs']['hunger'] = 50


def test_fast_projection_matches_public_state_constructor_and_hash():
    s = state_with_nested_payload()
    expected = WorldState(**s.to_dict())
    assert s.to_dict() == expected.to_dict()
    assert canonical_hash(s.to_dict()) == canonical_hash(expected.to_dict())
    assert WorldState.from_dict(s.to_dict()).to_dict() == s.to_dict()


def test_fast_projection_detaches_from_untrusted_snapshot_input():
    data = state_with_nested_payload().to_dict()
    got = WorldState.from_dict(data)
    data['npcs']['nora']['needs']['hunger'] = 100
    data['locations']['market']['name'] = 'tampered'
    assert got.npcs['nora']['needs']['hunger'] == 20
    assert got.locations['market']['name'] == 'Village'


def test_direct_constructed_states_still_validate_json_scalars():
    for bad in (math.nan, math.inf, -math.inf, object()):
        with pytest.raises((ValueError, TypeError)):
            WorldState('w', time=bad).to_dict()
    with pytest.raises((ValueError, TypeError)):
        WorldState('w', entities={'strange': {'object':object()}})


def test_external_snapshot_keeps_schema_and_collection_validation():
    s = state_with_nested_payload().to_dict()
    for bad in ({'npcs': {'nora': {'invalid': True}}},
                {'revision': -1}, {'schema_version': 12345},
                {'survival_progress': {'nora': {'hunger_seconds': -1,'fatigue_seconds':0}}}):
        altered = json.loads(json.dumps(s))
        altered.update(bad)
        with pytest.raises((TypeError, ValueError)):
            WorldState.from_dict(altered)


def test_prior_state_unchanged_on_invalid_event():
    current = state_with_nested_payload()
    with pytest.raises(ValueError):
        apply_event(current, event('ResourceChanged', {
            'owner_id':'nora','resource':'food','previous':None,
            'current':500,'source':'consumption'}, actor='nora'))
    assert current.revision == 3
    assert current.resources == {}


def test_snapshot_corruption_is_still_detected(tmp_path):
    with SQLiteEventStore(tmp_path/'snapshot.sqlite') as db:
        db.create_world('world')
        TimeEngine(db).open_session('world')
        db.append('world','first',0,[event('LocationCreated', {'id':'market','name':'Market'})])
        db.snapshot('world')
        db.db.execute('UPDATE snapshots SET state=?', ('{}',))
        with pytest.raises(IntegrityError):
            db.load('world')


def test_batch_failure_preserves_atomic_revision(tmp_path):
    with SQLiteEventStore(tmp_path/'atomic.sqlite') as db:
        db.create_world('world')
        TimeEngine(db).open_session('world')
        with pytest.raises(InvalidEvent):
            db.append('world','batch',0,[
                event('LocationCreated', {'id':'market','name':'Market'}),
                event('LocationCreated', {'id':'market','name':'Duplicate'})])
        assert db.load('world').revision == 0
        assert db.db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 0


def test_projection_tuple_json_roundtrip_preserves_list_semantics():
    current = state_with_nested_payload()
    serialized = current.to_dict()
    assert isinstance(serialized['npcs']['nora']['delivery_history'], list)
    assert isinstance(current.npcs['nora']['delivery_history'], tuple)
    assert WorldState.from_dict(serialized).to_dict() == serialized
