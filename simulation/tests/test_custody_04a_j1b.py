"""J1b custody lineage: certify what is physically determined, otherwise unknown."""
from __future__ import annotations

import pytest
from carlos_sim import (
    DomainEvent, SQLiteEventStore, TimeEngine, NPCPropertyService, NPCMarketService,
    NPCAssistanceService, NPCConsumptionService, NPCProductionService,
)
from carlos_sim.domain import WorldState
from carlos_sim.custody import custody_audit
from carlos_sim.store import InvalidEvent
from test_rights_04a_j1a import scene, origin, register
from test_assistance import setup as assistance_setup


def _rev(db, name="v"):
    return db.load(name).revision


def _take(db, clock, actor="basim", qty=1, name="t1", holder="bakery"):
    return NPCPropertyService(db, clock).take(
        "v", actor, name, holder, "bakery", "bread", qty,
        expected_revision=_rev(db)).state


def test_full_source_known_taking_certifies_actual_custodians(scene):
    db, clock = scene
    register(db, [origin()])
    actual = _take(db, clock)
    row = actual.property_custody_lots["origin-bread"]
    assert dict(row["known_holders"]) == {"bakery": 1, "basim": 1}
    assert row["unresolved_quantity"] == 0
    assert row["exited_quantity"] == 0
    moves = list(actual.property_custody_moves.values())
    assert len(moves) == 1 and moves[0]["source_holder"] == "bakery"
    assert moves[0]["target_holder"] == "basim"
    assert moves[0]["event_kind"] == "PropertyTaken"
    assert actual.property_title_origins["origin-bread"]["record_kind"] == "historical_origin_only"
    assert db.verify("v").to_dict() == actual.to_dict()


def test_reselling_traceable_taken_loaf_tracks_custody_not_title(scene):
    db, clock = scene
    register(db, [origin()])
    _take(db, clock)
    market = NPCMarketService(db, clock)
    market.post("v", "basim", "basim", "bakery", "quote-b", "bread", 1,
                "coin_copper", 2, expected_revision=_rev(db))
    sold = market.buy("v", "salma", "sale-b", "quote-b", 1, 2,
                      expected_revision=_rev(db)).state
    assert dict(sold.property_custody_lots["origin-bread"]["known_holders"]) == {
        "bakery": 1, "salma": 1,
    }
    assert sold.property_title_origins["origin-bread"]["recorded_beneficiary_id"] == "bakery"
    events = tuple(sold.property_custody_moves.values())
    assert len(events) == 2 and events[-1]["event_kind"] == "MarketTradeExecuted"
    assert events[-1]["target_holder"] == "salma"
    assert db.verify("v").to_dict() == sold.to_dict()


def test_partial_from_partly_unregistered_bread_loses_certainty(scene):
    db, clock = scene
    register(db, [origin(quantity=1)])
    after = _take(db, clock)
    lot = after.property_custody_lots["origin-bread"]
    assert lot["known_holders"] == {}
    assert lot["unresolved_quantity"] == 1
    assert lot["exited_quantity"] == 0
    assert after.resources["bakery"]["bread"] == 1
    assert after.resources["basim"]["bread"] == 1
    row = next(iter(after.property_custody_moves.values()))
    assert row["kind"] == "unresolved" and row["target_holder"] is None
    assert db.verify("v").to_dict() == after.to_dict()


def test_partial_mixed_two_origins_never_picks_arbitrary_loaf(scene):
    db, clock = scene
    register(db, [origin("o1", quantity=1), origin("o2", quantity=1)])
    after = _take(db, clock)
    for ident in ("o1", "o2"):
        assert after.property_custody_lots[ident]["known_holders"] == {}
        assert after.property_custody_lots[ident]["unresolved_quantity"] == 1
    assert len(after.property_custody_moves) == 2
    assert db.verify("v").to_dict() == after.to_dict()


