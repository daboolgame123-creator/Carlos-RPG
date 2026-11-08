"""PLAY-29: internal audit must read real resources without changing them."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scenarios" / "test_village"))

from carlos_sim import DomainEvent, SQLiteEventStore, canonical_hash
from carlos_sim.food_security_audit import audit_food_security
from carlos_sim.domain import WorldState
from play_physical_supply import WORLD, seed_physical_supply


def test_empty_world_is_a_valid_empty_report():
    r = audit_food_security(WorldState("empty"))
    assert r.npc_count == 0
    assert r.high_risk == ()
    assert r.personal_food_units == 0
    assert r.to_dict()["high_risk"] == []


@pytest.mark.parametrize("initial_food,expected_total", [(0, 0), (18, 126)])
def test_seven_actual_npcs_keep_food_ownership_distinct(tmp_path, initial_food, expected_total):
    with SQLiteEventStore(tmp_path / "village.sqlite") as db:
        seed_physical_supply(db, personal_food=initial_food)
        state = db.load(WORLD)
        before = canonical_hash(state.to_dict())
        report = audit_food_security(state)
        assert report.world_id == WORLD
        assert report.npc_count == 7
        assert report.personal_food_units == expected_total
        assert report.consumed_meals == 0
        assert report.reserved_courier_food_units == 0
        assert report.food_stock_unknown_npcs == ()
        assert all(0 <= x.hunger <= 100 for x in report.high_risk)
        assert canonical_hash(state.to_dict()) == before
        assert db.verify(WORLD).to_dict() == state.to_dict()
        assert db.player_view(WORLD) == {
            "world_id": WORLD, "time": 0, "revision": state.revision,
        }


def test_risk_is_real_need_plus_actual_owned_stock(tmp_path):
    with SQLiteEventStore(tmp_path / "village.sqlite") as db:
        seed_physical_supply(db, personal_food=0)
        report = audit_food_security(db.load(WORLD))
        assert "adel" in report.high_risk_without_food
        assert "adel" not in report.high_risk_unknown_food
        assert report.high_risk[0].hunger >= 75
        assert report.personal_food_units == 0
        assert report.hunger_at_cap == ()


def test_risk_can_exist_even_if_character_owns_provisions(tmp_path):
    with SQLiteEventStore(tmp_path / "village.sqlite") as db:
        seed_physical_supply(db, personal_food=18)
        report = audit_food_security(db.load(WORLD))
        assert report.high_risk
        assert all(x.personally_owned_food == 18 for x in report.high_risk)
        assert report.high_risk_without_food == ()


def test_missing_npc_food_is_unknown_and_not_zero(tmp_path):
    with SQLiteEventStore(tmp_path / "unknown.sqlite") as db:
        db.create_world("u")
        events = [
            DomainEvent("LocationCreated", None, "test", 0, {"id": "home", "name": "Home"}),
            DomainEvent("EntityCreated", None, "test", 0, {
                "id": "hungry", "name": "Hungry", "location_id": "home",
                "controller": "npc",
            }),
            DomainEvent("NPCConfigured", None, "test", 0, {
                "npc_id": "hungry", "role": "resident",
                "needs": {"hunger": 90, "fatigue": 0, "safety": 0},
                "goals": {"survive": 30, "earn": 0, "explore": 0},
            }),
        ]
        db.append("u", "init", 0, events, bootstrap=True)
        report = audit_food_security(db.load("u"))
        assert report.personal_food_units == 0
        assert report.food_stock_unknown_npcs == ("hungry",)
        assert report.high_risk_unknown_food == ("hungry",)
        assert report.high_risk_without_food == ()
        assert report.food_stock_unknown_sites == ("home",)


@pytest.mark.parametrize("bad", [False, True, 0, -1, 101, "75", 75.0, None])
def test_invalid_risk_threshold_never_changes_world(bad):
    state = WorldState("empty")
    before = canonical_hash(state.to_dict())
    with pytest.raises(ValueError):
        audit_food_security(state, risk_threshold=bad)
    assert canonical_hash(state.to_dict()) == before


def test_reports_are_detached_and_pure_for_read_only_checks(tmp_path):
    with SQLiteEventStore(tmp_path / "village.sqlite") as db:
        seed_physical_supply(db, personal_food=18)
        state = db.load(WORLD)
        old = state.to_dict()
        r = audit_food_security(state).to_dict()
        assert isinstance(r["high_risk"], list)
        r["high_risk"].append({"npc_id": "fake", "hunger": 100})
        assert state.to_dict() == old
        assert db.verify(WORLD).to_dict() == old


def test_world_required():
    with pytest.raises(TypeError):
        audit_food_security({"resources": {"food": 100}})
