"""Phase 01-N: strict equivalence guards around faster immutable projections.

Performance belongs in benchmark output, not a brittle unit-test threshold.
These tests compare the optimized validated snapshot decoder with the public
constructor's independent JSON-validation/freezing path.
"""
import json
from types import MappingProxyType

import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, WorldState,
                        LivingWorldEngine, apply_event, canonical_hash)
from carlos_sim.domain import canonical
from carlos_sim.store import InvalidEvent, IntegrityError, RevisionConflict
from test_survival import make


def _sample(db):
    clock = make(db, names=('nora', 'basim'))
    engine = LivingWorldEngine(db, clock, survival_enabled=True)
    advance = engine.advance('test', seconds=360, command_id='sample-advance',
                             expected_revision=db.load('test').revision)
    return advance.state


def test_optimized_decoder_matches_public_constructor_for_real_world(tmp_path):
    with SQLiteEventStore(tmp_path / 'world.db') as db:
        state = _sample(db)
        raw = state.to_dict()
        fast = WorldState.from_dict(raw)
        constructor = WorldState(**raw)
        assert fast.to_dict() == constructor.to_dict() == state.to_dict()
        assert canonical_hash(fast.to_dict()) == canonical_hash(constructor.to_dict())
        assert fast.revision == constructor.revision == state.revision


def test_snapshot_decoder_detaches_all_nested_caller_data(tmp_path):
    with SQLiteEventStore(tmp_path / 'isolation.db') as db:
        original = _sample(db).to_dict()
        decoded = WorldState.from_dict(original)
        original['npcs']['nora']['needs']['hunger'] = 100
        original['entities']['nora']['location_id'] = 'wrong-place'
        original['survival_progress']['nora']['hunger_seconds'] = 999
        assert decoded.npcs['nora']['needs']['hunger'] != 100
        assert decoded.entities['nora']['location_id'] != 'wrong-place'
        assert decoded.survival_progress['nora']['hunger_seconds'] != 999
        with pytest.raises(TypeError):
            decoded.npcs['nora']['needs']['hunger'] = 90
        with pytest.raises(TypeError):
            decoded.survival_progress['nora']['fatigue_seconds'] = 100


def test_to_dict_returns_a_fully_detached_json_tree(tmp_path):
    with SQLiteEventStore(tmp_path / 'mutable-copy.db') as db:
        state = _sample(db)
        first = state.to_dict()
        second = state.to_dict()
        first['actions'].clear()
        first['npcs']['nora']['needs']['hunger'] = 100
        first['survival_progress']['nora']['hunger_seconds'] = 0
        assert state.to_dict() == second
        assert first != second
        assert json.loads(json.dumps(second)) == second


def test_to_dict_is_identical_to_old_json_roundtrip_semantics(tmp_path):
    with SQLiteEventStore(tmp_path / 'old-semantics.db') as db:
        state = _sample(db)
        thawed = state.to_dict()
        baseline = json.loads(canonical({key: getattr(state, key)
                                         for key in state.__dataclass_fields__}))
        assert thawed == baseline
        assert canonical(thawed) == canonical(baseline)


def test_mapping_proxy_nested_array_semantics_are_unchanged():
    from carlos_sim.domain import _thaw
    frozen = MappingProxyType({'nested': (MappingProxyType({'count': 7}),
                                          [1, 2, 3])})
    assert _thaw(frozen) == {'nested': [{'count': 7}, [1, 2, 3]]}
    assert canonical(frozen) == '{"nested":[{"count":7},[1,2,3]]}'


def test_finite_json_validation_cannot_be_bypassed(tmp_path):
    with SQLiteEventStore(tmp_path / 'finite.db') as db:
        raw = _sample(db).to_dict()
        for malformed in (float('nan'), float('inf'), -float('inf'), object()):
            candidate = json.loads(json.dumps(raw))
            candidate['entities']['nora']['name'] = malformed
            with pytest.raises((ValueError, TypeError)):
                WorldState.from_dict(candidate)


def test_public_constructor_still_rejects_unportable_inputs():
    with pytest.raises(ValueError, match='finite JSON'):
        WorldState('test', entities={'npc': {'name': float('nan')}})
    with pytest.raises(ValueError, match='finite JSON'):
        WorldState('test', entities={'npc': {'name': object()}})


