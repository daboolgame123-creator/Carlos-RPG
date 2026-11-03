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


def test_no_remote_or_traveling_requester(village):
    db, clock = village
    moved = NPCMovementService(db, clock).start('w','nora','road','nora-away',
                                               expected_revision=db.load('w').revision)
    assert choose_assistance_intent(moved.state, 'nora', 'request') is None
    result = living(db, clock, 1, 'during-trip')
    assert result.state.obligations == {}


def test_no_request_while_actively_working(village):
    db, clock = village
    NPCService(db, clock).decide('w', 'nora', command_id='nora-plan',
                                 expected_revision=db.load('w').revision)
    NPCActionService(db, clock).start('w', 'nora', 'work',
                                     expected_revision=db.load('w').revision)
    assert choose_assistance_intent(db.load('w'), 'nora', 'request') is None
    result = living(db, clock, 1, 'nora-working')
    assert result.state.obligations == {}


def test_prior_private_intention_prevents_autonomous_aid(village):
    db, clock = village
    NPCService(db, clock).decide('w', 'nora', command_id='nora-decided',
                                 expected_revision=db.load('w').revision)
    assert choose_assistance_intent(db.load('w'), 'nora', 'request') is None
    outcome = living(db, clock, 1, 'intent-honored')
    assert not outcome.state.obligations
    assert any(a['npc_id'] == 'nora' for a in outcome.state.actions.values())


def test_provider_not_using_requesters_secret_needs_for_response(village):
    db, clock = village
    svc = NPCAssistanceService(db, clock)
    svc.request('w', 'nora', 'basim', 'food', 2, 'manual-request',
                expected_revision=db.load('w').revision)
    first = choose_assistance_intent(db.load('w'), 'basim', 'respond')
    # Change only Nora's own private need after making the request.
    db.append('w', 'secret-change', db.load('w').revision, [e('NPCNeedChanged', {
              'npc_id': 'nora', 'need': 'hunger', 'previous': 85, 'current': 99}, actor='nora')])
    assert choose_assistance_intent(db.load('w'), 'basim', 'respond') == first


def test_manual_request_is_auto_handled_by_provider(tmp_path):
    with SQLiteEventStore(tmp_path/'manual.db') as db:
        setup(db)
        clock=TimeEngine(db);clock.open_session('w')
        svc=NPCAssistanceService(db,clock)
        svc.request('w','nora','basim','water',3,'manual',expected_revision=db.load('w').revision)
        output=living(db,clock,1,'respond')
        assert output.state.obligations['manual']['status']=='promised'
        assert output.assistance_transitions == (('manual','promised'),)
        assert output.state.resources['basim']['water']==8


def test_auto_cancels_promise_if_stock_spent_before_delivery(village):
    db,clock=village
    svc=NPCAssistanceService(db,clock)
    svc.request('w','nora','basim','food',9,'big',expected_revision=db.load('w').revision)
    svc.respond('w','basim','big',accept=True,command_id='yes',
                expected_revision=db.load('w').revision)
    db.append('w','eat',db.load('w').revision,[e('ResourceChanged', {
            'owner_id':'basim','resource':'food','previous':10,'current':1,'source':'consumption'},actor='basim')])
    clock.advance('w',seconds=1,command_id='time',expected_revision=db.load('w').revision)
    result=living(db,clock,1,'cancel')
    assert result.assistance_transitions[0] == ('big','cancelled')
    assert result.state.obligations['big']['status']=='cancelled'
    assert result.state.resources['basim']['food']==1
    assert result.state.relations=={}


def test_no_remote_delivery_or_remote_cancellation(village):
    db,clock=village
    svc=NPCAssistanceService(db,clock)
    svc.request('w','nora','basim','food',2,'promise',expected_revision=db.load('w').revision)
    svc.respond('w','basim','promise',accept=True,command_id='yes',
                expected_revision=db.load('w').revision)
    travel=NPCMovementService(db,clock).start('w','basim','road','depart',
                                            expected_revision=db.load('w').revision)
    clock.advance('w',seconds=20,command_id='arrive',expected_revision=travel.state.revision)
    result=living(db,clock,1,'while-separated')
    assert result.state.obligations['promise']['status']=='promised'
    assert all(i != 'promise' for i, status in result.assistance_transitions)
    assert result.state.resources['basim']['food']==10


def test_one_long_advance_matches_four_short_advances(tmp_path):
    results=[]
    for i, chunks in enumerate(((400,), (100, 100, 100, 100))):
        with SQLiteEventStore(tmp_path / f'chunk{i}.db') as db:
            clock = world_with_needy_person(db)
            for j, seconds in enumerate(chunks):
                living(db, clock, seconds, f'chunk{j}')
            state = db.verify('w').to_dict()
            state.pop('revision')  # number of TimeAdvanced boundaries differs
            results.append(state)
    assert results[0] == results[1]


def test_request_refractory_period_survives_refusal(village):
    db,clock=village
    svc=NPCAssistanceService(db,clock)
    svc.request('w','nora','basim','food',2,'first',expected_revision=db.load('w').revision)
    svc.respond('w','basim','first',accept=False,command_id='decline',
                expected_revision=db.load('w').revision)
    assert choose_assistance_intent(db.load('w'),'nora','request') is None
    clock.advance('w',seconds=899,command_id='wait',expected_revision=db.load('w').revision)
    assert choose_assistance_intent(db.load('w'),'nora','request') is None
    clock.advance('w',seconds=1,command_id='reconsider',expected_revision=db.load('w').revision)
    intent=choose_assistance_intent(db.load('w'),'nora','request')
    assert intent is not None and intent.request_id=='auto-help:nora:900'


