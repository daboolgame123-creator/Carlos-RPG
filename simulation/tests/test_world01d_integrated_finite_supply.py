"""WORLD-01d: join finite extraction, charcoal supply, and Carlos's forge job."""
from __future__ import annotations

import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCProductionService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.store import InvalidEvent

WORLD = "world01d-integrated-finite-supply"
PLAYER = "carlos"
MINER = "miner"
WOODCUTTER = "woodcutter"
BURNER = "burner"
HOME = "home"
MINE = "iron_mine"
FOREST = "lumberyard"
KILN = "charcoal_kiln"
FORGE = "smithy"
MINE_RECIPE = "finite-iron-extraction"
WOOD_RECIPE = "finite-timber-cutting"
CHARCOAL_RECIPE = "finite-wood-charcoal"
FORGE_RECIPE = "carlos-iron-fitting"
OPENING_COPPER = 8


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01d disposable integration setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        *[_event("LocationCreated", {"id": site, "name": site})
          for site in (HOME, MINE, FOREST, KILN, FORGE)],
        *[_event("RouteCreated", {
            "id": route, "a": start, "b": end, "seconds": duration,
        }) for route, start, end, duration in (
            ("home-mine", HOME, MINE, 60),
            ("mine-forge", MINE, FORGE, 30),
            ("forge-kiln", FORGE, KILN, 40),
            ("kiln-lumberyard", KILN, FOREST, 35),
        )],
        _event("EntityCreated", {
            "id": PLAYER, "name": "Carlos", "location_id": HOME,
            "controller": "player",
        }),
    ]
    for npc, role, site in (
        (MINER, "miner", MINE),
        (WOODCUTTER, "woodcutter", FOREST),
        (BURNER, "charcoal_burner", KILN),
    ):
        events.extend((
            _event("EntityCreated", {
                "id": npc, "name": npc, "location_id": site,
                "controller": "npc",
            }),
            _event("NPCConfigured", {
                "npc_id": npc, "role": role,
                "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                "goals": {"earn": 10, "explore": 10, "survive": 30},
            }),
        ))

    # Every coin, source unit, and tool is an explicit opening endowment.
    for owner, stock in (
        (PLAYER, {"coin_copper": 2, "iron_ore": 0, "charcoal": 0}),
        (MINER, {"coin_copper": 0}),
        (WOODCUTTER, {"coin_copper": 0}),
        (BURNER, {"coin_copper": 1, "wood": 0}),
        (MINE, {"iron_ore_reserve": 1, "iron_ore": 0,
                "pickaxe": 1, "coin_copper": 1}),
        (FOREST, {"standing_timber": 1, "wood": 0,
                  "axe": 1, "coin_copper": 2}),
        (KILN, {"wood": 0, "charcoal": 0,
                "kiln_tool": 1, "coin_copper": 1}),
        (FORGE, {"iron_ore": 0, "charcoal": 0, "iron_fitting": 0,
                 "anvil": 1, "coin_copper": 1}),
    ):
        for resource, quantity in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))

    for npc, workplace in (
        (MINER, MINE), (WOODCUTTER, FOREST), (BURNER, KILN),
    ):
        events.append(_event("NPCRoutineConfigured", {
            "npc_id": npc, "home_id": HOME,
            "workplace_id": workplace, "work_start": 0,
            "work_end": 20_000,
        }))
    for site, keeper in (
        (MINE, MINER), (FOREST, WOODCUTTER), (KILN, BURNER),
    ):
        events.append(_event("MarketStallConfigured", {
            "site_id": site, "keeper_id": keeper,
        }))

    events.extend((
        _event("ProductionRecipeConfigured", {
            "id": MINE_RECIPE, "site_id": MINE, "role": "miner",
            "input_resource": "iron_ore_reserve", "input_amount": 1,
            "output_resource": "iron_ore", "output_amount": 1,
            "tool_resource": "pickaxe", "duration_seconds": 120,
            "wage_coin": 1,
        }),
        _event("ProductionRecipeConfigured", {
            "id": WOOD_RECIPE, "site_id": FOREST, "role": "woodcutter",
            "input_resource": "standing_timber", "input_amount": 1,
            "output_resource": "wood", "output_amount": 1,
            "tool_resource": "axe", "duration_seconds": 120,
            "wage_coin": 2,
        }),
        _event("ProductionRecipeConfigured", {
            "id": CHARCOAL_RECIPE, "site_id": KILN,
            "role": "charcoal_burner",
            "input_resource": "wood", "input_amount": 1,
            "output_resource": "charcoal", "output_amount": 1,
            "tool_resource": "kiln_tool", "duration_seconds": 120,
            "wage_coin": 1,
        }),
        _event("ProductionRecipeConfigured", {
            "id": FORGE_RECIPE, "site_id": FORGE, "role": "blacksmith",
            "inputs": [
                {"resource": "iron_ore", "amount": 1},
                {"resource": "charcoal", "amount": 1},
            ],
            "output_resource": "iron_fitting", "output_amount": 1,
            "tool_resource": "anvil", "duration_seconds": 90,
            "wage_coin": 1, "player_worker_id": PLAYER,
        }),
    ))
    store.append(WORLD, "world01d:bootstrap", 0, events, bootstrap=True)


