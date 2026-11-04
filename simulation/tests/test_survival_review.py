"""Phase 01-M independent review: explicit planning and time integrity."""
from pathlib import Path

import pytest

from carlos_sim import (SQLiteEventStore, TimeEngine, LivingWorldEngine,
                        NPCService)
from test_survival import make, tick


def test_manual_npc_decision_can_use_same_critical_hunger_policy(tmp_path):
    with SQLiteEventStore(tmp_path / 'critical.sqlite') as db:
        clock = make(db, hunger=90)
        initial = db.load('test')
        decision = NPCService(db, clock, survival_enabled=True).decide(
            'test', 'nora', command_id='survival-intention',
            expected_revision=initial.revision)
        assert decision.action in ('rest', 'wait')
        assert db.load('test').npcs['nora']['last_decision']['action'] == decision.action
        assert db.load('test').time == 0
        assert db.load('test').survival_progress == {}
        out = LivingWorldEngine(db, clock, survival_enabled=True).advance(
            'test', seconds=1, command_id='execute',
            expected_revision=db.load('test').revision)
        assert out.state.actions['auto:nora:0']['action'] == decision.action
        assert db.verify('test').to_dict() == out.state.to_dict()


def test_legacy_npc_decision_stays_default_without_survival_flag(tmp_path):
    with SQLiteEventStore(tmp_path / 'legacy.sqlite') as db:
        clock = make(db, hunger=90)
        choice = NPCService(db, clock).decide(
            'test', 'nora', command_id='legacy-plan',
            expected_revision=db.load('test').revision)
        assert choice.action == 'work'
        # Existing recorded decisions remain authoritative, even when the
        # coordinator starts a different opt-in mode afterward.
        out = LivingWorldEngine(db, clock, survival_enabled=True).advance(
            'test', seconds=1, command_id='execute-manual',
            expected_revision=db.load('test').revision)
        assert out.state.actions['auto:nora:0']['action'] == 'work'
        assert db.verify('test').to_dict() == out.state.to_dict()


def test_noncritical_survival_manual_decision_is_not_overridden(tmp_path):
    with SQLiteEventStore(tmp_path / 'mild.sqlite') as db:
        clock = make(db, hunger=20)
        out = NPCService(db, clock, survival_enabled=True).decide(
            'test', 'nora', command_id='mild-plan',
            expected_revision=db.load('test').revision)
        assert out.action == 'work'
        assert db.verify('test').npcs['nora']['last_decision']['action'] == 'work'


def test_bad_survival_mode_types_are_rejected(tmp_path):
    with SQLiteEventStore(tmp_path / 'bad.sqlite') as db:
        clock = make(db)
        for flag in (0, 1, None, 'true', []):
            with pytest.raises(ValueError, match='survival_enabled'):
                NPCService(db, clock, survival_enabled=flag)


def test_survival_policy_intention_survives_database_restart(tmp_path):
    filename = tmp_path / 'restart.sqlite'
    with SQLiteEventStore(filename) as db:
        clock = make(db, hunger=95)
        planned = NPCService(db, clock, survival_enabled=True).decide(
            'test', 'nora', command_id='survival-policy',
            expected_revision=db.load('test').revision)
        db.snapshot('test')
        stored = db.load('test').to_dict()
    with SQLiteEventStore(filename) as db:
        assert db.verify('test').to_dict() == stored
        clock = TimeEngine(db)
        clock.open_session('test')
        result = LivingWorldEngine(db, clock, survival_enabled=True).advance(
            'test', seconds=1, command_id='after-restart',
            expected_revision=db.load('test').revision)
        assert result.state.actions['auto:nora:0']['action'] == planned.action
        assert db.verify('test').to_dict() == result.state.to_dict()


def test_manual_survival_planning_does_not_advance_elapsed_time(tmp_path):
    with SQLiteEventStore(tmp_path / 'time.sqlite') as db:
        clock = make(db, hunger=95)
        before = tick(db, 299, 'elapsed-before-intention')
        NPCService(db, clock, survival_enabled=True).decide(
            'test', 'nora', command_id='choose-at-299',
            expected_revision=before.revision)
        after = db.load('test')
        assert after.time == 299
        assert after.survival_progress['nora']['hunger_seconds'] == 299
        # No second metabolism charge on the decision event itself.
        later = tick(db, 1, 'elapsed-after-intention')
        assert later.survival_progress['nora']['hunger_seconds'] == 0
        assert later.npcs['nora']['needs']['hunger'] == 96
        assert db.verify('test').to_dict() == later.to_dict()
