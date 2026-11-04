"""Phase 01-L regression tests: food ownership -> deliberate NPC consumption."""
import pytest
from carlos_sim import (DomainEvent, SQLiteEventStore, TimeEngine, NPCConsumptionService,
                        LivingWorldEngine, NPCMovementService, NPCActionService,
                        NPCService, NPCAssistanceService, choose_food_consumption)
from carlos_sim.store import InvalidEvent, RevisionConflict
from carlos_sim.time_engine import SessionClosed, AdvanceLimitExceeded
from carlos_sim.consumption import _meal_id
from test_assistance import setup, e


@pytest.fixture
def village(tmp_path):
    with SQLiteEventStore(tmp_path/'meal.sqlite') as db:
        setup(db, food_a=3, food_b=10)
        clock=TimeEngine(db); clock.open_session('w')
        old=db.load('w')
        db.append('w','hungry',old.revision,[e('NPCNeedChanged',{
            'npc_id':'nora','need':'hunger','previous':25,'current':85},actor='nora')])
        yield db,clock,NPCConsumptionService(db,clock)


def eat(db,svc,qty=1,who='nora',cmd='eat'):
    return svc.eat('w',who,qty,command_id=cmd,expected_revision=db.load('w').revision)


def test_real_meal_debits_owned_food_and_relives_hunger(village):
    db,clock,svc=village
    before=db.load('w')
    result=eat(db,svc)
    assert result.consumed_quantity==1 and result.new_hunger==60
    assert result.state.resources['nora']['food']==2
    assert result.state.resources['basim']['food']==10
    assert result.state.consumptions[result.id]['hunger_before']==85
    assert result.state.consumptions[result.id]['hunger_after']==60
    assert before.npcs['nora']['needs']['hunger']==85
    assert db.verify('w').to_dict()==result.state.to_dict()


def test_multiple_units_for_one_valid_meal(village):
    db,clock,svc=village
    result=eat(db,svc,qty=3)
    assert result.new_hunger==10
    assert result.state.resources['nora']['food']==0
    assert result.state.consumptions[result.id]['quantity']==3


def test_cannot_eat_twice_in_one_tick_even_with_different_command(village):
    db,clock,svc=village
    first=eat(db,svc)
    with pytest.raises(InvalidEvent,match='twice'):
        eat(db,svc,cmd='again')
    assert db.load('w').to_dict()==first.state.to_dict()


def test_next_tick_allows_another_meal(village):
    db,clock,svc=village
    first=eat(db,svc)
    clock.advance('w',seconds=1,command_id='second-tick',expected_revision=first.state.revision)
    later=eat(db,svc,cmd='second')
    assert later.state.npcs['nora']['needs']['hunger']==35
    assert later.state.resources['nora']['food']==1
    assert len(later.state.consumptions)==2


def test_no_food_and_unknown_food_are_different_but_both_cannot_feed(tmp_path):
    for name, stock in (('zero',0),('unknown',None)):
        with SQLiteEventStore(tmp_path/f'{name}.sqlite') as db:
            setup(db,initialize=stock is not None,food_a=stock or 0)
            clock=TimeEngine(db);clock.open_session('w')
            svc=NPCConsumptionService(db,clock)
            prior=db.load('w')
            with pytest.raises(InvalidEvent,match='sufficient initialized'):
                eat(db,svc)
            assert db.load('w').to_dict()==prior.to_dict()


def test_hunger_zero_cannot_waste_food(village):
    db,clock,svc=village
    db.append('w','no-hunger',db.load('w').revision,[e('NPCNeedChanged',{
       'npc_id':'nora','need':'hunger','previous':85,'current':0},actor='nora')], npc_authorized=True)
    with pytest.raises(InvalidEvent,match='hunger'):
        eat(db,svc)


def test_quantity_must_be_positive_real_integer_and_bounded(village):
    db,clock,svc=village
    for qty in (0,-1,4,100,True,1.5,'2',None):
        with pytest.raises(InvalidEvent):eat(db,svc,qty=qty)
    assert db.load('w').resources['nora']['food']==3


def test_eating_cannot_exceed_remaining_hunger_even_with_food(village):
    db,clock,svc=village
    db.append('w','mild',db.load('w').revision,[e('NPCNeedChanged',{
        'npc_id':'nora','need':'hunger','previous':85,'current':10},actor='nora')], npc_authorized=True)
    with pytest.raises(InvalidEvent,match='hunger'):
        eat(db,svc,qty=2)
    assert eat(db,svc,qty=1).new_hunger==0


