"""WORLD-01j: player mining plus NPC-produced charcoal in full-life."""
from __future__ import annotations

import json
import pytest

from carlos_sim import (
    DomainEvent, LivingWorldEngine, NPCMarketService, PlayerGateway,
    SQLiteEventStore, TimeEngine,
)
from carlos_sim.domain import RULES_VERSION, SCHEMA_VERSION
from carlos_sim.store import InvalidEvent

WORLD = "world01j-full-life-player-mine-npc-charcoal"
PLAYER = "carlos"
MINE_KEEPER = "mine_steward"
KILN_KEEPER = "charcoal_burner"
WOODCUTTER = "independent_woodcutter"
HOME = "home"
MINE = "iron_mine"
FOREST = "lumberyard"
KILN = "charcoal_kiln"
FORGE = "smithy"
MINE_RECIPE = "carlos-finite-iron-miner"
FORGE_RECIPE = "carlos-iron-fitting"
WOOD_RECIPE = "independent-finite-timber-cutting"
CHARCOAL_RECIPE = "independent-finite-wood-charcoal"


def _event(kind: str, data: dict) -> DomainEvent:
    return DomainEvent(kind, None, "WORLD-01j disposable integration setup", 0, data)


def _seed(store: SQLiteEventStore) -> None:
    store.create_world(WORLD)
    events = [
        *[_event("LocationCreated", {"id": site, "name": site})
          for site in (HOME, MINE, FOREST, KILN, FORGE)],
        *[_event("RouteCreated", {
            "id": route, "a": start, "b": end, "seconds": seconds,
        }) for route, start, end, seconds in (
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
    for npc, site, role in (
        (MINE_KEEPER, MINE, "merchant"),
        (KILN_KEEPER, KILN, "charcoal_burner"),
        (WOODCUTTER, FOREST, "woodcutter"),
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
    # The exact opening copper funds Carlos's purchases, each wage, and the
    # charcoal burner's actual local wood purchase. No charcoal is seeded.
    for owner, stock in (
        (PLAYER, {"coin_copper": 1, "iron_ore": 0, "charcoal": 0}),
        (MINE, {"iron_ore_reserve": 1, "iron_ore": 0,
                "pickaxe": 1, "coin_copper": 2}),
        (KILN, {"wood": 0, "charcoal": 0, "kiln_tool": 1,
                "coin_copper": 1}),
        (FOREST, {"standing_timber": 1, "wood": 0, "axe": 1,
                  "coin_copper": 2}),
        (FORGE, {"iron_ore": 0, "charcoal": 0, "iron_fitting": 0,
                 "anvil": 1, "coin_copper": 1}),
        (MINE_KEEPER, {"coin_copper": 0}),
        (KILN_KEEPER, {"wood": 0, "coin_copper": 1}),
        (WOODCUTTER, {"coin_copper": 0}),
    ):
        for resource, quantity in stock.items():
            events.append(_event("ResourceChanged", {
                "owner_id": owner, "resource": resource,
                "previous": None, "current": quantity,
                "source": "initialization",
            }))

    events.extend((
        _event("MarketStallConfigured", {
            "site_id": MINE, "keeper_id": MINE_KEEPER,
        }),
        _event("MarketStallConfigured", {
            "site_id": KILN, "keeper_id": KILN_KEEPER,
        }),
        _event("MarketStallConfigured", {
            "site_id": FOREST, "keeper_id": WOODCUTTER,
        }),
        _event("NPCRoutineConfigured", {
            "npc_id": WOODCUTTER, "home_id": HOME,
            "workplace_id": FOREST, "work_start": 0, "work_end": 20_000,
        }),
        _event("NPCRoutineConfigured", {
            "npc_id": KILN_KEEPER, "home_id": HOME,
            "workplace_id": KILN, "work_start": 0, "work_end": 20_000,
        }),
        _event("ProductionRecipeConfigured", {
            "id": MINE_RECIPE, "site_id": MINE, "role": "miner",
            "input_resource": "iron_ore_reserve", "input_amount": 1,
            "output_resource": "iron_ore", "output_amount": 1,
            "tool_resource": "pickaxe", "duration_seconds": 120,
            "wage_coin": 1, "player_worker_id": PLAYER,
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
        _event("ProductionRecipeConfigured", {
            "id": WOOD_RECIPE, "site_id": FOREST, "role": "woodcutter",
            "input_resource": "standing_timber", "input_amount": 1,
            "output_resource": "wood", "output_amount": 1,
            "tool_resource": "axe", "duration_seconds": 120,
            "wage_coin": 2,
        }),
        _event("ProductionRecipeConfigured", {
            "id": CHARCOAL_RECIPE, "site_id": KILN,
            "role": "charcoal_burner", "input_resource": "wood",
            "input_amount": 1, "output_resource": "charcoal",
            "output_amount": 1, "tool_resource": "kiln_tool",
            "duration_seconds": 120, "wage_coin": 1,
        }),
    ))
    store.append(WORLD, "world01j:bootstrap", 0, events, bootstrap=True)


def _copper_total(state) -> int:
    return sum(stock.get("coin_copper", 0)
               for stock in state.resources.values())


def _event_rows(store: SQLiteEventStore) -> tuple[tuple, ...]:
    return tuple(store.db.execute(
        "SELECT seq, command_id, payload, hash FROM events "
        "WHERE world_id=? ORDER BY seq", (WORLD,),
    ))


def _npc_jobs(state) -> list[dict]:
    return sorted((job for job in state.production_jobs.values()
                   if job["npc_id"] == WOODCUTTER
                   and job["recipe_id"] == WOOD_RECIPE),
                  key=lambda job: (job["started_at"], job["due"]))


def _charcoal_jobs(state) -> list[dict]:
    return sorted((job for job in state.production_jobs.values()
                   if job["npc_id"] == KILN_KEEPER
                   and job["recipe_id"] == CHARCOAL_RECIPE),
                  key=lambda job: (job["started_at"], job["due"]))


def _full_life_engine(store: SQLiteEventStore, clock: TimeEngine):
    return LivingWorldEngine(
        store, clock, max_events_per_advance=5000,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=False, navigation_enabled=True, routines_enabled=True,
        multi_professional_markets_enabled=True, compound_procurement_enabled=True,
        consumption_enabled=True, survival_enabled=True, supply_enabled=True,
        professional_full_life_enabled=True,
    )


def _travel(db, gateway: PlayerGateway, route: str, seconds: int,
            command: str, destination: str):
    before = db.verify(WORLD)
    departure = gateway.move(
        route, command_id=command + "-depart",
        expected_revision=before.revision,
    )
    assert departure.status == "traveling"
    arrival = gateway.wait(
        seconds, command_id=command + "-arrive",
        expected_revision=departure.revision,
    )
    assert arrival.time == before.time + seconds
    state = db.verify(WORLD)
    assert state.entities[PLAYER]["location_id"] == destination
    return state


def _post_offer(db, clock, seller: str, owner: str, site: str,
                offer_id: str, resource: str):
    result = NPCMarketService(db, clock).post(
        WORLD, seller, owner, site, offer_id, resource, 1,
        "coin_copper", 1, expected_revision=db.verify(WORLD).revision,
    )
    return result.state


def _run_world(database):
    with SQLiteEventStore(database) as db:
        _seed(db)
        opening = db.verify(WORLD)
        assert opening.schema_version == SCHEMA_VERSION == 46
        assert opening.rules_version == RULES_VERSION == 73
        assert opening.entities[PLAYER]["controller"] == "player"
        assert PLAYER not in opening.npcs
        assert opening.production_jobs == {}
        assert opening.market_offers == {}
        assert opening.resources[MINE]["iron_ore_reserve"] == 1
        assert opening.resources[MINE]["iron_ore"] == 0
        assert opening.resources[MINE]["coin_copper"] == 2
        assert opening.resources[KILN]["wood"] == 0
        assert opening.resources[KILN]["charcoal"] == 0
        assert opening.resources[KILN]["kiln_tool"] == 1
        assert opening.resources[FORGE]["iron_ore"] == 0
        assert opening.resources[FORGE]["charcoal"] == 0
        assert opening.resources[FORGE]["iron_fitting"] == 0
        assert opening.resources[FOREST]["standing_timber"] == 1
        assert opening.resources[FOREST]["wood"] == 0
        assert opening.resources[FOREST]["axe"] == 1
        assert opening.resources[FOREST]["coin_copper"] == 2
        assert opening.resources[PLAYER]["coin_copper"] == 1
        assert opening.resources[KILN_KEEPER]["coin_copper"] == 1
        assert _copper_total(opening) == 8

        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            gateway = PlayerGateway(
                db, clock, world_id=WORLD, player_id=PLAYER,
                engine=_full_life_engine(db, clock),
            )
            with pytest.raises(ValueError, match="physically present"):
                gateway.work(
                    MINE_RECIPE, command_id="mine-before-travel",
                    expected_revision=opening.revision,
                )
            assert db.verify(WORLD).to_dict() == opening.to_dict()

            at_mine = _travel(
                db, gateway, "home-mine", 60, "to-mine", MINE,
            )
            assert at_mine.time == 60
            npc_jobs = _npc_jobs(at_mine)
            assert len(npc_jobs) == 1
            npc_job = npc_jobs[0]
            assert npc_job["status"] == "running"
            assert (npc_job["started_at"], npc_job["due"]) == (0, 120)
            assert at_mine.resources[FOREST]["standing_timber"] == 0
            assert at_mine.resources[FOREST]["wood"] == 0
            assert at_mine.resources[FOREST]["coin_copper"] == 2
            assert at_mine.resources[WOODCUTTER]["coin_copper"] == 0
            assert at_mine.resources[KILN_KEEPER]["coin_copper"] == 1
            assert gateway.offers().details["offers"] == ()

            started = gateway.work(
                MINE_RECIPE, command_id="start-mining",
                expected_revision=at_mine.revision,
            )
            mining = db.verify(WORLD)
            mine_job = mining.production_jobs[started.details["job_id"]]
            assert mine_job["status"] == "running"
            assert (mine_job["started_at"], mine_job["due"]) == (60, 180)
            assert mining.resources[MINE]["iron_ore_reserve"] == 0
            assert mining.resources[MINE]["iron_ore"] == 0
            assert mining.resources[MINE]["coin_copper"] == 2
            assert mining.resources[PLAYER]["coin_copper"] == 1
            assert _npc_jobs(mining)[0]["status"] == "running"
            assert _copper_total(mining) == 8

            gateway.wait(
                59, command_id="wait-mining-to-119",
                expected_revision=mining.revision,
            )
            before_npc_due = db.verify(WORLD)
            assert before_npc_due.time == 119
            assert before_npc_due.production_jobs[started.details["job_id"]]["status"] == "running"
            assert _npc_jobs(before_npc_due)[0]["status"] == "running"
            assert before_npc_due.resources[FOREST]["wood"] == 0
            assert before_npc_due.resources[WOODCUTTER]["coin_copper"] == 0
            assert _charcoal_jobs(before_npc_due) == []
            assert before_npc_due.resources[MINE]["iron_ore"] == 0
            assert before_npc_due.resources[PLAYER]["coin_copper"] == 1

            gateway.wait(
                1, command_id="finish-npc-woodcutting",
                expected_revision=before_npc_due.revision,
            )
            npc_completed = db.verify(WORLD)
            npc_job = _npc_jobs(npc_completed)[0]
            assert npc_completed.time == 120
            assert npc_job["status"] == "completed"
            assert npc_job["output_after"] == 1
            assert npc_job["work_wage"]["paid_at"] == 120
            assert npc_job["work_wage"]["amount"] == 2
            assert npc_completed.resources[FOREST]["standing_timber"] == 0
            wood_trades = [trade for trade in npc_completed.market_trades.values()
                           if trade["buyer_id"] == KILN_KEEPER
                           and trade["resource"] == "wood"]
            assert len(wood_trades) == 1
            wood_trade = wood_trades[0]
            assert (wood_trade["seller_id"], wood_trade["stock_owner_id"],
                    wood_trade["resource"], wood_trade["quantity"],
                    wood_trade["payment_resource"], wood_trade["total_paid"],
                    wood_trade["site_id"]) == (
                WOODCUTTER, FOREST, "wood", 1, "coin_copper", 1, FOREST,
            )
            assert (wood_trade["goods_source_before"],
                    wood_trade["goods_source_after"],
                    wood_trade["goods_target_before"],
                    wood_trade["goods_target_after"]) == (1, 0, 0, 1)
            assert npc_completed.resources[FOREST]["wood"] == 0
            assert npc_completed.resources[WOODCUTTER]["coin_copper"] == 2
            assert npc_completed.resources[KILN_KEEPER]["coin_copper"] == 0
            assert npc_completed.production_jobs[started.details["job_id"]]["status"] == "running"
            assert npc_completed.resources[MINE]["iron_ore"] == 0
            assert npc_completed.resources[PLAYER]["coin_copper"] == 1
            assert _copper_total(npc_completed) == 8

            start_events = [json.loads(row[2]) for row in _event_rows(db)]
            start_events = [event for event in start_events
                            if event["event_type"] == "ProductionStarted"]
            npc_job_id = next(
                job_id for job_id, job in npc_completed.production_jobs.items()
                if job["npc_id"] == WOODCUTTER
                and job["recipe_id"] == WOOD_RECIPE
            )
            npc_start = next(event for event in start_events
                             if event["data"]["id"] == npc_job_id)
            assert (npc_start["actor_id"], npc_start["time"]) == (WOODCUTTER, 0)
            assert npc_start["cause"].startswith("autonomous production:")
            player_start = next(
                event for event in start_events
                if event["data"]["id"] == started.details["job_id"]
            )
            assert (player_start["actor_id"], player_start["cause"],
                    player_start["time"]) == (
                PLAYER, "player explicitly started contracted local production", 60,
            )

            gateway.wait(
                59, command_id="wait-mining-to-179",
                expected_revision=npc_completed.revision,
            )
            almost_mined = db.verify(WORLD)
            assert almost_mined.time == 179
            assert almost_mined.production_jobs[started.details["job_id"]]["status"] == "running"
            assert almost_mined.resources[MINE]["iron_ore"] == 0
            assert almost_mined.resources[PLAYER]["coin_copper"] == 1

            gateway.wait(
                1, command_id="finish-mining",
                expected_revision=almost_mined.revision,
            )
            mined = db.verify(WORLD)
            mine_job = mined.production_jobs[started.details["job_id"]]
            assert mined.time == 180
            assert mine_job["status"] == "completed"
            assert mine_job["output_after"] == 1
            assert mine_job["work_wage"]["paid_at"] == 180
            assert mine_job["work_wage"]["amount"] == 1
            assert mined.resources[MINE]["iron_ore"] == 1
            assert mined.resources[PLAYER]["coin_copper"] == 2
            assert mined.resources[MINE]["coin_copper"] == 1
            assert _copper_total(mined) == 8

            before_empty_retry = db.verify(WORLD)
            before_retry_events = _event_rows(db)
            with pytest.raises(InvalidEvent, match="insufficient or unknown"):
                gateway.work(
                    MINE_RECIPE, command_id="mine-empty-reserve-retry",
                    expected_revision=before_empty_retry.revision,
                )
            assert db.verify(WORLD).to_dict() == before_empty_retry.to_dict()
            assert _event_rows(db) == before_retry_events

            ore_posted = _post_offer(
                db, clock, MINE_KEEPER, MINE, MINE,
                "world01j-player-mined-ore", "iron_ore",
            )
            ore_quote = gateway.offers().details["offers"]
            assert ore_quote == ({
                "offer_id": "world01j-player-mined-ore",
                "seller_id": MINE_KEEPER, "resource": "iron_ore",
                "available": 1, "payment_resource": "coin_copper",
                "unit_price": 1,
            },)
            bought_ore = gateway.buy(
                "world01j-player-mined-ore", 1, 1,
                command_id="buy-mined-ore",
                expected_revision=ore_posted.revision,
            )
            after_ore = db.verify(WORLD)
            ore_trade = after_ore.market_trades[bought_ore.details["trade_id"]]
            assert ore_trade["buyer_id"] == PLAYER
            assert ore_trade["seller_id"] == MINE_KEEPER
            assert ore_trade["stock_owner_id"] == MINE
            assert (ore_trade["resource"], ore_trade["quantity"],
                    ore_trade["total_paid"]) == ("iron_ore", 1, 1)
            assert after_ore.resources[MINE]["iron_ore"] == 0
            assert after_ore.resources[PLAYER]["iron_ore"] == 1
            assert after_ore.resources[PLAYER]["coin_copper"] == 1
            assert after_ore.resources[MINE]["coin_copper"] == 2
            assert _copper_total(after_ore) == 8

            with pytest.raises(ValueError, match="contracted worksite"):
                gateway.deposit_material(
                    FORGE_RECIPE, "iron_ore", 1,
                    command_id="ore-deposit-at-mine",
                    expected_revision=after_ore.revision,
                )
            assert db.verify(WORLD).to_dict() == after_ore.to_dict()

            at_forge = _travel(
                db, gateway, "mine-forge", 30, "to-forge", FORGE,
            )
            assert at_forge.time == 210
            at_kiln = _travel(
                db, gateway, "forge-kiln", 40, "to-kiln", KILN,
            )
            assert at_kiln.time == 250
            assert at_kiln.resources[PLAYER]["iron_ore"] == 1
            charcoal_ready = gateway.wait(
                350, command_id="wait-for-npc-produced-charcoal",
                expected_revision=at_kiln.revision,
            )
            fueled = db.verify(WORLD)
            assert charcoal_ready.time == 600
            charcoal_jobs = _charcoal_jobs(fueled)
            assert len(charcoal_jobs) == 1
            charcoal_job = charcoal_jobs[0]
            assert charcoal_job["status"] == "completed"
            assert charcoal_job["output_after"] == 1
            assert charcoal_job["work_wage"]["amount"] == 1
            assert charcoal_job["work_wage"]["paid_at"] == charcoal_job["due"]
            assert fueled.resources[FOREST]["wood"] == 0
            assert fueled.resources[KILN_KEEPER]["wood"] == 0
            assert fueled.resources[KILN]["wood"] == 0
            assert fueled.resources[KILN]["charcoal"] == 1
            assert fueled.resources[KILN_KEEPER]["coin_copper"] == 1
            assert fueled.resources[KILN]["coin_copper"] == 0
            assert _copper_total(fueled) == 8
            burner_travels = [travel for travel in fueled.travels.values()
                              if travel["npc_id"] == KILN_KEEPER]
            assert len(burner_travels) == 2
            assert all(travel["status"] == "arrived"
                       for travel in burner_travels)
            assert {travel["destination"] for travel in burner_travels} == {
                FOREST, KILN,
            }

            charcoal_quotes = [
                offer for offer in gateway.offers().details["offers"]
                if offer["resource"] == "charcoal"
            ]
            assert len(charcoal_quotes) == 1, charcoal_quotes
            charcoal_quote = charcoal_quotes[0]
            assert (charcoal_quote["seller_id"],
                    charcoal_quote["resource"], charcoal_quote["available"],
                    charcoal_quote["payment_resource"],
                    charcoal_quote["unit_price"]) == (
                KILN_KEEPER, "charcoal", 1, "coin_copper", 1,
            )
            charcoal_offer_id = charcoal_quote["offer_id"]
            charcoal_purchase = gateway.buy(
                charcoal_offer_id, 1, 1,
                command_id="buy-npc-produced-charcoal",
                expected_revision=fueled.revision,
            )
            bought_inputs = db.verify(WORLD)
            charcoal_trade = bought_inputs.market_trades[
                charcoal_purchase.details["trade_id"]
            ]
            assert charcoal_trade["buyer_id"] == PLAYER
            assert charcoal_trade["seller_id"] == KILN_KEEPER
            assert charcoal_trade["stock_owner_id"] == KILN
            assert (charcoal_trade["resource"], charcoal_trade["quantity"],
                    charcoal_trade["total_paid"]) == ("charcoal", 1, 1)
            assert bought_inputs.resources[PLAYER]["iron_ore"] == 1
            assert bought_inputs.resources[PLAYER]["charcoal"] == 1
            assert bought_inputs.resources[KILN]["charcoal"] == 0
            assert bought_inputs.resources[PLAYER]["coin_copper"] == 0
            assert _copper_total(bought_inputs) == 8

            trip = gateway.move(
                "forge-kiln", command_id="return-to-forge-depart",
                expected_revision=bought_inputs.revision,
            )
            assert trip.status == "traveling"
            in_transit = db.verify(WORLD)
            with pytest.raises(ValueError, match="while travelling"):
                # Custody cannot be deposited until the physical arrival event.
                gateway.deposit_material(
                    FORGE_RECIPE, "iron_ore", 1,
                    command_id="ore-deposit-in-transit",
                    expected_revision=trip.revision,
                )
            assert db.verify(WORLD).to_dict() == in_transit.to_dict()
            assert in_transit.entities[PLAYER]["location_id"] == KILN
            assert in_transit.resources[PLAYER]["iron_ore"] == 1
            gateway.wait(
                40, command_id="arrive-at-forge",
                expected_revision=in_transit.revision,
            )
            at_forge = db.verify(WORLD)
            assert at_forge.entities[PLAYER]["location_id"] == FORGE

            gateway.deposit_material(
                FORGE_RECIPE, "iron_ore", 1,
                command_id="deliver-mined-ore",
                expected_revision=at_forge.revision,
            )
            ore_at_forge = db.verify(WORLD)
            assert ore_at_forge.resources[PLAYER]["iron_ore"] == 0
            assert ore_at_forge.resources[FORGE]["iron_ore"] == 1
            with pytest.raises(InvalidEvent, match="insufficient or unknown"):
                gateway.work(
                    FORGE_RECIPE, command_id="forge-without-charcoal",
                    expected_revision=ore_at_forge.revision,
                )
            assert db.verify(WORLD).to_dict() == ore_at_forge.to_dict()
            gateway.deposit_material(
                FORGE_RECIPE, "charcoal", 1,
                command_id="deliver-declared-charcoal",
                expected_revision=ore_at_forge.revision,
            )
            ready = db.verify(WORLD)
            assert ready.resources[FORGE]["iron_ore"] == 1
            assert ready.resources[FORGE]["charcoal"] == 1
            assert ready.resources[PLAYER]["charcoal"] == 0

            forge_start = gateway.work(
                FORGE_RECIPE, command_id="forge-mined-ore-fitting",
                expected_revision=ready.revision,
            )
            running = db.verify(WORLD)
            forge_job_id = forge_start.details["job_id"]
            forge_job = running.production_jobs[forge_job_id]
            assert forge_job["status"] == "running"
            assert (forge_job["started_at"], forge_job["due"]) == (640, 730)
            assert running.resources[FORGE]["iron_ore"] == 0
            assert running.resources[FORGE]["charcoal"] == 0
            assert running.resources[FORGE]["anvil"] == 1
            assert running.resources[FORGE]["iron_fitting"] == 0
            assert running.resources[FORGE]["coin_copper"] == 1
            assert running.resources[PLAYER]["coin_copper"] == 0

            gateway.wait(
                89, command_id="wait-forge-to-729",
                expected_revision=running.revision,
            )
            almost_forged = db.verify(WORLD)
            assert almost_forged.time == 729
            assert almost_forged.production_jobs[forge_job_id]["status"] == "running"
            assert almost_forged.resources[FORGE]["iron_fitting"] == 0
            assert almost_forged.resources[FORGE]["coin_copper"] == 1
            assert almost_forged.resources[PLAYER]["coin_copper"] == 0

            gateway.wait(
                1, command_id="complete-forge-job",
                expected_revision=almost_forged.revision,
            )
            finished = db.verify(WORLD)
            forge_job = finished.production_jobs[forge_job_id]
            assert finished.time == 730
            assert forge_job["status"] == "completed"
            assert forge_job["output_after"] == 1
            assert forge_job["work_wage"]["paid_at"] == 730
            assert forge_job["work_wage"]["amount"] == 1
            assert finished.resources[FORGE]["iron_fitting"] == 1
            assert finished.resources[FORGE]["anvil"] == 1
            assert finished.resources[FORGE]["coin_copper"] == 0
            assert finished.resources[PLAYER]["coin_copper"] == 1
            assert finished.resources[PLAYER]["iron_ore"] == 0
            assert finished.resources[PLAYER]["charcoal"] == 0
            assert finished.resources[MINE]["coin_copper"] == 2
            assert finished.resources[FOREST]["standing_timber"] == 0
            assert finished.resources[FOREST]["wood"] == 0
            assert finished.resources[WOODCUTTER]["coin_copper"] == 2
            assert finished.resources[KILN]["wood"] == 0
            assert finished.resources[KILN]["charcoal"] == 0
            assert finished.resources[KILN]["coin_copper"] == 1
            assert finished.resources[KILN_KEEPER]["coin_copper"] == 1
            assert _copper_total(finished) == 8
            assert len(_npc_jobs(finished)) == 1
            assert len(_charcoal_jobs(finished)) == 1
            assert sum(1 for job in finished.production_jobs.values()
                       if job["npc_id"] == PLAYER
                       and job["recipe_id"] == MINE_RECIPE) == 1
            assert sum(1 for job in finished.production_jobs.values()
                       if job["npc_id"] == PLAYER
                       and job["recipe_id"] == FORGE_RECIPE) == 1
            trades = list(finished.market_trades.values())
            assert sorted((trade["buyer_id"], trade["resource"],
                           trade["site_id"]) for trade in trades) == sorted((
                (KILN_KEEPER, "wood", FOREST),
                (PLAYER, "iron_ore", MINE),
                (PLAYER, "charcoal", KILN),
            ))
            assert all(trade["quantity"] == trade["total_paid"] == 1
                       and trade["payment_resource"] == "coin_copper"
                       for trade in trades)

            rows = _event_rows(db)
            started_events = [json.loads(row[2]) for row in rows]
            started_events = [event for event in started_events
                              if event["event_type"] == "ProductionStarted"]
            jobs_by_id = {job_id: job
                          for job_id, job in finished.production_jobs.items()}
            start_by_job = {
                event["data"]["id"]: event for event in started_events
            }
            wood_job_id = next(
                job_id for job_id, job in jobs_by_id.items()
                if job["npc_id"] == WOODCUTTER
                and job["recipe_id"] == WOOD_RECIPE
            )
            charcoal_job_id = next(
                job_id for job_id, job in jobs_by_id.items()
                if job["npc_id"] == KILN_KEEPER
                and job["recipe_id"] == CHARCOAL_RECIPE
            )
            for job_id, actor, expected_time in (
                (wood_job_id, WOODCUTTER, 0),
                (charcoal_job_id, KILN_KEEPER,
                 jobs_by_id[charcoal_job_id]["started_at"]),
            ):
                event = start_by_job[job_id]
                assert (event["actor_id"], event["time"]) == (
                    actor, expected_time,
                )
                assert event["cause"].startswith("autonomous production:")
            for recipe, expected_time in ((MINE_RECIPE, 60),
                                          (FORGE_RECIPE, 640)):
                player_job_id = next(
                    job_id for job_id, job in jobs_by_id.items()
                    if job["npc_id"] == PLAYER
                    and job["recipe_id"] == recipe
                )
                event = start_by_job[player_job_id]
                assert (event["actor_id"], event["time"], event["cause"]) == (
                    PLAYER, expected_time,
                    "player explicitly started contracted local production",
                )
            assert PLAYER not in finished.npcs
            assert db.load(WORLD).to_dict() == finished.to_dict()

            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == finished.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            state_data = finished.to_dict()
        finally:
            clock.close_session(WORLD)

    with SQLiteEventStore(database) as reopened:
        assert reopened.verify(WORLD).to_dict() == state_data
        assert reopened.load(WORLD).to_dict() == state_data
        assert reopened.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    return state_data, rows


def test_full_life_player_mining_uses_npc_produced_charcoal_and_replays(tmp_path):
    first_state, first_events = _run_world(
        tmp_path / "world01j-first.sqlite",
    )
    repeated_state, repeated_events = _run_world(
        tmp_path / "world01j-repeat.sqlite",
    )
    assert repeated_state == first_state
    assert repeated_events == first_events
