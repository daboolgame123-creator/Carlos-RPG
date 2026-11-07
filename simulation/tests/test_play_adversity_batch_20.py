"""PLAY-20 adversarial tests: seven autonomous NPCs, finite food, two choices."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM / 'scenarios' / 'test_village'))
from play_adversity import run_adversity  # noqa: E402


@pytest.mark.parametrize('choice,expected', [
    ('stockpile', {'bread': 2, 'coin_copper': 4, 'food': 0}),
    ('share', {'bread': 0, 'coin_copper': 8, 'food': 0}),
])
def test_counterfactual_choices_keep_seven_npcs_and_do_not_mint_food(
        tmp_path, choice, expected):
    result = run_adversity(tmp_path / (choice + '.sqlite'),
                           choice, horizon_seconds=600)
    assert result['canonical_story'] is False
    assert result['disposable_test'] is True
    own = result['player_visible']['handoff_at_checkpoint']
    assert own['time'] == 600
    assert own['player_supplies']['balances'] == expected
    audit = result['test_audit_only']
    assert audit['npc_count'] == 7
    assert audit['npc_meals'] == 2
    assert audit['npc_food_left'] == 0
    assert audit['forest_wild_food_left'] == 0
    assert audit['square_wild_food_left'] == 2
    assert audit['npc_actions'] >= 7
    assert audit['bread_and_coin_conserved']
    assert audit['wild_food_conserved']
    assert audit['npc_owned_food_conserved']
    assert audit['forage_depletion_accepted']
    assert all(audit['denials_without_state_mutation'][kind] for kind in (
        'busy_or_exhausted_seller', 'trade_during_travel',
        'remote_trade', 'fifth_forage', 'fifth_meal',
        'repeated_meal_command', 'stale_revision'))
    assert result['restart'] == {
        'sqlite_verified': True, 'handoff_unchanged_on_reopen': True,
        'no_wall_clock_advance': True,
        'no_duplicate_meal': True, 'no_stale_revision': True,
        'time_after_explicit_resume_wait': 610,
    }


def test_one_world_is_deterministic_across_independent_sqlite_files(tmp_path):
    a = run_adversity(tmp_path / 'a.sqlite', 'stockpile', horizon_seconds=600)
    b = run_adversity(tmp_path / 'b.sqlite', 'stockpile', horizon_seconds=600)
    assert a == b


def test_adversity_player_handoff_excludes_private_npc_state(tmp_path):
    report = run_adversity(tmp_path / 'privacy.sqlite', 'share',
                           horizon_seconds=600)
    view = json.dumps(report['player_visible'], ensure_ascii=False)
    for hidden in (
        '"npcs"', '"beliefs"', '"goals"', '"needs"',
        '"relations"', '"injuries"', '"market_trades"',
        '"consumptions"', '"survival_progress"',
        '"npc_food_left"', '"npc_actions"', '"npc_meals"',
    ):
        assert hidden not in view
    assert report['test_audit_only']['npc_count'] == 7


@pytest.mark.parametrize('bad_choice,bad_seconds', [
    ('not-a-path', 600), ('share', 290),
    ('share', 86401), ('share', True), ('share', '600'),
])
def test_adversity_rejects_invalid_horizon_or_choice_before_world_creation(
        tmp_path, bad_choice, bad_seconds):
    path = tmp_path / 'not-created.sqlite'
    with pytest.raises(ValueError):
        run_adversity(path, bad_choice, horizon_seconds=bad_seconds)
    assert not path.exists()



def test_seven_npcs_can_leave_without_carlos_and_cannot_be_addressed_remotely(tmp_path):
    """Contrast scarce-food mode with the existing normal-world travel policy."""
    from carlos_sim.resumable_play import ResumableTestSession
    from carlos_sim.store import InvalidEvent
    from living_player_fixture import (
        WORLD, PLAYER, PEOPLE, living_player_gateway,
        setup_living_foraging_world,
    )

    with ResumableTestSession.create(
        tmp_path / 'moving.sqlite', WORLD, PLAYER,
        setup_living_foraging_world, disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        db, gateway = session.store, session.gateway
        start = db.load(WORLD)
        assert len(start.npcs) == len(PEOPLE) == 7
        before_location = {who: start.entities[who]['location_id']
                           for who, *_ in PEOPLE}
        advance = gateway.wait(201, command_id='npc-independent-travel',
                               expected_revision=start.revision)
        assert advance.time == 201
        state = db.load(WORLD)
        assert state.travels, 'normal village should contain autonomous NPC trips'
        assert any(t['npc_id'] in before_location for t in state.travels.values())
        for trip in state.travels.values():
            route = state.routes[trip['route_id']]
            assert {trip['origin'], trip['destination']} == {
                route['a'], route['b']}
            assert trip['due'] - trip['start'] == route['seconds']
            if trip['status'] == 'traveling':
                assert trip['arrived_at'] is None
                assert state.entities[trip['npc_id']]['location_id'] == trip['origin']
            else:
                assert trip['status'] == 'arrived'
                assert trip['arrived_at'] == trip['due']
        scene = gateway.inspect()
        local = {person['id'] for person in scene.details['occupants']}
        remote = next(who for who in state.npcs if who not in local)
        before = db.load(WORLD).to_dict()
        with pytest.raises(InvalidEvent):
            gateway.interact(remote, kind='greeting', text='Hello',
                             command_id='cannot-talk-remote-npc',
                             expected_revision=state.revision)
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before


def test_exhausted_autonomy_event_budget_rolls_back_without_partial_tick(tmp_path):
    """The command may not commit some NPC moves/actions and omit the rest."""
    from carlos_sim import LivingWorldEngine
    from carlos_sim.resumable_play import ResumableTestSession
    from carlos_sim.time_engine import AdvanceLimitExceeded
    from living_player_fixture import (
        WORLD, PLAYER, living_player_gateway, setup_living_foraging_world,
    )

    with ResumableTestSession.create(
        tmp_path / 'bounded.sqlite', WORLD, PLAYER,
        setup_living_foraging_world, disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(session.store, session.clock))
        db = session.store
        before = db.load(WORLD).to_dict()
        bounded = LivingWorldEngine(
            db, session.clock, max_events_per_advance=1,
            navigation_enabled=True, social_enabled=True,
        )
        with pytest.raises(AdvanceLimitExceeded):
            bounded.advance(
                WORLD, seconds=201, command_id='player-wait:over-budget',
                expected_revision=before['revision'], player_observer_id=PLAYER,
            )
        assert db.verify(WORLD).to_dict() == before
        assert db.db.execute(
            'SELECT COUNT(*) FROM commands WHERE world_id=? AND command_id=?',
            (WORLD, 'player-wait:over-budget')).fetchone()[0] == 0
        # A fresh legitimate command succeeds after the rejected attempt.
        advanced = session.gateway.wait(
            1, command_id='valid-after-over-budget',
            expected_revision=before['revision'])
        assert advanced.time == 1
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