def test_atomic_event_budget_failure(village):
    db,clock=village
    before=db.load('w').to_dict()
    with pytest.raises(AdvanceLimitExceeded):
        living(db,clock,300,'budget-too-small',max_events_per_advance=1)
    assert db.load('w').to_dict()==before
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='budget-too-small'").fetchone()[0]==0


def test_paused_game_cannot_autonomously_deliver(village):
    db,clock=village
    engine=LivingWorldEngine(db,clock,assistance_enabled=True)
    result=engine.advance('w',seconds=1,command_id='first',expected_revision=db.load('w').revision)
    clock.close_session('w')
    before=db.load('w').to_dict()
    with pytest.raises(PermissionError):
        engine.advance('w',seconds=400,command_id='offline',expected_revision=result.state.revision)
    assert db.load('w').to_dict()==before


def test_same_world_replays_from_snapshot_after_autonomous_delivery(village):
    db,clock=village
    living(db,clock,400,'full')
    db.snapshot('w')
    assert db.verify('w').to_dict()==db.load('w').to_dict()
    assert db.load('w').obligations['auto-help:nora:0']['status']=='fulfilled'


def test_deterministic_across_two_isolated_worlds(tmp_path):
    outcomes=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path/f'{i}.db') as db:
            clock=world_with_needy_person(db)
            res=living(db,clock,400,'full')
            outcomes.append((res.state.to_dict(),res.assistance_transitions))
    assert outcomes[0]==outcomes[1]


def test_invalid_opt_in_settings_rejected(village):
    db,clock=village
    for invalid in ('yes',None,1,0):
        with pytest.raises(ValueError):
            LivingWorldEngine(db,clock,assistance_enabled=invalid)
    for invalid in ('unknown',None,123):
        with pytest.raises(ValueError):
            choose_assistance_intent(db.load('w'),'nora',invalid)


def test_social_navigation_and_assistance_work_together(village):
    db,clock=village
    result=LivingWorldEngine(db,clock,assistance_enabled=True,
                             social_enabled=True,navigation_enabled=True).advance(
           'w',seconds=2,command_id='all-three',expected_revision=db.load('w').revision)
    assert result.state.obligations['auto-help:nora:0']['status']=='promised'
    assert db.verify('w').to_dict()==result.state.to_dict()


def test_unknown_resource_registry_not_interpreted_as_zero(tmp_path):
    with SQLiteEventStore(tmp_path/'unknown.db') as db:
        setup(db,initialize=False)
        clock=TimeEngine(db);clock.open_session('w')
        db.append('w','needs',db.load('w').revision,[e('NPCNeedChanged',{
            'npc_id':'nora','need':'hunger','previous':25,'current':90},actor='nora')])
        assert choose_assistance_intent(db.load('w'),'nora','request') is None


def test_two_needy_people_do_not_force_provider_to_accept_twice_at_same_tick(tmp_path):
    with SQLiteEventStore(tmp_path/'three.db') as db:
        clock=world_with_needy_person(db)
        # Sara begins in the forest; she returns to the public market and then
        # experiences hunger. There is no magical remote assistance request.
        mover=NPCMovementService(db,clock)
        started=mover.start('w','sara','road','sara-returns',expected_revision=db.load('w').revision)
        clock.advance('w',seconds=20,command_id='sara-arrives',expected_revision=started.state.revision)
        db.append('w','sara-hungry',db.load('w').revision,[e('NPCNeedChanged',{
            'npc_id':'sara','need':'hunger','previous':25,'current':88},actor='sara',at=20)])
        result=living(db,clock,1,'assist')
        obligations=result.state.obligations
        assert len(obligations)==2
        assert sorted(x['status'] for x in obligations.values())==['promised','requested']
        assert sum(x['status']=='promised' for x in obligations.values())==1
        assert all(x['status']!='fulfilled' for x in obligations.values())
        assert result.state.resources['basim']['food']==10
        assert db.verify('w').to_dict()==result.state.to_dict()


def test_provider_respects_existing_promises_when_evaluating_new_request(tmp_path):
    with SQLiteEventStore(tmp_path/'overpromise.db') as db:
        clock=world_with_needy_person(db)
        svc=NPCAssistanceService(db,clock)
        # Both parties are on-site at time zero: eight units promised and not
        # yet taken from the provider's physical stock.
        svc.request('w','nora','basim','food',8,'first',expected_revision=db.load('w').revision)
        svc.respond('w','basim','first',accept=True,command_id='promise-eight',
                    expected_revision=db.load('w').revision)
        clock.advance('w',seconds=1,command_id='tick',expected_revision=db.load('w').revision)
        # The same requester can ask for water separately, but a second food
        # claimant must not be promised already-committed supplies. Move Sara
        # from forest to the same local market to make her request legitimate.
        trip=NPCMovementService(db,clock).start('w','sara','road','arrive',
                                               expected_revision=db.load('w').revision)
        arrived=clock.advance('w',seconds=20,command_id='sara-home',expected_revision=trip.state.revision)
        svc.request('w','sara','basim','food',2,'second',expected_revision=arrived.state.revision)
        intent=choose_assistance_intent(db.load('w'),'basim','respond')
        assert intent is not None and intent.request_id=='second'
        assert intent.fields=={'accept':False}
        assert db.load('w').resources['basim']['food']==10