def test_decoder_never_accepts_malformed_state_shape(tmp_path):
    with SQLiteEventStore(tmp_path / 'shape.db') as db:
        raw = _sample(db).to_dict()
        for field in ('revision', 'time', 'schema_version', 'rules_version',
                      'entities', 'resources', 'npcs', 'survival_progress'):
            invalid = json.loads(json.dumps(raw))
            del invalid[field]
            with pytest.raises(ValueError):
                WorldState.from_dict(invalid)
        invalid = json.loads(json.dumps(raw))
        invalid['unexpected'] = 'do not accept extra fields'
        with pytest.raises(ValueError):
            WorldState.from_dict(invalid)


def test_failed_batch_does_not_leak_mutations(tmp_path):
    with SQLiteEventStore(tmp_path / 'atomic.db') as db:
        make(db)
        before = db.load('test')
        valid = DomainEvent('TimeAdvanced', None, 'valid', 300,
                            {'from': 0, 'to': 300})
        invalid = DomainEvent('TimeAdvanced', None, 'rewind', 10,
                              {'from': 300, 'to': 10})
        with pytest.raises(InvalidEvent):
            db.append('test', 'reject-all', before.revision, [valid, invalid],
                      clock_authorized=True, survival_authorized=True)
        assert db.load('test').to_dict() == before.to_dict()
        assert not db.db.execute('SELECT * FROM commands WHERE command_id=?',
                                 ('reject-all',)).fetchone()


def test_snapshot_and_genesis_replay_equal_after_many_actions(tmp_path):
    with SQLiteEventStore(tmp_path / 'replay.db') as db:
        clock = make(db, names=('nora', 'basim'))
        engine = LivingWorldEngine(db, clock, survival_enabled=True)
        engine.advance('test', seconds=360, command_id='first',
                       expected_revision=db.load('test').revision)
        db.snapshot('test')
        engine.advance('test', seconds=360, command_id='second',
                       expected_revision=db.load('test').revision)
        assert db.load('test').to_dict() == db.load('test', use_snapshot=False).to_dict()
        assert db.verify('test').to_dict() == db.load('test').to_dict()


def test_corrupt_snapshot_hash_remains_detected(tmp_path):
    with SQLiteEventStore(tmp_path / 'tamper.db') as db:
        _sample(db)
        db.snapshot('test')
        db.db.execute("UPDATE snapshots SET hash='corrupted'")
        with pytest.raises(IntegrityError):
            db.load('test')


def test_state_matches_after_full_replay_between_independent_stores(tmp_path):
    result = []
    for i in range(2):
        with SQLiteEventStore(tmp_path / f'deterministic-{i}.db') as db:
            world = _sample(db)
            result.append((canonical_hash(db.verify('test').to_dict()),
                           canonical_hash(world.to_dict())))
    assert result[0] == result[1]


def test_no_unauthorized_resource_or_time_behavior_change(tmp_path):
    with SQLiteEventStore(tmp_path / 'security.db') as db:
        clock = make(db)
        before = db.load('test')
        with pytest.raises(InvalidEvent):
            db.append('test', 'clock-forgery', before.revision, [
                DomainEvent('TimeAdvanced', None, 'forgery', 120,
                            {'from': 0, 'to': 120})])
        with pytest.raises(InvalidEvent):
            db.append('test', 'resource-forgery', before.revision, [
                DomainEvent('ResourceChanged', 'nora', 'forgery', 0,
                            {'owner_id': 'nora', 'resource': 'food',
                             'previous': None, 'current': 100,
                             'source': 'initialization'})])
        assert db.load('test').to_dict() == before.to_dict()


def test_cached_projection_does_not_disclose_private_state_to_player(tmp_path):
    with SQLiteEventStore(tmp_path / 'player.db') as db:
        state = _sample(db)
        assert db.player_view('test') == {
            'world_id': 'test', 'time': state.time, 'revision': state.revision}


def test_full_engine_fixture_event_counts_are_unchanged():
    # The benchmark must not silently turn off decisions to appear fast.
    from pathlib import Path
    import sys
    scenarios = Path(__file__).resolve().parents[1] / 'scenarios' / 'test_village'
    sys.path.insert(0, str(scenarios))
    try:
        from bench_living_world import measure
        results = measure(5)
        assert results['actual_simulated_seconds'] == 60
        assert results['advance_events'] == 16  # 3 events per NPC + clock
    finally:
        sys.path.remove(str(scenarios))