def test_eating_while_traveling_rejected(village):
    db,clock,svc=village
    first=NPCMovementService(db,clock).start('w','nora','road','travel',expected_revision=db.load('w').revision)
    with pytest.raises(InvalidEvent,match='traveling'):
        eat(db,svc)
    assert db.load('w').to_dict()==first.state.to_dict()


def test_eating_while_busy_rejected(village):
    db,clock,svc=village
    NPCService(db,clock).decide('w','nora',command_id='choose',expected_revision=db.load('w').revision)
    NPCActionService(db,clock).start('w','nora','busy',expected_revision=db.load('w').revision)
    before=db.load('w')
    with pytest.raises(InvalidEvent,match='busy'):
        eat(db,svc)
    assert db.load('w').to_dict()==before.to_dict()


def test_cannot_eat_without_active_play_session_even_via_low_level_store(village):
    db,clock,svc=village
    clock.close_session('w')
    before=db.load('w')
    with pytest.raises(SessionClosed):eat(db,svc)
    with pytest.raises(InvalidEvent,match='active play session'):
        db.append('w','fake',before.revision,[DomainEvent('NPCFoodConsumed','nora','offline',0,
            {'id':_meal_id('nora',0),'npc_id':'nora','quantity':1})],consumption_authorized=True)
    assert db.load('w').to_dict()==before.to_dict()


def test_low_level_food_event_without_capability_rejected(village):
    db,clock,svc=village
    before=db.load('w')
    with pytest.raises(InvalidEvent,match='capability'):
        db.append('w','forge',before.revision,[DomainEvent('NPCFoodConsumed','nora','fake',0,
             {'id':_meal_id('nora',0),'npc_id':'nora','quantity':1})])
    assert db.load('w').to_dict()==before.to_dict()


def test_mismatched_actor_and_meal_identifiers_rejected(village):
    db,clock,svc=village
    start=db.load('w')
    for id_,actor in (('bad-meal-id','nora'),(_meal_id('nora',0),'basim')):
        with pytest.raises(InvalidEvent):
            db.append('w',f'bad-{actor}-{id_}',start.revision,[DomainEvent('NPCFoodConsumed',actor,
                 'forged',0,{'id':id_,'npc_id':'nora','quantity':1})],consumption_authorized=True)
    assert db.load('w').to_dict()==start.to_dict()


def test_atomic_two_meals_in_same_tick_roll_back_entire_batch(village):
    db,clock,svc=village
    before=db.load('w')
    event=DomainEvent('NPCFoodConsumed','nora','one',0,
                       {'id':_meal_id('nora',0),'npc_id':'nora','quantity':1})
    with pytest.raises(InvalidEvent):
        db.append('w','batch-cheat',before.revision,[event,event],consumption_authorized=True)
    assert db.load('w').to_dict()==before.to_dict()
    assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='batch-cheat'").fetchone()[0]==0


def test_revision_conflict_is_not_silent(village):
    db,clock,svc=village
    old=db.load('w')
    eat(db,svc)
    with pytest.raises(RevisionConflict):
        svc.eat('w','nora',1,command_id='stale',expected_revision=old.revision)


def test_autonomous_meal_is_opt_in(village):
    db,clock,svc=village
    result=LivingWorldEngine(db,clock).advance('w',seconds=1,command_id='disabled',expected_revision=db.load('w').revision)
    assert result.meals_consumed==()
    assert result.state.consumptions=={}


def test_autonomous_meal_relieves_own_hunger(village):
    db,clock,svc=village
    result=LivingWorldEngine(db,clock,consumption_enabled=True).advance('w',seconds=1,
       command_id='eat-autonomously',expected_revision=db.load('w').revision)
    assert result.meals_consumed==(_meal_id('nora',0),)
    assert result.state.npcs['nora']['needs']['hunger']==60
    assert result.state.resources['nora']['food']==2
    assert db.verify('w').to_dict()==result.state.to_dict()


def test_autonomous_policy_only_reads_own_hunger_food(village):
    db,clock,svc=village
    first=choose_food_consumption(db.load('w'),'nora')
    db.append('w','change-basims-hunger',db.load('w').revision,[e('NPCNeedChanged',{
        'npc_id':'basim','need':'hunger','previous':25,'current':99},actor='basim')])
    assert first==choose_food_consumption(db.load('w'),'nora')==1


