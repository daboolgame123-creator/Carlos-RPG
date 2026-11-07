"""PLAY-20: real, adversarial seven-NPC experiment; never the canonical story.

Two counterfactual human decisions, independent NPC ticks, a busy/remote seller,
finite forest, a bounded one-hour horizon, and exact SQLite resume.
Usage from simulation/:
  PYTHONPATH=src python scenarios/test_village/play_adversity.py
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict

from living_player_fixture import (
    WORLD, PLAYER, PEOPLE, living_player_gateway,
    setup_living_npc_survival_world,
)


def _do(session, label: str, method, *args):
    state = session.store.load(WORLD)
    return method(*args, command_id=label, expected_revision=state.revision)


def _must_reject(session, label: str, expected: tuple[type[Exception], ...],
                 method, *args) -> str:
    before = session.store.load(WORLD).to_dict()
    try:
        _do(session, label, method, *args)
    except expected as exc:
        assert session.store.load(WORLD).to_dict() == before, (
            'rejection must not mutate the event ledger')
        return type(exc).__name__
    raise AssertionError(label + ' unexpectedly succeeded')


def _conservation(state, decision: str, consumed_wild: int) -> None:
    supplies = state.resources
    player, seller = supplies[PLAYER], supplies['salma']
    expected_bread_eaten = 1 if decision == 'stockpile' else 0
    assert player['bread'] + seller['bread'] + expected_bread_eaten == 3
    assert player['coin_copper'] + seller['coin_copper'] == 10
    assert supplies['woods']['wild_food'] + player['food'] + consumed_wild == 4
    assert supplies['square']['wild_food'] == 2
    assert sum(supplies[npc]['food'] for npc, *_ in PEOPLE) + len(
        state.consumptions) == 2
    assert len(state.npcs) == len(PEOPLE) == 7
    assert all(supplies[npc]['food'] >= 0 for npc, *_ in PEOPLE)


def run_adversity(path: str | Path, decision: str = 'stockpile',
                  *, horizon_seconds: int = 3600) -> dict[str, Any]:
    """Run one reproducible world, with private audit clearly segregated.

    The horizon is an explicit in-world duration, not elapsed real time.
    Test-only setup injects the original finite starting stock exactly once.
    """
    if decision not in ('stockpile', 'share'):
        raise ValueError('decision must be stockpile or share')
    if type(horizon_seconds) is not int or not 291 <= horizon_seconds <= 86400:
        raise ValueError('horizon must be between 291 and 86400 seconds')
    denials: dict[str, str] = {}
    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_npc_survival_world, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(
            session.store, session.clock, npc_survival_demo=True))
        db, g = session.store, session.gateway
        state = db.load(WORLD)
        profile_at_start = g.status().details
        assert state.time == 0
        assert len(state.npcs) == 7
        assert state.resources['salma']['bread'] == 3
        assert state.resources[PLAYER]['coin_copper'] == 10

        # Two alternative choices from identical, empty test-world databases.
        amount = 3 if decision == 'stockpile' else 1
        purchase = _do(session, decision + '-buy', g.buy, 'salma-bread', amount, 2)
        assert purchase.status == 'purchased'
        if decision == 'stockpile':
            assert _do(session, 'stockpile-eat-bread', g.eat, 'bread').status == 'ate'
        else:
            assert _do(session, 'share-return-loaf', g.give, 'salma', 'bread', 1).status == 'gifted'
        _conservation(db.load(WORLD), decision, 0)

        # First NPC decisions and first actual NPC-owned meals happen
        # independently of Carlos. A quoted product is not a guaranteed sale.
        assert _do(session, decision + '-tick', g.wait, 1).time == 1
        active = db.load(WORLD)
        assert {x['npc_id'] for x in active.consumptions.values()} == {
            'basim', 'nora'}
        assert any(a['npc_id'] == 'salma' and a['status'] == 'running'
                   for a in active.actions.values())
        denials['busy_or_exhausted_seller'] = _must_reject(
            session, decision + '-bad-busy-trade', (InvalidEvent,),
            g.buy, 'salma-bread', 1, 2)

        # Player cannot barter while travelling or teleport to a vendor.
        assert _do(session, decision + '-leave-square',
                   g.move, 'square-woods').status == 'traveling'
        denials['trade_during_travel'] = _must_reject(
            session, decision + '-trade-on-road', (ValueError,),
            g.buy, 'salma-bread', 1, 2)
        assert g.inspect().status == 'traveling'
        assert _do(session, decision + '-arrive-woods', g.wait, 50).time == 51
        assert g.inspect().details['location_id'] == 'woods'
        denials['remote_trade'] = _must_reject(
            session, decision + '-trade-from-woods', (InvalidEvent,),
            g.buy, 'salma-bread', 1, 2)
        assert g.offers().details['offers'] == ()

        # All four woodland units can be taken only after 60-second tasks.
        for i in range(4):
            before = db.load(WORLD)
            assert before.resources['woods']['wild_food'] == 4 - i
            assert _do(session, f'{decision}-forage-{i}', g.forage).status == 'foraging'
            underway = db.load(WORLD)
            assert underway.resources['woods']['wild_food'] == 4 - i
            assert underway.resources[PLAYER]['food'] == i
            finished = _do(session, f'{decision}-finish-forage-{i}', g.wait, 60)
            assert finished.details['forage_result'] == 'collected'
            _conservation(db.load(WORLD), decision, 0)
        assert db.load(WORLD).time == 291
        denials['fifth_forage'] = _must_reject(
            session, decision + '-impossible-forage', (ValueError,), g.forage)
        for i in range(4):
            assert _do(session, f'{decision}-eat-wild-{i}', g.eat, 'food').status == 'ate'
            _conservation(db.load(WORLD), decision, i + 1)
        denials['fifth_meal'] = _must_reject(
            session, decision + '-empty-meal', (ValueError,), g.eat, 'food')

        # Split long time: LivingWorldEngine aborts atomically at its event
        # budget; no manual NPC action injection or accelerated fake clock.
        intervals = 0
        while db.load(WORLD).time < horizon_seconds:
            state = db.load(WORLD)
            elapsed = min(180, horizon_seconds - state.time)
            next_step = _do(session, f'{decision}-long-wait-{intervals}',
                            g.wait, elapsed)
            assert next_step.time == state.time + elapsed
            _conservation(db.load(WORLD), decision, 4)
            intervals += 1
        final = db.verify(WORLD).to_dict()
        assert final == db.load(WORLD).to_dict()
        assert final['time'] == horizon_seconds
        assert len(final['consumptions']) == 2
        assert len(final['actions']) >= 7
        assert g.needs().details['hunger'] == 'not_modeled'
        # Player status still reflects explicit player actions only: there
        # are no silent HP/ST/MP edits from autonomous NPC hunger.
        public = session.handoff()
        raw_public = json.dumps(public, ensure_ascii=False)
        for key in ('"npcs"', '"beliefs"', '"goals"', '"needs"',
                    '"relations"', '"injuries"', '"market_trades"',
                    '"consumptions"', '"survival_progress"'):
            assert key not in raw_public
        assert public['canonical_story'] is False
        assert public['time'] == horizon_seconds
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == final

        audit = {
            'npc_count': len(final['npcs']),
            'npc_actions': len(final['actions']),
            'npc_travels': len(final['travels']),
            'npc_social_messages': len(final['social_messages']),
            'npc_meals': len(final['consumptions']),
            'npc_food_left': sum(final['resources'][n]['food'] for n, *_ in PEOPLE),
            'forest_wild_food_left': final['resources']['woods']['wild_food'],
            'square_wild_food_left': final['resources']['square']['wild_food'],
            'bread_and_coin_conserved': True,
            'wild_food_conserved': True,
            'npc_owned_food_conserved': True,
            'forage_depletion_accepted': True,
            'denials_without_state_mutation': denials,
            'explicit_wait_chunks': intervals,
            'player_profile_unchanged_by_npc_tick': (
                profile_at_start == g.status().details),
        }

    # Open the very same file from scratch and prove no time/revision drift.
    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True
    ) as session:
        session.bind_gateway(living_player_gateway(
            session.store, session.clock, npc_survival_demo=True))
        db, g = session.store, session.gateway
        assert db.verify(WORLD).to_dict() == final
        assert session.handoff() == public
        assert g.inspect().time == horizon_seconds
        denials['repeated_meal_command'] = _must_reject(
            session, f'{decision}-eat-wild-0',
            (DuplicateCommand,), g.eat, 'food')
        before = db.load(WORLD).to_dict()
        try:
            g.wait(1, command_id=f'{decision}-stale-tick',
                   expected_revision=before['revision'] - 1)
        except RevisionConflict:
            denials['stale_revision'] = 'RevisionConflict'
        else:
            raise AssertionError('stale time command was accepted')
        assert db.load(WORLD).to_dict() == before
        # An explicit new command is the ONLY way resumed world time moves.
        after = _do(session, f'{decision}-resume-advance', g.wait, 10)
        assert after.time == horizon_seconds + 10
        _conservation(db.load(WORLD), decision, 4)
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()

    return {
        'format': 'carlos-play20-adversity-test-v1',
        'canonical_story': False, 'disposable_test': True,
        'decision': decision,
        'player_visible': {
            'handoff_at_checkpoint': public,
            'requested_horizon_seconds': horizon_seconds,
        },
        'test_audit_only': audit,
        'restart': {
            'sqlite_verified': True, 'handoff_unchanged_on_reopen': True,
            'no_wall_clock_advance': True,
            'no_duplicate_meal': True, 'no_stale_revision': True,
            'time_after_explicit_resume_wait': horizon_seconds + 10,
        },
    }


def main() -> None:
    print('CARLOS — PLAY-20 adverse village experiment (test-only)')
    with TemporaryDirectory(prefix='carlos-play20-') as temp:
        root = Path(temp)
        reports = {
            'stockpile': run_adversity(root / 'stockpile.sqlite', 'stockpile'),
            'share': run_adversity(root / 'share.sqlite', 'share'),
        }
    for name, report in reports.items():
        audit = report['test_audit_only']
        supplies = report['player_visible']['handoff_at_checkpoint']['player_supplies']['balances']
        print(
            f'{name}: t=3600; NPCs={audit["npc_count"]}; '
            f'NPC meals={audit["npc_meals"]}; '
            f'woods food={audit["forest_wild_food_left"]}; '
            f'own supplies={supplies}'
        )
    print('PLAY20_JSON=' + json.dumps(reports, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
