"""Regression guards for recipient-private intent isolation in Phase 01-I."""
from pathlib import Path
from carlos_sim import (SQLiteEventStore, TimeEngine, NPCService,
                        LivingWorldEngine, choose_social_intent)
from test_social_autonomy import make_world


def test_private_recipient_intention_does_not_change_senders_social_choice(tmp_path):
    with SQLiteEventStore(tmp_path / 'private-intent.sqlite') as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session('village')
        initial = choose_social_intent(db.load('village'), 'aaron')
        assert initial is not None and initial.recipient_id == 'zora'
        NPCService(db, clock).decide('village', 'zora', command_id='zora-private',
                                     expected_revision=db.load('village').revision)
        # Zora is standing in the same public location. Only her private
        # unstarted activity intention changed; Aaron must not learn it.
        assert choose_social_intent(db.load('village'), 'aaron') == initial


def test_known_busy_peer_still_excluded_but_unstarted_intention_is_not(tmp_path):
    with SQLiteEventStore(tmp_path / 'three-npcs.sqlite') as db:
        make_world(db, names=('aaron', 'bella', 'zora'))
        clock = TimeEngine(db)
        clock.open_session('village')
        initial = choose_social_intent(db.load('village'), 'aaron')
        assert initial is not None and initial.recipient_id == 'bella'
        NPCService(db, clock).decide('village', 'bella', command_id='bella-private',
                                     expected_revision=db.load('village').revision)
        assert choose_social_intent(db.load('village'), 'aaron') == initial
        from carlos_sim import NPCActionService
        NPCActionService(db, clock).start('village', 'bella', 'bella-work',
                                         expected_revision=db.load('village').revision)
        after = choose_social_intent(db.load('village'), 'aaron')
        assert after is not None and after.recipient_id == 'zora'


def test_live_engine_can_greet_peer_with_private_pending_intention(tmp_path):
    with SQLiteEventStore(tmp_path / 'live.sqlite') as db:
        make_world(db)
        clock = TimeEngine(db)
        clock.open_session('village')
        NPCService(db, clock).decide('village', 'zora', command_id='private-plan',
                                     expected_revision=db.load('village').revision)
        out = LivingWorldEngine(db, clock, social_enabled=True).advance(
            'village', seconds=1, command_id='advance',
            expected_revision=db.load('village').revision)
        assert out.social_message_ids == ('auto-social:aaron:0',)
        assert out.state.social_messages['auto-social:aaron:0']['recipient'] == 'zora'
        assert any(a['npc_id'] == 'zora' for a in out.state.actions.values())
        assert db.verify('village').to_dict() == out.state.to_dict()
