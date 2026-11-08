"""PLAY-44 acceptance: two real professional procurement and baking cycles.

The baker's professional decisions are automatic; nobody manually posts,
purchases, moves, deposits, starts work, pays wages or sells bread here.
Events, real roads, local stalls, real customer cash and replay are asserted.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine, WorldState,
)
from carlos_sim.professional_trade import (
    choose_local_grain_purchase, choose_professional_known_road,
    choose_local_grain_offer,
)
from test_play43_grain_deposit import (
    WORLD, FARM, BAKERY, BAKER, FARMER, CUSTOMER, _boot,
)

CUSTOMERS = ("anna", "boris", "cora", "dina")


def _setup(db):
    previous = _boot(db)
    tail = [DomainEvent(
        "NPCRoutineConfigured", None, "baker actually works bakery shifts",
        0, {
            "npc_id": BAKER, "home_id": FARM, "workplace_id": BAKERY,
            "work_start": 0, "work_end": 20000,
        },
    )]
    for who in CUSTOMERS:
        tail.extend([
            DomainEvent(
                "EntityCreated", None, "finite customer joins village", 0,
                {"id": who, "name": who.title(), "location_id": BAKERY,
                 "controller": "npc"},
            ),
            DomainEvent(
                "NPCConfigured", None, "customer has genuine food need", 0,
                {"npc_id": who, "role": "resident",
                 "needs": {"hunger": 85, "fatigue": 0, "safety": 0},
                 "goals": {"earn": 10, "explore": 10, "survive": 30}},
            ),
            DomainEvent(
                "ResourceChanged", None, "finite opening customer food", 0,
                {"owner_id": who, "resource": "food",
                 "previous": None, "current": 0, "source": "initialization"},
            ),
            DomainEvent(
                "ResourceChanged", None, "finite opening customer copper", 0,
                {"owner_id": who, "resource": "coin_copper",
                 "previous": None, "current": 2, "source": "initialization"},
            ),
        ])
    return db.append(WORLD, "play44:remaining-time-zero", previous.revision,
                     tail, bootstrap=True)


def _engine(db, clock, *, enabled=True):
    return LivingWorldEngine(
        db, clock, economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=True, routines_enabled=True,
        navigation_enabled=True, professional_procurement_enabled=enabled,
        max_events_per_advance=5000,
    )


def _coins(state):
    return sum(wallet.get("coin_copper", 0)
               for wallet in state.resources.values())


def _advance(db, engine, target):
    before = db.load(WORLD)
    assert target > before.time
    committed = engine.advance(
        WORLD, seconds=target-before.time,
        command_id=f"play44:clock:{target}",
        expected_revision=before.revision,
    ).state
    assert committed.time == target
    assert db.verify(WORLD).to_dict() == committed.to_dict()
    assert _coins(committed) == 12
    assert all(value >= 0 for wallet in committed.resources.values()
               for value in wallet.values() if type(value) is int)
    for t in committed.travels.values():
        assert t["due"] - t["start"] == committed.routes[t["route_id"]]["seconds"]
        if t["status"] == "arrived":
            assert t["arrived_at"] == t["due"]
    return committed


def test_two_autonomous_professional_work_cycles_with_local_market_and_finite_cash(tmp_path):
    with SQLiteEventStore(tmp_path / "automatic-grain-workshops.sqlite") as db:
        initial = _setup(db)
        assert _coins(initial) == 12
        assert initial.resources[FARM]["grain"] == 2
        assert initial.resources[BAKERY]["grain"] == 0
        assert not initial.market_offers
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            states = []
            for target in (1, 60, 120, 210, 211, 271, 331, 421, 422):
                state = _advance(db, engine, target)
                states.append(state)
            final = states[-1]
            raw = [e for (e,) in db.db.execute(
                "SELECT payload FROM events WHERE world_id=? ORDER BY seq",
                (WORLD,),
            ).fetchall()]
            event_types = [json.loads(e)["event_type"] for e in raw]
            assert event_types.count("WorkshopMaterialDeposited") == 2
            assert event_types.count("ProductionWagePaid") == 2
            assert event_types.count("MarketTradeExecuted") == 6
            grain_trades = [
                t for t in final.market_trades.values() if t["resource"] == "grain"
            ]
            bread_trades = [
                t for t in final.market_trades.values() if t["resource"] == "food"
            ]
            assert len(grain_trades) == 2
            assert len(bread_trades) == 4
            assert all(t["buyer_id"] == BAKER and t["site_id"] == FARM
                       and t["total_paid"] == 2 for t in grain_trades)
            assert {t["buyer_id"] for t in bread_trades} == set(CUSTOMERS)
            paid = [j for j in final.production_jobs.values()
                    if j["npc_id"] == BAKER and "work_wage" in j]
            assert len(paid) == 2
            assert all(j["work_wage"]["amount"] == 2 for j in paid)
            trips = [t for t in final.travels.values() if t["npc_id"] == BAKER]
            assert len(trips) >= 4
            assert any(t["destination"] == FARM for t in trips)
            assert all(t["status"] == "arrived" or t["due"] > final.time
                       for t in trips)
            assert final.resources[FARM]["grain"] == 0
            assert final.resources[BAKERY]["food"] == 0
            assert final.resources[BAKER]["grain"] == 0
            assert _coins(final) == 12
            assert final.resources[FARM]["coin_copper"] == 4
            assert final.resources[BAKERY]["coin_copper"] == 4
            assert final.resources[BAKER]["coin_copper"] == 2
            assert final.resources[CUSTOMER]["coin_copper"] == 2
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == final.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY44_AUTO_REAL_ECONOMY", json.dumps({
                "grain_sales": len(grain_trades),
                "bread_sales": len(bread_trades),
                "funded_wages": len(paid),
                "physical_legs": len(trips),
                "total_copper": _coins(final),
            }, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_professional_route_never_reads_unvisited_remote_farm_stock(tmp_path):
    with SQLiteEventStore(tmp_path / "private-route.sqlite") as db:
        original = _setup(db)
        raw = original.to_dict()
        raw["navigation"][BAKER] = {
            "known_routes": ["farm-bakery"],
            "visited": [BAKERY],
            "target": None,
        }
        previous = None
        for amount in (0, 1, 2, 50):
            shaped = dict(raw)
            shaped["resources"] = {owner: dict(stock)
                                   for owner, stock in raw["resources"].items()}
            shaped["resources"][FARM]["grain"] = amount
            state = WorldState.from_dict(shaped)
            route = choose_professional_known_road(state, BAKER)
            assert route is not None
            assert route.route_id == "farm-bakery"
            assert route.reason == "unknown-supplier-exploration-on-known-road"
            assert previous is None or route == previous
            assert choose_local_grain_purchase(state, BAKER) is None
            previous = route


@pytest.mark.parametrize("bad", [None, 0, 1, "true", [], {}])
def test_procurement_flag_is_strictly_boolean_and_opt_in(tmp_path, bad):
    with SQLiteEventStore(tmp_path / "invalid-flags.sqlite") as db:
        clock = TimeEngine(db)
        with pytest.raises(ValueError, match="professional_procurement_enabled"):
            LivingWorldEngine(db, clock, professional_procurement_enabled=bad)


def test_procurement_fails_without_required_economy_and_known_roads(tmp_path):
    with SQLiteEventStore(tmp_path / "no-route.sqlite") as db:
        state = _setup(db)
        assert choose_professional_known_road(state, BAKER) is None
        assert choose_local_grain_offer(state, FARMER) is not None
        with pytest.raises(ValueError, match="professional_procurement_enabled"):
            LivingWorldEngine(db, TimeEngine(db),
                              economic_enabled=True,
                              professional_procurement_enabled=True)
        with pytest.raises(ValueError, match="professional_procurement_enabled"):
            LivingWorldEngine(
                db, TimeEngine(db), economic_enabled=True,
                agriculture_enabled=True, economy_only_enabled=True,
                navigation_enabled=True, routines_enabled=True,
                shopping_routes_enabled=True,
                professional_procurement_enabled=True,
                consumption_enabled=True, survival_enabled=True,
            )


def test_default_off_and_explicit_false_have_identical_events_and_state(tmp_path):
    snapshots = []
    histories = []
    for explicit in (False, True):
        with SQLiteEventStore(tmp_path / f"disabled-{explicit}.sqlite") as db:
            _setup(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                flags = dict(economic_enabled=True, agriculture_enabled=True,
                             economy_only_enabled=True, routines_enabled=True,
                             navigation_enabled=True, max_events_per_advance=5000)
                if explicit:
                    flags["professional_procurement_enabled"] = False
                engine = LivingWorldEngine(db, clock, **flags)
                state = _advance(db, engine, 422)
                snapshots.append(state.to_dict())
                histories.append([
                    payload for (payload,) in db.db.execute(
                        "SELECT payload FROM events WHERE world_id=? ORDER BY seq",
                        (WORLD,),
                    ).fetchall()
                ])
                assert not [e for e in state.market_trades.values()
                            if e["resource"] == "grain"]
                assert not any(j["npc_id"] == BAKER for j
                               in state.production_jobs.values())
            finally:
                clock.close_session(WORLD)
    assert snapshots[0] == snapshots[1]
    assert histories[0] == histories[1]


def test_sold_out_farmer_cannot_create_third_sale_or_infinite_baker_market_loop(tmp_path):
    with SQLiteEventStore(tmp_path / "honest-sold-out.sqlite") as db:
        _setup(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            state = _advance(db, engine, 900)
            bought = [t for t in state.market_trades.values()
                      if t["resource"] == "grain"]
            assert len(bought) == 2
            assert state.resources[FARM]["grain"] == 0
            assert _coins(state) == 12
            legs = [t for t in state.travels.values()
                    if t["npc_id"] == BAKER]
            assert len(legs) == 6, "third funded errand must return, without oscillating"
            assert all(t["status"] == "arrived" for t in legs)
            assert state.entities[BAKER]["location_id"] == BAKERY
            assert state.resources[BAKER]["grain"] == 0
            assert len([j for j in state.production_jobs.values()
                        if j["npc_id"] == BAKER]) == 2
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


def test_farmer_departure_during_actual_road_travel_blocks_purchase_and_worker_returns(tmp_path):
    from carlos_sim.movement import NPCMovementService
    with SQLiteEventStore(tmp_path / "seller-absent.sqlite") as db:
        _setup(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            first = _advance(db, engine, 1)
            assert any(t["npc_id"] == BAKER and t["status"] == "traveling"
                       for t in first.travels.values())
            assert any(o["resource"] == "grain"
                       for o in first.market_offers.values())
            # A real seller is now unavailable while traveling along the
            # same road; an old recorded quote is NOT a remote seller.
            leaving = NPCMovementService(db, clock).start(
                WORLD, FARMER, "farm-bakery", "farmer-is-away",
                expected_revision=first.revision,
            )
            assert leaving.due == first.time + 60
            state = _advance(db, engine, 240)
            assert not state.market_trades
            assert not state.production_jobs
            assert state.resources[FARM]["grain"] == 2
            assert state.resources[BAKER]["grain"] == 0
            assert state.entities[BAKER]["location_id"] == BAKERY
            legs = [t for t in state.travels.values()
                    if t["npc_id"] == BAKER]
            assert len(legs) == 2
            assert all(t["status"] == "arrived" for t in legs)
            assert _coins(state) == 12
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


def test_pure_professional_quote_needs_real_staff_and_known_copper(tmp_path):
    with SQLiteEventStore(tmp_path / "seller-capacity.sqlite") as db:
        raw = _setup(db).to_dict()
        assert choose_local_grain_offer(WorldState.from_dict(raw), FARMER)
        # No real physical keeper at the stall means no sale quotation.
        raw["entities"][FARMER]["location_id"] = BAKERY
        assert choose_local_grain_offer(WorldState.from_dict(raw), FARMER) is None
        raw["entities"][FARMER]["location_id"] = FARM
        raw["resources"][FARM]["coin_copper"] = None
        assert choose_local_grain_offer(WorldState.from_dict(raw), FARMER) is None
