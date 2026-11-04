"""Post-review cases: food must not create free satiety through legacy need events."""
import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine, NPCConsumptionService
from carlos_sim.store import InvalidEvent
from test_assistance import setup


def fixture_world(db):
    setup(db, food_a=2, food_b=3)
    clock = TimeEngine(db)
    clock.open_session('w')
    return clock


def hunger_event(current, *, previous=25, actor='nora'):
    return DomainEvent('NPCNeedChanged', actor, 'fixture need adjustment', 0,
        {'npc_id': 'nora', 'need': 'hunger', 'previous': previous, 'current': current})


def test_legacy_need_change_cannot_grant_foodless_satiety(tmp_path):
    with SQLiteEventStore(tmp_path/'free-satiety.sqlite') as db:
        fixture_world(db)
        before = db.load('w')
        with pytest.raises(InvalidEvent, match='trusted NPC adjustment'):
            db.append('w', 'magic-meal', before.revision, [hunger_event(0)])
        assert db.load('w').to_dict() == before.to_dict()
        assert db.db.execute("SELECT count(*) FROM commands WHERE command_id='magic-meal'").fetchone()[0] == 0


def test_explicit_trusted_need_adjustment_still_available_without_food_effect(tmp_path):
    with SQLiteEventStore(tmp_path/'trusted.sqlite') as db:
        fixture_world(db)
        modified = db.append('w', 'admin-relief', db.load('w').revision, [hunger_event(5)],
                             npc_authorized=True)
        assert modified.npcs['nora']['needs']['hunger'] == 5
        assert modified.resources['nora']['food'] == 2
        assert modified.consumptions == {}
        assert db.verify('w').to_dict() == modified.to_dict()


def test_hunger_increase_remains_possible_without_extra_capability(tmp_path):
    with SQLiteEventStore(tmp_path/'growing.sqlite') as db:
        fixture_world(db)
        result = db.append('w', 'more-hunger', db.load('w').revision, [hunger_event(75)])
        assert result.npcs['nora']['needs']['hunger'] == 75


def test_untrusted_relief_rolls_back_other_valid_changes_in_batch(tmp_path):
    with SQLiteEventStore(tmp_path/'rollback.sqlite') as db:
        fixture_world(db)
        before = db.load('w')
        waste_food = DomainEvent('ResourceChanged', 'nora', 'food spoiled', 0,
            {'owner_id': 'nora', 'resource': 'food', 'previous': 2,
             'current': 1, 'source': 'consumption'})
        with pytest.raises(InvalidEvent, match='trusted NPC adjustment'):
            db.append('w', 'mixed-batch', before.revision, [waste_food, hunger_event(0)])
        assert db.load('w').to_dict() == before.to_dict()


def test_offline_trusted_hunger_adjustment_remains_rejected(tmp_path):
    with SQLiteEventStore(tmp_path/'offline.sqlite') as db:
        clock = fixture_world(db)
        clock.close_session('w')
        before = db.load('w')
        with pytest.raises(InvalidEvent, match='active play session'):
            db.append('w', 'offline-relief', before.revision, [hunger_event(0)], npc_authorized=True)
        assert db.load('w').to_dict() == before.to_dict()


def test_finite_food_meal_is_valid_without_legacy_need_override(tmp_path):
    with SQLiteEventStore(tmp_path/'normal-meal.sqlite') as db:
        clock = fixture_world(db)
        result = NPCConsumptionService(db,clock).eat('w','nora',1,
                    command_id='real-meal',expected_revision=db.load('w').revision)
        assert result.state.resources['nora']['food'] == 1
        assert result.new_hunger == 0
        assert len(result.state.consumptions) == 1