def test_full_mixed_stock_transfer_preserves_all_known_origins(scene):
    db, clock = scene
    register(db, [origin("o1", quantity=1), origin("o2", quantity=1)])
    taken = _take(db, clock, qty=2)
    assert taken.property_custody_lots["o1"]["known_holders"] == {"basim": 1}
    assert taken.property_custody_lots["o2"]["known_holders"] == {"basim": 1}
    market = NPCMarketService(db, clock)
    market.post("v", "basim", "basim", "bakery", "all-stock", "bread", 2,
                "coin_copper", 1, expected_revision=_rev(db))
    after = market.buy("v", "salma", "whole-sale", "all-stock", 2, 1,
                       expected_revision=_rev(db)).state
    for ident in ("o1", "o2"):
        assert after.property_custody_lots[ident]["known_holders"] == {"salma": 1}
    assert len(after.property_custody_moves) == 4
    assert db.verify("v").to_dict() == after.to_dict()


def test_untraced_legacy_world_produces_no_fake_custody(scene):
    db, clock = scene
    assert db.load("v").property_custody_lots == {}
    taken = _take(db, clock)
    assert taken.property_custody_lots == {} and taken.property_custody_moves == {}
    assert db.verify("v").to_dict() == taken.to_dict()


def test_help_delivery_moves_certified_food_without_granting_title(tmp_path):
    with SQLiteEventStore(tmp_path / "help-lot.sqlite") as db:
        assistance_setup(db, food_a=1, food_b=10)
        clock = TimeEngine(db); clock.open_session("w")
        ev = origin("food-basim", "basim", "basim", 10, "food", "market")
        db.append("w", "register", _rev(db, "w"), [ev], bootstrap=True)
        svc = NPCAssistanceService(db, clock)
        svc.request("w", "nora", "basim", "food", 3, "help1",
                    expected_revision=_rev(db, "w"))
        svc.respond("w", "basim", "help1", accept=True, command_id="yes",
                    expected_revision=_rev(db, "w"))
        result = svc.deliver("w", "basim", "help1", command_id="delivered",
                             expected_revision=_rev(db, "w"))
        state = result.state
        assert state.resources["nora"]["food"] == 4
        assert state.resources["basim"]["food"] == 7
        assert dict(state.property_custody_lots["food-basim"]["known_holders"]) == {
            "nora": 3, "basim": 7,
        }
        assert state.property_custody_lots["food-basim"]["unresolved_quantity"] == 0
        assert db.verify("w").to_dict() == state.to_dict()


def test_food_consumption_exits_origin_units_but_does_not_transfer_title(tmp_path):
    with SQLiteEventStore(tmp_path / "meal-lot.sqlite") as db:
        assistance_setup(db, food_a=3, food_b=10)
        clock = TimeEngine(db); clock.open_session("w")
        db.append("w", "orig-food", _rev(db, "w"), [
            origin("food-nora", "nora", "nora", 3, "food", "market")
        ], bootstrap=True)
        db.append("w", "hungry", _rev(db, "w"), [DomainEvent(
            "NPCNeedChanged", "nora", "test hunger", 0,
            {"npc_id": "nora", "need": "hunger",
             "previous": 25, "current": 85}
        )])
        svc = NPCConsumptionService(db, clock)
        ate = svc.eat("w", "nora", 1, command_id="eat-1",
                      expected_revision=_rev(db, "w")).state
        lot = ate.property_custody_lots["food-nora"]
        assert dict(lot["known_holders"]) == {"nora": 2}
        assert lot["exited_quantity"] == 1 and lot["unresolved_quantity"] == 0
        assert db.verify("w").to_dict() == ate.to_dict()


