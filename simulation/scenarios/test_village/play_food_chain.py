"""PLAY-23: one real finite grain -> owned food -> NPC meal (test-only).

The bakery job and market decision are explicitly coordinated test commands.
Only the *eating* and subsequent village life are chosen autonomously by NPCs.
The 90-second production preparation is driven by trusted TimeEngine, not by
the seven-NPC living planner; do not present that interval as autonomous life.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from carlos_sim import DomainEvent, NPCMarketService, NPCProductionService
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import DuplicateCommand, InvalidEvent, RevisionConflict

from living_player_fixture import (
    WORLD, PLAYER, PEOPLE, living_player_gateway,
    setup_living_npc_ecology_world,
)

# The original living ecology has 2 owned + 6 natural food. The extra test
# material is exactly 1 raw grain that can become exactly 1 food.
INITIAL_FOOD_EQUIVALENT = 9
INITIAL_COPPER = 12  # Carlos 10 + Adel 2; no wages or external deposits.
RECIPE_ID = "chain-grain-meal"
OFFER_ID = "chain-square-food"


def _bootstrap(kind: str, payload: dict) -> DomainEvent:
    return DomainEvent(kind, None, "trusted PLAY-23 disposable food-chain setup",
                       0, payload)


def setup_living_food_chain_world(store, *, grain: int = 1,
                                  buyer_copper: int = 2) -> None:
    """Add a separate, persisted opt-in recipe/ownership setup to PLAY-21.

    Valid zero grain or buyer copper is useful for negative tests, never food
    created by runtime. All other PLAY-21 and earlier saves remain untouched.
    """
    if type(grain) is not int or grain not in (0, 1):
        raise ValueError("demo grain must be exactly 0 or 1")
    if type(buyer_copper) is not int or not 0 <= buyer_copper <= 2:
        raise ValueError("demo buyer copper must be an integer from 0 to 2")
    setup_living_npc_ecology_world(store)
    events = [
        *(_bootstrap("ResourceChanged", {
            "owner_id": owner, "resource": resource, "previous": None,
            "current": amount, "source": "initialization",
        }) for owner, resource, amount in (
            ("square", "grain", grain),
            ("square", "oven", 1),
            ("square", "food", 0),
            ("square", "coin_copper", 0),
            ("adel", "coin_copper", buyer_copper),
        )),
        _bootstrap("ProductionRecipeConfigured", {
            "id": RECIPE_ID, "site_id": "square", "role": "baker",
            "input_resource": "grain", "input_amount": 1,
            "output_resource": "food", "output_amount": 1,
            "tool_resource": "oven", "duration_seconds": 90,
        }),
        _bootstrap("MarketStallConfigured", {
            "site_id": "square", "keeper_id": "salma",
        }),
    ]
    store.append(WORLD, "living-chain-recipe-stall", store.load(WORLD).revision,
                 events, bootstrap=True)


def _revision(session) -> int:
    return session.store.load(WORLD).revision


def _command(session, ident: str, method, *args):
    return method(*args, command_id=ident, expected_revision=_revision(session))


def _must_reject(db, expected: type[Exception], label: str, attempt) -> str:
    before = db.load(WORLD).to_dict()
    count = db.db.execute(
        "SELECT COUNT(*) FROM commands WHERE world_id=?", (WORLD,)
    ).fetchone()[0]
    try:
        attempt()
    except expected as err:
        assert db.load(WORLD).to_dict() == before, (
            f"{label}: rejected command changed world state")
        assert db.db.execute(
            "SELECT COUNT(*) FROM commands WHERE world_id=?", (WORLD,)
        ).fetchone()[0] == count
        return type(err).__name__
    raise AssertionError(f"{label}: invalid operation unexpectedly accepted")


def _resources(state, *, seeded_grain: int = 1, seeded_copper: int = 2) -> dict[str, int]:
    stock = state.resources
    npc_food = sum(stock[who]["food"] for who, *_ in PEOPLE)
    meals = sum(row["quantity"] for row in state.consumptions.values())
    wild = sum(stock[site]["wild_food"] for site in ("square", "woods", "bakery"))
    raw_grain = stock["square"]["grain"]
    site_food = stock["square"]["food"]
    player_food = stock[PLAYER]["food"]
    assert all(type(n) is int and n >= 0 for n in (
        npc_food, meals, wild, raw_grain, site_food, player_food))
    assert npc_food + meals + wild + raw_grain + site_food + player_food == (
        8 + seeded_grain), "physical food+grain must not appear from nowhere"
    assert stock["square"]["oven"] == 1
    assert stock["salma"]["bread"] == 3  # Separate prior market stock unchanged.
    assert stock[PLAYER]["bread"] == 0
    coins = (stock[PLAYER]["coin_copper"] + stock["adel"]["coin_copper"]
             + stock["square"]["coin_copper"] + stock["salma"]["coin_copper"])
    assert coins == 10 + seeded_copper, "currency can only move between owners"
    return {
        "wild_food": wild, "npc_food_owned": npc_food,
        "npc_food_eaten": meals, "player_food": player_food,
        "unprocessed_grain": raw_grain, "site_produced_food": site_food,
        "copper_total": coins,
    }


def run_food_chain(path: str | Path, choice: str = "sell",
                   *, horizon_seconds: int = 360) -> dict[str, Any]:
    """One baker produces, an explicit trade may occur, NPC eats autonomously.

    Compare worlds that start with identical food, copper, seven independent
    NPCs, and production. The only divergent input is the scripted trade.
    """
    if choice not in ("sell", "hold"):
        raise ValueError("food-chain choice must be sell or hold")
    if type(horizon_seconds) is not int or not 91 <= horizon_seconds <= 1200:
        raise ValueError("food-chain horizon must be 91..1200 logical seconds")

    with ResumableTestSession.create(
        path, WORLD, PLAYER, setup_living_food_chain_world,
        disposable_test=True,
    ) as session:
        db, clock = session.store, session.clock
        bakery = NPCProductionService(db, clock)
        market = NPCMarketService(db, clock)
        before = db.load(WORLD)
        assert before.time == 0 and len(before.npcs) == len(PEOPLE) == 7
        assert _resources(before)["site_produced_food"] == 0
        rejects = {}

        rejects["wrong_profession"] = _must_reject(
            db, InvalidEvent, "wrong profession",
            lambda: bakery.start(WORLD, "adel", RECIPE_ID, "forged-worker",
                                expected_revision=_revision(session)))
        made = bakery.start(WORLD, "basim", RECIPE_ID, "grain-batch-1",
                            expected_revision=_revision(session))
        assert made.due == 90
        assert made.state.resources["square"]["grain"] == 0
        assert made.state.resources["square"]["food"] == 0
        rejects["double_work"] = _must_reject(
            db, InvalidEvent, "baker already occupied",
            lambda: bakery.start(WORLD, "basim", RECIPE_ID, "grain-batch-2",
                                expected_revision=_revision(session)))
        rejects["premature_sale"] = _must_reject(
            db, InvalidEvent, "product not ready",
            lambda: market.post(WORLD, "salma", "square", "square",
                                "premature-food", "food", 1, "coin_copper", 2,
                                expected_revision=_revision(session)))
        clock.advance(WORLD, seconds=89, command_id="chain-bake-89",
                      expected_revision=_revision(session))
        assert db.load(WORLD).time == 89
        assert db.load(WORLD).resources["square"]["food"] == 0
        clock.advance(WORLD, seconds=1, command_id="chain-bake-90",
                      expected_revision=_revision(session))
        finished = db.load(WORLD)
        assert finished.time == 90
        assert finished.resources["square"]["food"] == 1
        assert finished.production_jobs["grain-batch-1"]["status"] == "completed"
        assert finished.resources["square"]["oven"] == 1
        assert db.verify(WORLD).to_dict() == finished.to_dict()

        market.post(WORLD, "salma", "square", "square", OFFER_ID, "food",
                    1, "coin_copper", 2, expected_revision=_revision(session))
        rejects["remote_buyer"] = _must_reject(
            db, InvalidEvent, "Nora cannot buy from bakery",
            lambda: market.buy(WORLD, "nora", "remote-food", OFFER_ID, 1, 2,
                               expected_revision=_revision(session)))
        rejects["wrong_price"] = _must_reject(
            db, InvalidEvent, "buyer changes quote",
            lambda: market.buy(WORLD, "adel", "cheap-food", OFFER_ID, 1, 1,
                               expected_revision=_revision(session)))
        before_sale = db.load(WORLD)
        assert before_sale.resources["adel"]["food"] == 0
        assert before_sale.resources["square"]["food"] == 1
        assert len(before_sale.consumptions) == 0
        if choice == "sell":
            sold = market.buy(WORLD, "adel", "adel-buys-food", OFFER_ID, 1, 2,
                              expected_revision=_revision(session)).state
            assert sold.resources["square"]["food"] == 0
            assert sold.resources["adel"]["food"] == 1
            assert sold.resources["square"]["coin_copper"] == 2
            assert sold.resources["adel"]["coin_copper"] == 0
            assert sold.npcs["adel"]["needs"]["hunger"] == 80
            assert sold.market_trades["adel-buys-food"]["total_paid"] == 2
            assert sold.market_trades["adel-buys-food"]["stock_owner_id"] == "square"
            rejects["double_sale"] = _must_reject(
                db, InvalidEvent, "finished quote",
                lambda: market.buy(WORLD, "adel", "adel-double-buy",
                                   OFFER_ID, 1, 2,
                                   expected_revision=_revision(session)))
        else:
            held = db.load(WORLD)
            assert held.resources["square"]["food"] == 1
            assert held.resources["adel"]["food"] == 0
            assert held.market_trades == {}
        _resources(db.load(WORLD))

        # TEST boundary: only after the physical production and explicit market
        # transaction do the independent NPC living-world ticks begin.
        session.bind_gateway(living_player_gateway(
            db, clock, npc_survival_demo=True, npc_ecology_demo=True))
        assert _command(session, "chain-autonomous-first-tick",
                        session.gateway.wait, 1).time == 91
        first = db.load(WORLD)
        adel_meals = [m for m in first.consumptions.values()
                      if m["npc_id"] == "adel"]
        assert len(adel_meals) == (1 if choice == "sell" else 0)
        if choice == "sell":
            assert first.resources["adel"]["food"] == 0
            assert adel_meals[0]["quantity"] == 1
            assert adel_meals[0]["food_before"] == 1
            assert adel_meals[0]["food_after"] == 0
            assert first.npcs["adel"]["needs"]["hunger"] < 80
        else:
            assert first.resources["square"]["food"] == 1
            assert first.npcs["adel"]["needs"]["hunger"] == 80
        assert first.time == 91
        _resources(first)
        first_tick = {
            "adel_meals": len(adel_meals),
            "site_food": first.resources["square"]["food"],
            "adel_food": first.resources["adel"]["food"],
            "adel_hunger": first.npcs["adel"]["needs"]["hunger"],
            "total_npc_meals": len(first.consumptions),
        }
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()

        waits = 0
        while db.load(WORLD).time < horizon_seconds:
            current = db.load(WORLD)
            advance = min(120, horizon_seconds - current.time)
            assert _command(
                session, f"chain-autonomous-{choice}-{waits}",
                session.gateway.wait, advance).time == current.time + advance
            _resources(db.load(WORLD))
            waits += 1
            if waits % 2 == 0:
                db.snapshot(WORLD)

        final = db.verify(WORLD)
        assert final.time == horizon_seconds
        assert len(final.npcs) == 7
        assert len(final.production_jobs) == 1
        assert len(final.market_trades) == (1 if choice == "sell" else 0)
        assert final.resources["square"]["oven"] == 1
        final_balances = _resources(final)
        public = session.handoff()
        assert public["canonical_story"] is False and public["time"] == horizon_seconds
        published = json.dumps(public, ensure_ascii=False)
        for private in ('"npcs"', '"beliefs"', '"goals"', '"needs"',
                        '"production_jobs"', '"market_trades"', '"consumptions"',
                        '"survival_progress"', '"obligations"', '"foraging_attempts"',
                        '"site_produced_food"', '"adel_hunger"'):
            assert private not in published
        db.snapshot(WORLD)
        assert db.verify(WORLD).to_dict() == final.to_dict()
        private_audit = {
            "first_autonomous_tick": first_tick,
            "npc_count_not_mortality": len(final.npcs),
            "npc_meals": len(final.consumptions),
            "npc_trips": len(final.travels),
            "npc_foraging_successes": sum(x["quantity"] for x in
                                          final.foraging_attempts.values()),
            "production_jobs": len(final.production_jobs),
            "market_transactions": len(final.market_trades),
            "end_balances": final_balances,
            "refusals_without_mutation": rejects,
            "living_wait_commands": waits + 1,
            "production_scripted_not_autonomous": True,
            "trade_scripted_not_autonomous": True,
        }
        final_dict = final.to_dict()

    with ResumableTestSession.resume(
        path, WORLD, PLAYER, disposable_test=True,
    ) as session:
        session.bind_gateway(living_player_gateway(
            session.store, session.clock,
            npc_survival_demo=True, npc_ecology_demo=True))
        db, g = session.store, session.gateway
        assert db.verify(WORLD).to_dict() == final_dict
        assert session.handoff() == public
        rejects["duplicate_wait"] = _must_reject(
            db, DuplicateCommand, "same first tick cannot repeat",
            lambda: g.wait(1, command_id="chain-autonomous-first-tick",
                           expected_revision=_revision(session)))
        rejects["stale_revision"] = _must_reject(
            db, RevisionConflict, "stale world cannot advance",
            lambda: g.wait(1, command_id="chain-stale",
                           expected_revision=_revision(session) - 1))
        assert _command(session, "chain-explicit-resume", g.wait, 10).time == (
            horizon_seconds + 10)
        _resources(db.verify(WORLD))

    return {
        "format": "carlos-play23-food-chain-test-v1",
        "canonical_story": False, "disposable_test": True, "choice": choice,
        "player_visible": {"handoff_at_horizon": public, "time": horizon_seconds},
        "test_audit_only": private_audit,
        "restart": {
            "verified_full_replay": True, "handoff_stable": True,
            "duplicate_and_stale_rejected": True,
            "explicit_resumed_time": horizon_seconds + 10,
        },
    }


def main() -> None:
    print("CARLOS — PLAY-23 test-only grain-to-NPC-meal chain")
    with TemporaryDirectory(prefix="carlos-play23-") as folder:
        trials = {
            choice: run_food_chain(Path(folder) / (choice + ".sqlite"), choice)
            for choice in ("sell", "hold")
        }
    for name, result in trials.items():
        audit = result["test_audit_only"]
        first = audit["first_autonomous_tick"]
        print(
            f"{name}: t=360, production=1, trades={audit['market_transactions']}, "
            f"Adel meals at t=91={first['adel_meals']}, "
            f"total NPC meals={audit['npc_meals']}, "
            f"site food remaining={audit['end_balances']['site_produced_food']}"
        )
    print("PLAY23_JSON=" + json.dumps(trials, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