def test_autonomous_does_not_supersede_manual_action_intention(village):
    db,clock,svc=village
    NPCService(db,clock).decide('w','nora',command_id='plan',expected_revision=db.load('w').revision)
    assert choose_food_consumption(db.load('w'),'nora') is None
    result=LivingWorldEngine(db,clock,consumption_enabled=True).advance('w',seconds=1,
                command_id='honor',expected_revision=db.load('w').revision)
    assert _meal_id('nora',0) not in result.state.consumptions
    assert any(action['npc_id']=='nora' for action in result.state.actions.values())


def test_invalid_autonomous_option_is_rejected(village):
    db,clock,svc=village
    for invalid in (0,1,None,'yes'):
        with pytest.raises(ValueError):
            LivingWorldEngine(db,clock,consumption_enabled=invalid)


def test_eating_cannot_advance_when_paused(village):
    db,clock,svc=village
    clock.close_session('w')
    before=db.load('w')
    with pytest.raises(SessionClosed):
        LivingWorldEngine(db,clock,consumption_enabled=True).advance('w',seconds=100,
            command_id='offline',expected_revision=before.revision)
    assert db.load('w').to_dict()==before.to_dict()


def test_food_transfer_alone_does_not_satisfy_hunger(village):
    db,clock,svc=village
    service=NPCAssistanceService(db,clock)
    asked=service.request('w','nora','basim','food',2,'aid',expected_revision=db.load('w').revision)
    promised=service.respond('w','basim','aid',accept=True,command_id='promise',expected_revision=asked.state.revision)
    done=service.deliver('w','basim','aid',command_id='deliver',expected_revision=promised.state.revision)
    assert done.state.npcs['nora']['needs']['hunger']==85
    assert done.state.resources['nora']['food']==5
    meal=eat(db,svc)
    assert meal.new_hunger==60
    assert meal.state.resources['nora']['food']==4


def test_meal_counter_timestamps_stable_under_replay_and_snapshot(village):
    db,clock,svc=village
    meal=eat(db,svc)
    db.snapshot('w')
    assert db.verify('w').to_dict()==meal.state.to_dict()


def test_equal_worlds_are_deterministic(tmp_path):
    results=[]
    for i in range(2):
        with SQLiteEventStore(tmp_path/f'{i}.sqlite') as db:
            setup(db,food_a=3)
            clock=TimeEngine(db);clock.open_session('w')
            db.append('w','need',db.load('w').revision,[e('NPCNeedChanged',{
                'npc_id':'nora','need':'hunger','previous':25,'current':90},actor='nora')])
            result=LivingWorldEngine(db,clock,consumption_enabled=True).advance('w',seconds=1,
                command_id='auto',expected_revision=db.load('w').revision)
            results.append(result.state.to_dict())
    assert results[0]==results[1]


def test_exceed_event_budget_rolls_back_meal(village):
    db,clock,svc=village
    before=db.load('w').to_dict()
    with pytest.raises(AdvanceLimitExceeded):
        LivingWorldEngine(db,clock,consumption_enabled=True,max_events_per_advance=1).advance('w',
            seconds=10,command_id='too-many',expected_revision=before['revision'])
    assert db.load('w').to_dict()==before


def test_read_only_player_view_does_not_expose_meal_ledger(village):
    db,clock,svc=village
    eat(db,svc)
    assert 'consumptions' not in db.player_view('w')


def test_obligations_remain_recorded_after_requester_eats_and_leaves(village):
    db,clock,svc=village
    help_service=NPCAssistanceService(db,clock)
    asked=help_service.request('w','nora','basim','food',2,'request-not-loan',
              expected_revision=db.load('w').revision)
    help_service.respond('w','basim','request-not-loan',accept=True,command_id='accept',expected_revision=asked.state.revision)
    help_service.deliver('w','basim','request-not-loan',command_id='give',expected_revision=db.load('w').revision)
    eat(db,svc)
    moved=NPCMovementService(db,clock).start('w','nora','road','leave',expected_revision=db.load('w').revision)
    assert moved.state.obligations['request-not-loan']['status']=='fulfilled'
    assert moved.state.npcs['nora']['needs']['hunger']==60
    assert moved.state.consumptions[_meal_id('nora',0)]['quantity']==1
    # This fixture is a gift/aid obligation. Do not invent a repayment debt.
    assert db.verify('w').to_dict()==moved.state.to_dict()