def test_production_input_exits_registered_lot_and_output_has_no_forged_origin(tmp_path):
    from test_market_02c import prepare
    with SQLiteEventStore(tmp_path / "production-lot.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db); clock.open_session("village")
        db.append("village", "grain-origin", _rev(db, "village"), [
            origin("grain4", "bakery", "bakery", 4, "grain", "bakery")
        ], bootstrap=True)
        maker = NPCProductionService(db, clock)
        after = maker.start("village", "basim", "bread", "bake1",
                            expected_revision=_rev(db, "village")).state
        lot = after.property_custody_lots["grain4"]
        assert lot["known_holders"] == {"bakery": 2}
        assert lot["exited_quantity"] == 2
        assert lot["unresolved_quantity"] == 0
        assert all(row["resource"] != "bread" for row in after.property_custody_lots.values())
        assert db.verify("village").to_dict() == after.to_dict()


def test_forged_lot_exceeds_real_inventory_is_rejected(scene):
    db, clock = scene
    register(db, [origin()])
    before = db.load("v").to_dict()
    before["property_custody_lots"]["origin-bread"]["known_holders"]["basim"] = 1
    before["property_custody_lots"]["origin-bread"]["known_holders"]["bakery"] = 1
    with pytest.raises(ValueError, match="exceeds actual inventory"):
        WorldState.from_dict(before)


def test_forged_lot_quantity_beyond_original_rejected(scene):
    db, clock = scene
    register(db, [origin()])
    forged = db.load("v").to_dict()
    forged["property_custody_lots"]["origin-bread"]["unresolved_quantity"] = 3
    with pytest.raises(ValueError, match="must be conserved"):
        WorldState.from_dict(forged)


def test_depleted_original_stock_leaves_no_phantom_certified_units(scene):
    db, clock = scene
    register(db, [origin()])
    _take(db, clock, name="first")
    final = _take(db, clock, actor="nora", name="second")
    assert final.resources["bakery"]["bread"] == 0
    assert "bakery" not in final.property_custody_lots["origin-bread"]["known_holders"]
    assert sum(final.property_custody_lots["origin-bread"]["known_holders"].values()) == 2
    assert db.verify("v").to_dict() == final.to_dict()


def test_replay_snapshot_and_restart_preserves_lot_certainty(tmp_path):
    with SQLiteEventStore(tmp_path / "persist.sqlite") as db:
        from test_property_02h1 import village
        village(db)
        clock = TimeEngine(db); clock.open_session("v")
        db.append("v", "orig", _rev(db), [origin()], bootstrap=True)
        _take(db, clock)
        before = db.snapshot("v").to_dict()
        assert db.verify("v").to_dict() == before
    with SQLiteEventStore(tmp_path / "persist.sqlite") as reopened:
        assert reopened.verify("v").to_dict() == before


def test_rejected_atomic_taking_does_not_write_lot_movement(scene):
    db, clock = scene
    register(db, [origin()])
    before = db.load("v").to_dict()
    with pytest.raises(InvalidEvent):
        _take(db, clock, qty=3)
    assert db.load("v").to_dict() == before


def test_barter_records_both_commodity_transfer_legs(tmp_path):
    from test_market_02c import prepare
    with SQLiteEventStore(tmp_path / "barter-lots.sqlite") as db:
        prepare(db)
        clock = TimeEngine(db); clock.open_session("village")
        db.append("village", "two-origins", _rev(db, "village"), [
            origin("huda-bread", "huda", "huda", 2, "bread", "bakery"),
            origin("layla-grain", "layla", "layla", 2, "grain", "bakery"),
        ], bootstrap=True)
        market = NPCMarketService(db, clock)
        market.post("village", "huda", "huda", "bakery", "barter-quote",
                    "bread", 2, "grain", 1,
                    expected_revision=_rev(db, "village"))
        after = market.buy("village", "layla", "barter-one", "barter-quote",
                           1, 1, expected_revision=_rev(db, "village")).state
        bread = after.property_custody_lots["huda-bread"]
        grain = after.property_custody_lots["layla-grain"]
        assert dict(bread["known_holders"]) == {"huda": 1, "layla": 1}
        assert dict(grain["known_holders"]) == {"huda": 1, "layla": 1}
        assert after.resources["layla"]["bread"] == 1
        assert after.resources["huda"]["grain"] == 1
        assert len(after.property_custody_moves) == 2
        assert db.verify("village").to_dict() == after.to_dict()
