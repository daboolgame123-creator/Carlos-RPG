"""PLAY-45: one physical multi-profession economy, no artificial customers.

All actors are real NPCs. Nobody scripts the purchases, material deposits,
production jobs, sales, travel, or wages after trusted time-zero setup.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine, WorldState
from carlos_sim.multi_professional_trade import (
    choose_local_material_offer, choose_local_material_purchase,
    choose_material_known_road,
)

WORLD = "play45-multisector"
WOOD = "lumberyard"
IRON = "ore-yard"
CARP = "carpentry"
SMITH = "forge"
BUILD = "building"
REPAIR = "repair"
HOME = "unmapped-home"


def _e(kind, data):
    return DomainEvent(kind, None, "finite physical PLAY45 bootstrap", 0, data)


def _seed(db, *, wood=1, iron=1, carpenter_cash=1, smith_cash=1,
          builder_cash=2, repairer_cash=2):
    db.create_world(WORLD)
    sites = (WOOD, IRON, CARP, SMITH, BUILD, REPAIR, HOME)
    events = [_e("LocationCreated", {"id": site, "name": site.title()})
              for site in sites]
    for rid, a, b, seconds in (
        ("wood-carp", WOOD, CARP, 30),
        ("iron-smith", IRON, SMITH, 30),
        ("carp-build", CARP, BUILD, 90),
        ("smith-repair", SMITH, REPAIR, 90),
    ):
        events.append(_e("RouteCreated",
                         {"id": rid, "a": a, "b": b, "seconds": seconds}))

    staff = (
        ("lumberer", "woodcutter", WOOD),
        ("miner", "miner", IRON),
        ("carpenter", "carpenter", CARP),
        ("smith", "blacksmith", SMITH),
        ("builder", "builder", BUILD),
        ("repairer", "repairer", REPAIR),
    )
    for who, role, site in staff:
        events.extend([
            _e("EntityCreated", {
                "id": who, "name": who.title(), "location_id": site,
                "controller": "npc",
            }),
            _e("NPCConfigured", {
                "npc_id": who, "role": role,
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ])
        if who not in ("lumberer", "miner"):
            events.append(_e("NPCRoutineConfigured", {
                "npc_id": who, "home_id": HOME, "workplace_id": site,
                "work_start": 250 if who in ("builder", "repairer") else 0,
                "work_end": 20_000,
            }))

    starting = {
        WOOD: {"wood": wood, "coin_copper": 0},
        IRON: {"iron_ore": iron, "coin_copper": 0},
        CARP: {"wood": 0, "plank": 0, "saw": 1, "coin_copper": 0},
        SMITH: {"iron_ore": 0, "iron_fitting": 0,
                "anvil": 1, "coin_copper": 0},
        BUILD: {"plank": 0, "frame": 0, "hammer": 1, "coin_copper": 0},
        REPAIR: {"iron_fitting": 0, "fixed_gear": 0,
                 "wrench": 1, "coin_copper": 0},
        "carpenter": {"wood": 0, "coin_copper": carpenter_cash},
        "smith": {"iron_ore": 0, "coin_copper": smith_cash},
        "builder": {"plank": 0, "coin_copper": builder_cash},
        "repairer": {"iron_fitting": 0, "coin_copper": repairer_cash},
    }
    for owner, resources in starting.items():
        for item, count in resources.items():
            events.append(_e("ResourceChanged", {
                "owner_id": owner, "resource": item,
                "previous": None, "current": count,
                "source": "initialization",
            }))

    for site, who in ((WOOD, "lumberer"), (IRON, "miner"),
                      (CARP, "carpenter"), (SMITH, "smith")):
        events.append(_e("MarketStallConfigured", {
            "site_id": site, "keeper_id": who,
        }))

    for ident, site, role, source, output, tool, wage in (
        ("saw-board", CARP, "carpenter", "wood", "plank", "saw", 1),
        ("forge-fitting", SMITH, "blacksmith", "iron_ore",
         "iron_fitting", "anvil", 1),
        ("build-frame", BUILD, "builder", "plank", "frame", "hammer", None),
        ("repair-gear", REPAIR, "repairer", "iron_fitting",
         "fixed_gear", "wrench", None),
    ):
        recipe = {
            "id": ident, "site_id": site, "role": role,
            "input_resource": source, "input_amount": 1,
            "output_resource": output, "output_amount": 1,
            "tool_resource": tool, "duration_seconds": 90,
        }
        if wage is not None:
            recipe["wage_coin"] = wage
        events.append(_e("ProductionRecipeConfigured", recipe))
    return db.append(WORLD, "play45:bootstrap", 0, events, bootstrap=True)


def _engine(db, clock, enabled=True):
    return LivingWorldEngine(
        db, clock, economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=True, routines_enabled=True,
        navigation_enabled=True, multi_professional_markets_enabled=enabled,
        max_events_per_advance=5000,
    )


def _cash(state):
    return sum(x.get("coin_copper", 0) for x in state.resources.values())


def _run(db, engine, stop, label):
    old = db.load(WORLD)
    final = engine.advance(
        WORLD, seconds=stop-old.time,
        command_id=f"play45:wait:{label}",
        expected_revision=old.revision,
    ).state
    assert final.time == stop
    assert db.verify(WORLD).to_dict() == final.to_dict()
    return final


def test_multiple_jobs_real_materials_real_buyers_and_funded_wages(tmp_path):
    with SQLiteEventStore(tmp_path / "real-four-store-chain.sqlite") as db:
        state = _seed(db)
        assert _cash(state) == 6
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            checkpoints = (1, 30, 60, 150, 250, 340, 430, 520, 700)
            for t in checkpoints:
                state = _run(db, engine, t, str(t))
                assert _cash(state) == 6
                assert all(value >= 0 for stock in state.resources.values()
                           for value in stock.values() if type(value) is int)
            trades = list(state.market_trades.values())
            assert sorted(t["resource"] for t in trades) == [
                "iron_fitting", "iron_ore", "plank", "wood",
            ]
            assert {(t["buyer_id"], t["resource"]) for t in trades} == {
                ("carpenter", "wood"), ("smith", "iron_ore"),
                ("builder", "plank"), ("repairer", "iron_fitting"),
            }
            completed = [j for j in state.production_jobs.values()
                         if j["status"] == "completed"]
            assert len(completed) == 4
            wages = [j for j in completed if "work_wage" in j]
            assert len(wages) == 2
            assert all(j["work_wage"]["amount"] == 1 for j in wages)
            assert state.resources[BUILD]["frame"] == 1
            assert state.resources[REPAIR]["fixed_gear"] == 1
            assert state.resources[WOOD]["wood"] == 0
            assert state.resources[IRON]["iron_ore"] == 0
            assert state.resources[CARP]["plank"] == 0
            assert state.resources[SMITH]["iron_fitting"] == 0
            travels = [t for t in state.travels.values()
                       if t["npc_id"] in ("carpenter", "smith",
                                       "builder", "repairer")]
            for who in ("carpenter", "smith", "builder", "repairer"):
                assert any(t["npc_id"] == who for t in travels)
            assert all(t["due"]-t["start"] ==
                       state.routes[t["route_id"]]["seconds"] for t in travels)
            assert _cash(state) == 6
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY45_REAL_MULTISECTOR", json.dumps({
                "shops": 4, "purchases": len(trades),
                "production_jobs": len(completed), "paid_wages": len(wages),
                "legs": len(travels), "copper": _cash(state),
            }, sort_keys=True))
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("bad", [None, 0, 1, "yes", [], {}])
def test_flag_rejects_non_boolean_or_incompatible_modes(tmp_path, bad):
    with SQLiteEventStore(tmp_path / "flag.sqlite") as db:
        with pytest.raises(ValueError, match="multi_professional_markets_enabled"):
            LivingWorldEngine(db, TimeEngine(db),
                              multi_professional_markets_enabled=bad)
        with pytest.raises(ValueError, match="multi_professional_markets_enabled"):
            LivingWorldEngine(
                db, TimeEngine(db), economic_enabled=True,
                agriculture_enabled=True, economy_only_enabled=True,
                navigation_enabled=True, routines_enabled=True,
                professional_procurement_enabled=True,
                multi_professional_markets_enabled=True,
            )


def test_flag_default_off_is_exactly_identical_to_explicit_false(tmp_path):
    all_states, all_events = [], []
    for yes in (False, True):
        with SQLiteEventStore(tmp_path / f"off-{yes}.sqlite") as db:
            _seed(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                settings = dict(economic_enabled=True, agriculture_enabled=True,
                                economy_only_enabled=True, routines_enabled=True,
                                navigation_enabled=True, max_events_per_advance=5000)
                if yes:
                    settings["multi_professional_markets_enabled"] = False
                engine = LivingWorldEngine(db, clock, **settings)
                state = _run(db, engine, 700, f"off-{yes}")
                all_states.append(state.to_dict())
                all_events.append(tuple(row[0] for row in db.db.execute(
                    "SELECT payload FROM events WHERE world_id=? ORDER BY seq",
                    (WORLD,),
                ).fetchall()))
                assert not state.market_trades
            finally:
                clock.close_session(WORLD)
    assert all_states[0] == all_states[1]
    assert all_events[0] == all_events[1]


def test_producer_does_not_know_remote_material_or_prices(tmp_path):
    with SQLiteEventStore(tmp_path / "privacy.sqlite") as db:
        state = _seed(db)
        raw = state.to_dict()
        raw["navigation"]["carpenter"] = {
            "known_routes": ["wood-carp"], "visited": [CARP], "target": None,
        }
        previous = None
        for amount in (0, 1, 99):
            shaped = dict(raw)
            shaped["resources"] = {owner: dict(stock)
                                   for owner, stock in raw["resources"].items()}
            shaped["resources"][WOOD]["wood"] = amount
            shaped["resources"][WOOD]["coin_copper"] = 0
            loaded = WorldState.from_dict(shaped)
            intent = choose_material_known_road(loaded, "carpenter")
            assert intent is not None
            assert intent.route_id == "wood-carp"
            assert previous is None or intent == previous
            assert choose_local_material_purchase(loaded, "carpenter") is None
            previous = intent


def test_empty_source_and_unfunded_workers_never_make_free_products(tmp_path):
    with SQLiteEventStore(tmp_path / "no-invented-stock.sqlite") as db:
        state = _seed(db, wood=0, iron=0,
                      carpenter_cash=0, smith_cash=0)
        assert _cash(state) == 4
        assert choose_local_material_offer(state, "lumberer") is None
        assert choose_local_material_offer(state, "miner") is None
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            final = _run(db, _engine(db, clock), 700, "no-funds")
            assert not final.market_trades
            assert not final.production_jobs
            assert final.resources[BUILD]["frame"] == 0
            assert final.resources[REPAIR]["fixed_gear"] == 0
            assert _cash(final) == 4
        finally:
            clock.close_session(WORLD)


def test_real_seller_leaving_while_worker_walks_blocks_wood_purchase(tmp_path):
    from carlos_sim.movement import NPCMovementService

    with SQLiteEventStore(tmp_path / "seller-absent.sqlite") as db:
        _seed(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            state = _run(db, engine, 1, "seller-moves")
            assert any(t["npc_id"] == "carpenter"
                       and t["status"] == "traveling"
                       for t in state.travels.values())
            moved = NPCMovementService(db, clock).start(
                WORLD, "lumberer", "wood-carp", "woodcutter-away",
                expected_revision=state.revision,
            )
            assert moved.due == state.time + 30
            final = _run(db, engine, 700, "away")
            assert not [t for t in final.market_trades.values()
                        if t["resource"] == "wood"]
            assert final.resources[WOOD]["wood"] == 1
            assert final.resources[CARP]["plank"] == 0
            assert final.resources[BUILD]["frame"] == 0
            assert _cash(final) == 6
        finally:
            clock.close_session(WORLD)