def test_autonomous_consumption_after_gift_fulfills_is_independent_event(tmp_path):
    with SQLiteEventStore(tmp_path/'integration.db') as db:
        setup(db,food_a=0,food_b=10)
        clock=TimeEngine(db);clock.open_session('w')
        db.append('w','hunger',db.load('w').revision,[e('NPCNeedChanged',{
            'npc_id':'nora','need':'hunger','previous':25,'current':95},actor='nora')])
        engine=LivingWorldEngine(db,clock,assistance_enabled=True,consumption_enabled=True)
        first=engine.advance('w',seconds=1,command_id='request',expected_revision=db.load('w').revision)
        assert first.state.obligations['auto-help:nora:0']['status']=='promised'
        assert first.state.resources['nora']['food']==0
        assert first.state.npcs['nora']['needs']['hunger']==95
        second=engine.advance('w',seconds=400,command_id='advance',expected_revision=first.state.revision)
        assert second.state.obligations['auto-help:nora:0']['status']=='fulfilled'
        assert len([m for m in second.state.consumptions.values() if m['npc_id']=='nora'])>=1
        assert second.state.npcs['nora']['needs']['hunger']<95
        assert second.state.resources['nora']['food'] < 3
        assert second.state.obligations['auto-help:nora:0']['transfer']['requester_after']==3
        assert db.verify('w').to_dict()==second.state.to_dict()


def test_meal_on_long_valid_npc_id_uses_short_deterministic_key(tmp_path):
    with SQLiteEventStore(tmp_path/'long-id.sqlite') as db:
        setup(db)
        ident='some-long-npc-'+'x'*110
        setup_events=[e('EntityCreated',{'id':ident,'name':'Test','controller':'npc','location_id':'market'}),
              e('NPCConfigured',{'npc_id':ident,'role':'eater',
                 'needs':{'hunger':90,'fatigue':0,'safety':0},
                 'goals':{'earn':0,'explore':0,'survive':0}}),
              e('ResourceChanged',{'owner_id':ident,'resource':'food',
                 'previous':None,'current':1,'source':'initialization'})]
        db.append('w','long-actor',db.load('w').revision,setup_events,bootstrap=True)
        clock=TimeEngine(db);clock.open_session('w')
        result=NPCConsumptionService(db,clock).eat('w',ident,1,command_id='meal-long',expected_revision=db.load('w').revision)
        assert len(result.id)<=128
        assert result.state.consumptions[result.id]['npc_id']==ident
        assert result.state.npcs[ident]['needs']['hunger']==65


def test_split_steps_match_single_advance_with_eating(tmp_path):
    output=[]
    for i,chunks in enumerate(((400,),(100,100,100,100))):
        with SQLiteEventStore(tmp_path/f'{i}.sqlite') as db:
            setup(db,food_a=2,food_b=10)
            clock=TimeEngine(db);clock.open_session('w')
            db.append('w','set',db.load('w').revision,[e('NPCNeedChanged',{
                'npc_id':'nora','need':'hunger','previous':25,'current':90},actor='nora')])
            engine=LivingWorldEngine(db,clock,consumption_enabled=True)
            for j,seconds in enumerate(chunks):
                engine.advance('w',seconds=seconds,command_id=f'tick-{j}',expected_revision=db.load('w').revision)
            state=db.verify('w').to_dict()
            state.pop('revision')
            output.append(state)
    assert output[0]==output[1]


def test_full_replay_after_database_reopen(tmp_path):
    filename=tmp_path/'reopen.db'
    with SQLiteEventStore(filename) as db:
        setup(db,food_a=2)
        c=TimeEngine(db);c.open_session('w')
        before=db.load('w')
        db.append('w','need',before.revision,[e('NPCNeedChanged',{
            'npc_id':'nora','need':'hunger','previous':25,'current':70},actor='nora')])
        eaten=NPCConsumptionService(db,c).eat('w','nora',1,command_id='first-meal',expected_revision=db.load('w').revision)
        db.snapshot('w')
    with SQLiteEventStore(filename) as db:
        assert db.verify('w').to_dict()==eaten.state.to_dict()
        assert db.load('w').consumptions[eaten.id]['food_after']==1


def test_regular_consumption_or_spoilage_does_not_grant_hunger_relief(village):
    db,clock,svc=village
    original=db.load('w')
    wasted=db.append('w','lost',original.revision,[e('ResourceChanged',{
       'owner_id':'nora','resource':'food','previous':3,'current':2,'source':'consumption'},actor='nora')])
    assert wasted.resources['nora']['food']==2
    assert wasted.npcs['nora']['needs']['hunger']==85
    assert wasted.consumptions=={}
