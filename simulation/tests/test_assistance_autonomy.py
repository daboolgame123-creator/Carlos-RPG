"""Phase 01-K: autonomous, resource-conserving aid under explicit game time."""
import pytest

from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, LivingWorldEngine,
                        NPCAssistanceService, NPCMovementService, NPCService,
                        NPCActionService, NPCSocialService,
                        choose_assistance_intent, AdvanceLimitExceeded)
from test_assistance import setup, e


def world_with_needy_person(db, *, provider_food=10, requester_food=1,
                            provider_hunger=25, requester_hunger=85):
    setup(db, food_a=requester_food, food_b=provider_food)
    clock = TimeEngine(db)
    clock.open_session('w')
    changes = []
    for name, hunger in (('nora', requester_hunger), ('basim', provider_hunger)):
        if hunger != 25:
            changes.append(e('NPCNeedChanged', {'npc_id': name, 'need': 'hunger',
                  'previous': 25, 'current': hunger}, actor=name))
    if changes:
        db.append('w', 'set-private-needs', db.load('w').revision, changes)
    return clock


def living(db, clock, seconds, command, **opts):
    return LivingWorldEngine(db, clock, assistance_enabled=True, **opts).advance(
        'w', seconds=seconds, command_id=command, expected_revision=db.load('w').revision)


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path/'village.sqlite') as db:
        clock = world_with_needy_person(db)
        yield db, clock


def test_idle_hungry_npc_requests_and_provider_autonomously_promises(village):
    db, clock = village
    result = living(db, clock, 1, 'request-and-response')
    oid = 'auto-help:nora:0'
    assert result.assistance_transitions == ((oid, 'requested'), (oid, 'promised'))
    assert result.state.obligations[oid]['quantity'] == 3
    assert result.state.resources['nora']['food'] == 1
    assert result.state.resources['basim']['food'] == 10
    assert result.state.relations == {}
    assert db.verify('w').to_dict() == result.state.to_dict()


def test_delivery_occurs_later_with_real_conservation(village):
    db, clock = village
    start = living(db, clock, 1, 'first')
    assert start.state.obligations['auto-help:nora:0']['status'] == 'promised'
    done = living(db, clock, 400, 'time-for-help')
    aid = done.state.obligations['auto-help:nora:0']
    assert aid['status'] == 'fulfilled'
    assert done.assistance_transitions.count(('auto-help:nora:0', 'fulfilled')) == 1
    assert aid['resolved_at'] > aid['responded_at']
    assert aid['transfer'] == {'provider_before': 10, 'provider_after': 7,
                               'requester_before': 1, 'requester_after': 4}
    assert done.state.resources['basim']['food'] + done.state.resources['nora']['food'] == 11
    assert done.state.relations['nora']['basim'] == 5
    assert db.verify('w').to_dict() == done.state.to_dict()


def test_older_manual_world_behavior_unchanged_if_disabled(village):
    db, clock = village
    result = LivingWorldEngine(db, clock).advance('w', seconds=1, command_id='off',
                           expected_revision=db.load('w').revision)
    assert result.assistance_transitions == ()
    assert result.state.obligations == {}
    assert result.started_action_ids


def test_no_request_if_sufficient_food(tmp_path):
    with SQLiteEventStore(tmp_path/'enough.db') as db:
        clock = world_with_needy_person(db, requester_food=5)
        result = living(db, clock, 1, 'enough')
        assert not result.state.obligations


def test_no_request_if_hunger_is_low(tmp_path):
    with SQLiteEventStore(tmp_path/'fine.db') as db:
        clock = world_with_needy_person(db, requester_hunger=20)
        result = living(db, clock, 1, 'not-hungry')
        assert not result.state.obligations


def test_refusal_if_provider_cannot_spare_stock(tmp_path):
    with SQLiteEventStore(tmp_path/'poor.db') as db:
        clock = world_with_needy_person(db, provider_food=4)
        done = living(db, clock, 1, 'cannot-spare')
        oid = 'auto-help:nora:0'
        assert done.state.obligations[oid]['status'] == 'declined'
        assert done.state.resources['basim']['food'] == 4
        assert done.state.resources['nora']['food'] == 1
        assert done.state.relations == {}


def test_refusal_if_provider_has_high_own_hunger(tmp_path):
    with SQLiteEventStore(tmp_path/'provider-needs.db') as db:
        clock = world_with_needy_person(db, provider_hunger=85)
        done = living(db, clock, 1, 'provider-needs')
        assert done.state.obligations['auto-help:nora:0']['status'] == 'declined'
        assert done.state.resources['basim']['food'] == 10


def test_provider_refuses_based_on_own_directed_distrust(village):
    db, clock = village
    NPCSocialService(db, clock).interact('w', 'nora', 'basim', kind='threat',
       text='go away', message_id='threat', expected_revision=db.load('w').revision)
    assert db.load('w').relations['basim']['nora'] == -12
    done = living(db, clock, 1, 'no-trust')
    assert done.state.obligations['auto-help:nora:0']['status'] == 'declined'


def test_requester_choice_does_not_depend_on_private_provider_stock(tmp_path):
    choices = []
    for i, provider_stock in enumerate((0, 15)):
        with SQLiteEventStore(tmp_path/f'{i}.db') as db:
            world_with_needy_person(db, provider_food=provider_stock)
            choice = choose_assistance_intent(db.load('w'), 'nora', 'request')
            assert choice is not None
            choices.append((choice.actor_id, choice.fields['provider'],
                            choice.fields['quantity'], choice.reason))
    assert choices[0] == choices[1]


def test_autonomous_request_not_derived_from_other_npcs_private_hunger(tmp_path):
    choices = []
    for i, provider_need in enumerate((0, 95)):
        with SQLiteEventStore(tmp_path/f'{i}.db') as db:
            world_with_needy_person(db, provider_hunger=provider_need)
            choices.append(choose_assistance_intent(db.load('w'), 'nora', 'request'))
    assert choices[0] == choices[1]


