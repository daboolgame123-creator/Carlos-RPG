"""PLAY-46 physical two-material market with a genuine repair-industry buyer.

A scripted integration *test* drives trusted APIs; there is no claim this is
autonomous coal-shopping NPC AI. All real movement, ownership and cash
transfers pass the normal reducer checks and survive SQLite replay.
"""
from __future__ import annotations

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.market import NPCMarketService
from carlos_sim.movement import NPCMovementService
from carlos_sim.production import NPCProductionService
from carlos_sim.workshop_transfers import NPCWorkshopService

WORLD = "play46-physical-smelting"
FORGE, MINE, KILN = "smithy", "iron_mine", "charcoal_kiln"
SMITH, MINER, BURNER, CUSTOMER = "smith", "miner", "burner", "mechanic"


def _e(kind, data):
    return DomainEvent(kind, None, "finite trusted setup", 0, data)


def _initialize(db):
    db.create_world(WORLD)
    events = [_e("LocationCreated", {"id": x, "name": x})
              for x in (FORGE, MINE, KILN)]
    for rid, a, b, sec in (
        ("smith-mine", FORGE, MINE, 30),
        ("smith-kiln", FORGE, KILN, 40),
    ):
        events.append(_e("RouteCreated", {
            "id": rid, "a": a, "b": b, "seconds": sec,
        }))
    for who, role, place in (
        (SMITH, "blacksmith", FORGE),
        (MINER, "miner", MINE),
        (BURNER, "charcoal_burner", KILN),
        (CUSTOMER, "repairer", FORGE),
    ):
        events.extend([
            _e("EntityCreated", {
                "id": who, "name": who,
                "location_id": place, "controller": "npc",
            }),
            _e("NPCConfigured", {
                "npc_id": who, "role": role,
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ])
    resources = {
        FORGE: {"iron_ore": 0, "charcoal": 0, "anvil": 1,
                "iron_fitting": 0, "coin_copper": 0},
        MINE: {"iron_ore": 1, "coin_copper": 0},
        KILN: {"charcoal": 1, "coin_copper": 0},
        SMITH: {"coin_copper": 2, "iron_ore": 0, "charcoal": 0},
        CUSTOMER: {"coin_copper": 2, "iron_fitting": 0},
    }
    for owner, owned in resources.items():
        for resource, n in owned.items():
            events.append(_e("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": n,
                "source": "initialization",
            }))
    for place, keeper in ((MINE, MINER), (KILN, BURNER), (FORGE, SMITH)):
        events.append(_e("MarketStallConfigured", {
            "site_id": place, "keeper_id": keeper,
        }))
    events.append(_e("ProductionRecipeConfigured", {
        "id": "iron-plus-fuel", "site_id": FORGE, "role": "blacksmith",
        "inputs": [
            {"resource": "iron_ore", "amount": 1},
            {"resource": "charcoal", "amount": 1},
        ],
        "output_resource": "iron_fitting", "output_amount": 1,
        "tool_resource": "anvil", "duration_seconds": 90,
        "wage_coin": 1,
    }))
    return db.append(WORLD, "physical:boot", 0, events, bootstrap=True)


def _money(state):
    return sum(owned.get("coin_copper", 0) for owned in state.resources.values())


def _leg(db, clock, movement, route, label):
    before = db.load(WORLD)
    started = movement.start(WORLD, SMITH, route, label,
                             expected_revision=before.revision)
    state = clock.advance(
        WORLD, seconds=started.due-before.time,
        command_id="physical:wait:" + label,
        expected_revision=db.load(WORLD).revision,
    ).state
    assert db.verify(WORLD).to_dict() == state.to_dict()
    assert _money(state) == 4
    return state


def test_purchased_ore_and_charcoal_cross_4_roads_and_fund_smith_wage(tmp_path):
    with SQLiteEventStore(tmp_path / "physical-chains.sqlite") as db:
        state = _initialize(db)
        assert _money(state) == 4
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            movement = NPCMovementService(db, clock)
            market = NPCMarketService(db, clock)
            workshop = NPCWorkshopService(db, clock)
            production = NPCProductionService(db, clock)
            for route, owner, seller, item, label in (
                ("smith-mine", MINE, MINER, "iron_ore", "ore"),
                ("smith-kiln", KILN, BURNER, "charcoal", "coal"),
            ):
                _leg(db, clock, movement, route, "out-" + label)
                asked = market.post(
                    WORLD, seller, owner, owner, "offer-" + label,
                    item, 1, "coin_copper", 1,
                    expected_revision=db.load(WORLD).revision,
                )
                purchase = market.buy(
                    WORLD, SMITH, "buy-" + label, "offer-" + label,
                    1, 1, expected_revision=asked.state.revision,
                )
                state = purchase.state
                assert state.resources[SMITH][item] == 1
                assert state.resources[FORGE][item] == 0
                assert _money(state) == 4
                _leg(db, clock, movement, route, "home-" + label)
                deposited = workshop.deposit(
                    WORLD, SMITH, FORGE, item, 1,
                    command_id="deliver-" + label,
                    expected_revision=db.load(WORLD).revision,
                )
                state = deposited.state
                assert state.resources[SMITH][item] == 0
                assert state.resources[FORGE][item] == 1
                assert _money(state) == 4
            assert len(state.market_trades) == 2
            produced = production.start(
                WORLD, SMITH, "iron-plus-fuel", "actual-smelting",
                expected_revision=state.revision,
            ).state
            assert produced.resources[FORGE]["iron_ore"] == 0
            assert produced.resources[FORGE]["charcoal"] == 0
            assert produced.resources[FORGE]["anvil"] == 1
            done = clock.advance(
                WORLD, seconds=90, command_id="physical:smelt",
                expected_revision=produced.revision,
            ).state
            assert done.resources[FORGE]["iron_fitting"] == 1
            quote = market.post(
                WORLD, SMITH, FORGE, FORGE, "finished-product",
                "iron_fitting", 1, "coin_copper", 2,
                expected_revision=done.revision,
            )
            bought = market.buy(
                WORLD, CUSTOMER, "repairer-purchase", "finished-product",
                1, 2, expected_revision=quote.state.revision,
            ).state
            assert bought.resources[CUSTOMER]["iron_fitting"] == 1
            assert bought.resources[FORGE]["coin_copper"] == 2
            assert _money(bought) == 4
            paid = db.append(WORLD, "physical:real-wage", bought.revision, [
                DomainEvent("ProductionWagePaid", None, "real sold output funds worker",
                            bought.time, {"job_id": "actual-smelting", "amount": 1}),
            ], production_authorized=True)
            assert paid.resources[FORGE]["coin_copper"] == 1
            assert paid.resources[SMITH]["coin_copper"] == 1
            assert _money(paid) == 4
            assert len(paid.market_trades) == 3
            assert sum(t["status"] == "arrived" for t in paid.travels.values()) == 4
            assert dict(paid.production_jobs["actual-smelting"][
                "input_after_by_resource"]) == {"iron_ore": 0, "charcoal": 0}
            assert db.verify(WORLD).to_dict() == paid.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == paid.to_dict()
        finally:
            clock.close_session(WORLD)



def _auto_boot(db):
    """Smith's actual work shift and contract are initialized at time zero."""
    state = _initialize(db)
    return db.append(WORLD, "auto:work-contract", state.revision, [
        _e("NPCRoutineConfigured", {
            "npc_id": SMITH, "home_id": MINE,
            "workplace_id": FORGE, "work_start": 0, "work_end": 20_000,
        }),
    ], bootstrap=True)


def _auto_engine(db, clock, enabled=True):
    from carlos_sim import LivingWorldEngine
    return LivingWorldEngine(
        db, clock, economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=True, navigation_enabled=True,
        routines_enabled=True, multi_professional_markets_enabled=True,
        compound_procurement_enabled=enabled,
        max_events_per_advance=5000,
    )


def _auto_until(db, engine, stop, label):
    current = db.load(WORLD)
    result = engine.advance(
        WORLD, seconds=stop-current.time,
        command_id="auto:time:" + label,
        expected_revision=current.revision,
    )
    assert result.state.time == stop
    assert db.verify(WORLD).to_dict() == result.state.to_dict()
    return result.state


def test_smith_autonomously_buys_both_distinct_inputs_on_roads_and_smelts(tmp_path):
    """No buyer/travel/production calls: one trusted world-time simulation only."""
    with SQLiteEventStore(tmp_path / "truly-autonomous.sqlite") as db:
        _auto_boot(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _auto_engine(db, clock)
            state = _auto_until(db, engine, 420, "one-long-wait")
            assert state.resources[FORGE]["iron_fitting"] == 1
            assert state.resources[FORGE]["iron_ore"] == 0
            assert state.resources[FORGE]["charcoal"] == 0
            trades = [t for t in state.market_trades.values() if t["buyer_id"] == SMITH]
            assert sorted(t["resource"] for t in trades) == ["charcoal", "iron_ore"]
            assert all(t["quantity"] == 1 and t["total_paid"] == 1 for t in trades)
            assert [t["site_id"] for t in sorted(trades,
                     key=lambda t: t["executed_at"])] == [MINE, KILN]
            jobs = [j for j in state.production_jobs.values() if j["npc_id"] == SMITH]
            assert len(jobs) == 1 and jobs[0]["status"] == "completed"
            assert dict(jobs[0]["input_after_by_resource"]) == {
                "iron_ore": 0, "charcoal": 0,
            }
            journeys = [t for t in state.travels.values()
                        if t["npc_id"] == SMITH]
            assert len(journeys) == 4
            assert all(t["status"] == "arrived" for t in journeys)
            assert _money(state) == 4
            assert state.resources[SMITH]["coin_copper"] == 0
            assert not any("work_wage" in j for j in jobs), (
                "No one bought the fitting yet; wages must not be minted"
            )
            # A customer paying at the *real counter* funds one later wage.
            priced = [o for o in state.market_offers.items()
                      if o[1]["resource"] == "iron_fitting"
                      and o[1]["status"] == "open"]
            assert len(priced) == 1
            offer_id, offer = priced[0]
            state = NPCMarketService(db, clock).buy(
                WORLD, CUSTOMER, "repairer-buys-autonomous-output",
                offer_id, 1, offer["unit_price"],
                expected_revision=state.revision,
            ).state
            assert _money(state) == 4
            state = _auto_until(db, engine, 421, "funded-salary")
            assert len([j for j in state.production_jobs.values()
                        if "work_wage" in j]) == 1
            assert state.resources[SMITH]["coin_copper"] == 1
            assert _money(state) == 4
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


def test_smith_does_not_conjure_sold_out_material_or_distant_price(tmp_path):
    from carlos_sim.movement import NPCMovementService
    from carlos_sim.compound_professional_trade import choose_compound_purchase

    with SQLiteEventStore(tmp_path / "seller-walks-away.sqlite") as db:
        _auto_boot(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _auto_engine(db, clock)
            state = _auto_until(db, engine, 1, "first-day")
            # Miner leaves while the smith is still traveling to the mine.
            mover = NPCMovementService(db, clock)
            mover.start(WORLD, MINER, "smith-mine", "miner-leaves",
                        expected_revision=state.revision)
            state = _auto_until(db, engine, 420, "seller-absent")
            assert not any(t["resource"] == "iron_ore"
                           for t in state.market_trades.values())
            assert state.resources[FORGE]["iron_fitting"] == 0
            assert state.resources[MINE]["iron_ore"] == 1
            assert _money(state) == 4
            assert len([t for t in state.travels.values()
                        if t["npc_id"] == SMITH]) <= 6
            assert choose_compound_purchase(state, SMITH) is None
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)


def test_multi_compound_flag_is_strict_default_off(tmp_path):
    import pytest
    from carlos_sim import LivingWorldEngine

    with SQLiteEventStore(tmp_path / "flag.sqlite") as db:
        clock = TimeEngine(db)
        for bad in ("yes", 1, None, (), {}, []):
            with pytest.raises(ValueError, match="compound_procurement_enabled"):
                LivingWorldEngine(db, clock,
                                  compound_procurement_enabled=bad)
        with pytest.raises(ValueError, match="compound_procurement_enabled"):
            LivingWorldEngine(db, clock, compound_procurement_enabled=True)


def test_one_wait_vs_partitioned_wait_preserves_individual_material_trades(tmp_path):
    outputs = []
    for name, targets in (
        ("single", (420,)),
        ("chunked", (1, 30, 61, 101, 141, 231, 420)),
    ):
        with SQLiteEventStore(tmp_path / (name + ".sqlite")) as db:
            _auto_boot(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                engine = _auto_engine(db, clock)
                for stop in targets:
                    state = _auto_until(db, engine, stop, f"{name}-{stop}")
                receipts = sorted((
                    v["resource"], v["site_id"], v["executed_at"],
                    v["total_paid"]) for v in state.market_trades.values())
                jobs = sorted((j["recipe_id"], j["started_at"],
                               j["finished_at"],
                               tuple(sorted(dict(j[
                                 "input_after_by_resource"]).items())))
                              for j in state.production_jobs.values())
                outputs.append((receipts, jobs,
                                state.resources[FORGE]["iron_fitting"],
                                _money(state)))
            finally:
                clock.close_session(WORLD)
    assert outputs[0] == outputs[1]



def _add_second_autonomous_profession(db):
    """Trusted time-zero repair workshop, no scripted buyer or product."""
    site, worker = "repair_shop", "repairman"
    current = db.load(WORLD)
    events = [
        _e("LocationCreated", {"id": site, "name": "Repair Shop"}),
        _e("RouteCreated", {
            "id": "smith-repair", "a": FORGE, "b": site, "seconds": 50,
        }),
        _e("EntityCreated", {
            "id": worker, "name": "Repairman",
            "location_id": site, "controller": "npc",
        }),
        _e("NPCConfigured", {
            "npc_id": worker, "role": "repairer",
            "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
            "goals": {"earn": 10, "explore": 10, "survive": 30},
        }),
    ]
    stock = {
        site: {"iron_fitting": 0, "repaired_gear": 0,
               "wrench": 1, "coin_copper": 0},
        worker: {"iron_fitting": 0, "coin_copper": 2},
    }
    for owner, owned in stock.items():
        for item, count in owned.items():
            events.append(_e("ResourceChanged", {
                "owner_id": owner, "resource": item,
                "previous": None, "current": count,
                "source": "initialization",
            }))
    events.extend([
        _e("ProductionRecipeConfigured", {
            "id": "repair-tools", "site_id": site, "role": "repairer",
            "input_resource": "iron_fitting", "input_amount": 1,
            "output_resource": "repaired_gear", "output_amount": 1,
            "tool_resource": "wrench", "duration_seconds": 90,
        }),
        _e("NPCRoutineConfigured", {
            "npc_id": worker, "home_id": KILN, "workplace_id": site,
            "work_start": 250, "work_end": 20_000,
        }),
    ])
    return db.append(WORLD, "repairer:genesis", current.revision,
                     events, bootstrap=True)


def test_all_three_trades_both_professions_act_without_manual_commands(tmp_path):
    """Miner/burner -> smith -> repairer, entire local economic sequence automatic."""
    with SQLiteEventStore(tmp_path / "autonomous-two-professions.sqlite") as db:
        _auto_boot(db)
        initial = _add_second_autonomous_profession(db)
        assert _money(initial) == 6
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = _auto_until(db, _auto_engine(db, clock), 700, "end-to-end")
            assert state.resources[FORGE]["iron_ore"] == 0
            assert state.resources[FORGE]["charcoal"] == 0
            assert state.resources[FORGE]["iron_fitting"] == 0
            assert state.resources["repair_shop"]["repaired_gear"] == 1
            trades = list(state.market_trades.values())
            assert sorted(t["resource"] for t in trades) == [
                "charcoal", "iron_fitting", "iron_ore",
            ]
            assert {(t["buyer_id"], t["resource"]) for t in trades} == {
                (SMITH, "iron_ore"), (SMITH, "charcoal"),
                ("repairman", "iron_fitting"),
            }
            completed = [j for j in state.production_jobs.values()
                         if j["status"] == "completed"]
            assert len(completed) == 2
            assert {j["recipe_id"] for j in completed} == {
                "iron-plus-fuel", "repair-tools",
            }
            assert sum("work_wage" in j for j in completed) == 1
            assert state.resources[SMITH]["coin_copper"] == 1
            assert _money(state) == 6
            repaired_trips = [t for t in state.travels.values()
                              if t["npc_id"] == "repairman"]
            assert len(repaired_trips) == 2
            assert all(t["status"] == "arrived" for t in repaired_trips)
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY46_FULL_AUTO_ECONOMY",
                  "trades=3 production_jobs=2 funded_wages=1 copper=6")
        finally:
            clock.close_session(WORLD)


def test_compound_autonomy_can_be_disabled_without_blocking_old_economy(tmp_path):
    with SQLiteEventStore(tmp_path / "autonomous-flag-off.sqlite") as db:
        state = _auto_boot(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = _auto_until(db, _auto_engine(db, clock, enabled=False),
                                420, "explicitly-disabled")
            assert state.resources[FORGE]["iron_fitting"] == 0
            assert not state.market_trades
            assert not state.production_jobs
            assert _money(state) == 4
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
