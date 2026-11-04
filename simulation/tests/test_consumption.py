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
       'npc_id':'nora','need':'hunger','previous':85,'current':0},actor='nora')])
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
        'npc_id':'nora','need':'hunger','previous':85,'current':10},actor='nora')])
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