def _engine(store: SQLiteEventStore, clock: TimeEngine, *,
            full_life: bool = False) -> LivingWorldEngine:
    return LivingWorldEngine(
        store, clock, max_events_per_advance=5000,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=not full_life, navigation_enabled=True,
        routines_enabled=True, multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        consumption_enabled=full_life, survival_enabled=full_life,
        supply_enabled=full_life,
        professional_full_life_enabled=full_life,
    )


def _copper(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _jobs(state, npc: str, recipe: str) -> list[dict]:
    return sorted((job for job in state.production_jobs.values()
                   if job["npc_id"] == npc and job["recipe_id"] == recipe),
                  key=lambda job: (job["started_at"], job["due"]))


def _travel(db, gateway, route: str, seconds: int,
            command: str, destination: str):
    before = db.verify(WORLD)
    trip = gateway.move(
        route, command_id=command + "-depart",
        expected_revision=before.revision,
    )
    assert trip.status == "traveling"
    wait = gateway.wait(
        seconds, command_id=command + "-arrive",
        expected_revision=trip.revision,
    )
    assert wait.time == before.time + seconds
    arrived = db.verify(WORLD)
    assert arrived.entities[PLAYER]["location_id"] == destination
    return arrived


def _local_offer(gateway, resource: str) -> dict:
    quotes = [offer for offer in gateway.offers().details["offers"]
              if offer["resource"] == resource]
    assert len(quotes) == 1, quotes
    return quotes[0]


@pytest.mark.parametrize("full_life", (False, True),
                         ids=("focused-economy", "full-life"))
def test_carlos_buys_finite_ore_and_charcoal_then_finishes_forge_job(
        tmp_path, full_life):
    database = tmp_path / "world01d-integrated.sqlite"
    with SQLiteEventStore(database) as db:
        _seed(db)
        opening = db.verify(WORLD)
        assert opening.resources[MINE]["iron_ore_reserve"] == 1
        assert opening.resources[MINE]["iron_ore"] == 0
        assert opening.resources[FOREST]["standing_timber"] == 1
        assert opening.resources[FOREST]["wood"] == 0
        assert opening.resources[KILN]["charcoal"] == 0
        assert opening.resources[FORGE]["iron_fitting"] == 0
        assert _copper(opening) == OPENING_COPPER

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock, full_life=full_life)
            gateway = PlayerGateway(
                db, clock, world_id=WORLD, player_id=PLAYER, engine=engine,
            )
            traveling = gateway.move(
                "home-mine", command_id="carlos-to-mine",
                expected_revision=opening.revision,
            )
            assert traveling.status == "traveling"
            first_hour = gateway.wait(
                60, command_id="wait-to-mine",
                expected_revision=traveling.revision,
            )
            working = db.verify(WORLD)
            assert first_hour.time == 60
            for npc, recipe in ((MINER, MINE_RECIPE),
                                (WOODCUTTER, WOOD_RECIPE)):
                jobs = _jobs(working, npc, recipe)
                assert len(jobs) == 1 and jobs[0]["status"] == "running"
                assert (jobs[0]["started_at"], jobs[0]["due"]) == (0, 120)
            assert working.resources[MINE]["iron_ore_reserve"] == 0
            assert working.resources[MINE]["iron_ore"] == 0
            assert working.resources[MINE]["pickaxe"] == 1
            assert working.resources[FOREST]["standing_timber"] == 0
            assert working.resources[FOREST]["wood"] == 0
            assert working.resources[FOREST]["axe"] == 1
            assert working.resources[KILN]["charcoal"] == 0
            assert working.resources[MINE]["coin_copper"] == 1
            assert working.resources[MINER]["coin_copper"] == 0
            assert working.resources[FOREST]["coin_copper"] == 2
            assert working.resources[WOODCUTTER]["coin_copper"] == 0
            assert _copper(working) == OPENING_COPPER

            due = gateway.wait(
                60, command_id="wait-for-first-output",
                expected_revision=working.revision,
            )
            mined = db.verify(WORLD)
            assert due.time == 120
            mine_job = _jobs(mined, MINER, MINE_RECIPE)
            wood_job = _jobs(mined, WOODCUTTER, WOOD_RECIPE)
            assert len(mine_job) == len(wood_job) == 1
            assert mine_job[0]["status"] == wood_job[0]["status"] == "completed"
            assert mine_job[0]["output_after"] == wood_job[0]["output_after"] == 1
            assert mine_job[0]["work_wage"]["amount"] == 1
            assert wood_job[0]["work_wage"]["amount"] == 2
            assert mined.resources[MINE]["iron_ore"] == 1
            assert mined.resources[MINE]["iron_ore_reserve"] == 0
            assert mined.resources[MINE]["pickaxe"] == 1
            assert mined.resources[FOREST]["standing_timber"] == 0
            assert mined.resources[FOREST]["axe"] == 1
            assert mined.resources[MINE]["coin_copper"] == 0
            assert mined.resources[MINER]["coin_copper"] == 1
            assert mined.resources[FOREST]["coin_copper"] == 1
            assert mined.resources[BURNER]["coin_copper"] == 0
            assert mined.resources[WOODCUTTER]["coin_copper"] == 2
            assert _copper(mined) == OPENING_COPPER
            wood_trades = [trade for trade in mined.market_trades.values()
                           if trade["buyer_id"] == BURNER
                           and trade["resource"] == "wood"]
            assert len(wood_trades) == 1
            wood_trade = wood_trades[0]
            assert (wood_trade["seller_id"], wood_trade["resource"],
                    wood_trade["quantity"], wood_trade["payment_resource"],
                    wood_trade["total_paid"], wood_trade["site_id"]) == (
                WOODCUTTER, "wood", 1, "coin_copper", 1, FOREST,
            )
            assert wood_trade["goods_source_before"] == 1
            assert wood_trade["goods_source_after"] == 0
            assert wood_trade["goods_target_before"] == 0
            assert wood_trade["goods_target_after"] == 1

            ore_offer = _local_offer(gateway, "iron_ore")
            assert ore_offer["seller_id"] == MINER
            assert ore_offer["available"] == 1
            assert ore_offer["unit_price"] == 1
            bought_ore = gateway.buy(
                ore_offer["offer_id"], 1, 1,
                command_id="buy-finite-ore",
                expected_revision=mined.revision,
            )
            after_ore = db.verify(WORLD)
            assert bought_ore.status == "purchased"
            assert after_ore.resources[PLAYER]["iron_ore"] == 1
            assert after_ore.resources[PLAYER]["coin_copper"] == 1
            assert after_ore.resources[MINE]["iron_ore"] == 0
            assert after_ore.resources[MINE]["coin_copper"] == 1
            ore_trades = [trade for trade in after_ore.market_trades.values()
                          if trade["buyer_id"] == PLAYER
                          and trade["resource"] == "iron_ore"]
            assert len(ore_trades) == 1
            assert (ore_trades[0]["goods_source_before"],
                    ore_trades[0]["goods_source_after"],
                    ore_trades[0]["goods_target_before"],
                    ore_trades[0]["goods_target_after"]) == (1, 0, 0, 1)
            assert _copper(after_ore) == OPENING_COPPER

            at_forge = _travel(db, gateway, "mine-forge", 30,
                               "carlos-to-forge", FORGE)
            at_kiln = _travel(db, gateway, "forge-kiln", 40,
                              "carlos-to-kiln", KILN)
            # The burner has to travel, buy and carry the wood, then finish
            # its timed, wage-funded charcoal batch from the actual kiln input.
            assert at_kiln.time == 190
            charcoal_ready = gateway.wait(
                410, command_id="wait-for-charcoal",
                expected_revision=at_kiln.revision,
            )
            fueled = db.verify(WORLD)
            assert charcoal_ready.time == 600
            charcoal_jobs = _jobs(fueled, BURNER, CHARCOAL_RECIPE)
            assert len(charcoal_jobs) == 1
            charcoal_job = charcoal_jobs[0]
            assert charcoal_job["status"] == "completed"
            assert charcoal_job["output_after"] == 1
            assert charcoal_job["work_wage"]["amount"] == 1
            assert fueled.resources[FOREST]["wood"] == 0
            assert fueled.resources[BURNER]["wood"] == 0
            assert fueled.resources[KILN]["wood"] == 0
            assert fueled.resources[KILN]["charcoal"] == 1
            assert fueled.resources[BURNER]["coin_copper"] == 1
            assert fueled.resources[KILN]["coin_copper"] == 0
            assert _copper(fueled) == OPENING_COPPER
            burner_travels = [travel for travel in fueled.travels.values()
                              if travel["npc_id"] == BURNER]
            assert len(burner_travels) == 2
            assert all(travel["status"] == "arrived"
                       for travel in burner_travels)
            assert {travel["destination"] for travel in burner_travels} == {
                FOREST, KILN,
            }

            charcoal_offer = _local_offer(gateway, "charcoal")
            assert charcoal_offer["seller_id"] == BURNER
            assert charcoal_offer["available"] == 1
            assert charcoal_offer["unit_price"] == 1
            bought_charcoal = gateway.buy(
                charcoal_offer["offer_id"], 1, 1,
                command_id="buy-finite-charcoal",
                expected_revision=fueled.revision,
            )
            after_charcoal = db.verify(WORLD)
            assert bought_charcoal.status == "purchased"
            assert after_charcoal.resources[PLAYER]["charcoal"] == 1
            assert after_charcoal.resources[PLAYER]["coin_copper"] == 0
            assert after_charcoal.resources[KILN]["charcoal"] == 0
            assert after_charcoal.resources[KILN]["coin_copper"] == 1
            charcoal_trades = [trade for trade in after_charcoal.market_trades.values()
                               if trade["buyer_id"] == PLAYER
                               and trade["resource"] == "charcoal"]
            assert len(charcoal_trades) == 1
            assert (charcoal_trades[0]["goods_source_before"],
                    charcoal_trades[0]["goods_source_after"],
                    charcoal_trades[0]["goods_target_before"],
                    charcoal_trades[0]["goods_target_after"]) == (1, 0, 0, 1)
            assert _copper(after_charcoal) == OPENING_COPPER

            at_forge = _travel(db, gateway, "forge-kiln", 40,
                               "carlos-return-to-forge", FORGE)
            gateway.deposit_material(
                FORGE_RECIPE, "iron_ore", 1,
                command_id="deliver-ore-to-forge",
                expected_revision=at_forge.revision,
            )
            ready = db.verify(WORLD)
            assert ready.resources[PLAYER]["iron_ore"] == 0
            assert ready.resources[FORGE]["iron_ore"] == 1
            gateway.deposit_material(
                FORGE_RECIPE, "charcoal", 1,
                command_id="deliver-charcoal-to-forge",
                expected_revision=ready.revision,
            )
            ready = db.verify(WORLD)
            assert ready.resources[PLAYER]["charcoal"] == 0
            assert ready.resources[FORGE]["iron_ore"] == 1
            assert ready.resources[FORGE]["charcoal"] == 1

            started = gateway.work(
                FORGE_RECIPE, command_id="make-finite-iron-fitting",
                expected_revision=ready.revision,
            )
            running = db.verify(WORLD)
            player_jobs = _jobs(running, PLAYER, FORGE_RECIPE)
            assert len(player_jobs) == 1 and player_jobs[0]["status"] == "running"
            assert (player_jobs[0]["started_at"], player_jobs[0]["due"]) == (
                ready.time, ready.time + 90,
            )
            assert running.resources[FORGE]["iron_fitting"] == 0
            assert running.resources[FORGE]["anvil"] == 1

            finished = gateway.wait(
                90, command_id="finish-finite-iron-fitting",
                expected_revision=started.revision,
            )
            final = db.verify(WORLD)
            job = _jobs(final, PLAYER, FORGE_RECIPE)[0]
            assert finished.time == ready.time + 90
            assert job["status"] == "completed"
            assert job["output_after"] == 1
            assert dict(job["input_after_by_resource"]) == {
                "iron_ore": 0, "charcoal": 0,
            }
            assert job["work_wage"]["amount"] == 1
            assert final.resources[FORGE]["iron_fitting"] == 1
            assert final.resources[FORGE]["iron_ore"] == 0
            assert final.resources[FORGE]["charcoal"] == 0
            assert final.resources[FORGE]["coin_copper"] == 0
            assert final.resources[PLAYER]["coin_copper"] == 1
            assert _copper(final) == OPENING_COPPER
            if full_life:
                hunger = [profile["needs"]["hunger"]
                          for profile in final.npcs.values()]
                assert all(10 <= value < 75 for value in hunger)
                assert any(value > 10 for value in hunger)
                assert not final.consumptions
                assert sum(stock.get("food", 0)
                           for stock in final.resources.values()) == 0

            assert all(job["status"] == "completed" for job in (
                mine_job[0], wood_job[0], charcoal_job, job,
            ))
            assert len(_jobs(final, MINER, MINE_RECIPE)) == 1
            assert len(_jobs(final, WOODCUTTER, WOOD_RECIPE)) == 1
            assert len(_jobs(final, BURNER, CHARCOAL_RECIPE)) == 1
            trades = list(final.market_trades.values())
            assert sorted((trade["buyer_id"], trade["resource"], trade["site_id"])
                          for trade in trades) == sorted((
                (BURNER, "wood", FOREST),
                (PLAYER, "iron_ore", MINE),
                (PLAYER, "charcoal", KILN),
            ))
            assert all(trade["quantity"] == trade["total_paid"] == 1
                       and trade["payment_resource"] == "coin_copper"
                       for trade in trades)

            before_empty_retry = db.verify(WORLD)
            with pytest.raises(InvalidEvent, match="insufficient"):
                NPCProductionService(db, clock).start(
                    WORLD, MINER, MINE_RECIPE, "retry-empty-mine",
                    expected_revision=before_empty_retry.revision,
                )
            assert db.verify(WORLD).to_dict() == before_empty_retry.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == before_empty_retry.to_dict()
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == final.to_dict()
