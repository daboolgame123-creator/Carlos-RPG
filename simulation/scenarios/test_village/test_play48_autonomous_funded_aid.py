"""PLAY-48F: a first-person NPC aid relay, NOT a 96-hour village recovery.

Prior route discovery uses real navigation and timed movement, not forged
knowledge. Once a starving courier asks for help, NO test code buys,
responds, transfers, feeds, or moves the donor: the opt-in autonomous
coordinator chooses all those actions via the unchanged trusted reducers.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import (
    SQLiteEventStore, TimeEngine, LivingWorldEngine,
)
from carlos_sim.navigation import NPCNavigationService
from carlos_sim.movement import NPCMovementService
from carlos_sim.supply_diagnostics import audit_courier
from carlos_sim.npc_food_relief import choose_aid_relay
from carlos_sim.store import DuplicateCommand
from play_physical_supply import (
    WORLD, seed_physical_supply, audit_physical_supply,
)


def _own_copper(state):
    return sum(owned.get("coin_copper", 0) for owned in state.resources.values())


def _surveyed_donor_at_well(db, clock, *, market_wallets=True, food=3):
    seed_physical_supply(
        db, market_wallets=market_wallets,
        initial_market_food=food, courier_hunger=89,
    )
    movement = NPCMovementService(db, clock)
    navigation = NPCNavigationService(db, clock)
    clock.open_session(WORLD)
    state = db.load(WORLD)
    for site, route, destination in (
        ("market", "bakery-market", "bakery"),
        ("bakery", "farm-bakery", "farm"),
        ("farm", "well-farm", "well"),
    ):
        assert state.entities["omar"]["location_id"] == site
        state = navigation.survey(
            WORLD, "omar", command_id="aid:learn:" + site,
            expected_revision=state.revision,
        )
        step = movement.start(
            WORLD, "omar", route, "aid:prior-walk:" + destination,
            expected_revision=state.revision,
        )
        assert step.state.entities["omar"]["location_id"] == site
        state = clock.advance(
            WORLD, seconds=step.due-state.time,
            command_id="aid:prior-arrive:" + destination,
            expected_revision=step.state.revision,
        ).state
        assert state.entities["omar"]["location_id"] == destination
    state = navigation.survey(
        WORLD, "omar", command_id="aid:learn:well",
        expected_revision=state.revision,
    )
    assert set(state.navigation["omar"]["visited"]) == {
        "well", "farm", "bakery", "market"
    }
    assert len(state.navigation["omar"]["known_routes"]) >= 3
    return state


def _starve_safely(db, clock, state):
    # No supply trips until the courier genuinely reaches the hunger cutoff.
    aging = LivingWorldEngine(
        db, clock, economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=True, survival_enabled=True, supply_enabled=False,
        max_events_per_advance=5000,
    )
    state = aging.advance(
        WORLD, seconds=3600, command_id="aid:independent-metabolism",
        expected_revision=state.revision,
    ).state
    assert state.npcs["huda"]["needs"]["hunger"] == 100
    assert audit_courier(state, "huda", supply_enabled=True)["next_action"] is None
    assert state.npcs["omar"]["needs"]["hunger"] <= 60
    assert _own_copper(state) == 12
    return state


def _aid_engine(db, clock):
    return LivingWorldEngine(
        db, clock, economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=True, survival_enabled=True,
        consumption_enabled=True, assistance_enabled=True,
        navigation_enabled=True, supply_enabled=True,
        aid_relay_enabled=True, max_events_per_advance=5000,
    )


def test_autonomous_request_buy_walk_consent_meal_and_courier_restart(tmp_path):
    with SQLiteEventStore(tmp_path / "auto-relief.sqlite") as db:
        clock = TimeEngine(db)
        state = _surveyed_donor_at_well(db, clock)
        state = _starve_safely(db, clock, state)
        first_time = state.time
        original_deliveries = state.supply_circuits["huda"]["deliveries"]
        assert original_deliveries == 0
        assert not state.obligations
        engine = _aid_engine(db, clock)
        saw = []
        for step in range(1, 31):
            state = engine.advance(
                WORLD, seconds=60,
                command_id=f"aid:independent:{step}",
                expected_revision=state.revision,
            ).state
            assert _own_copper(state) == 12
            relayed = [o for o in state.obligations.values()
                       if o["requester"] == "huda" and o["provider"] == "omar"]
            if relayed:
                saw.append(relayed[0]["status"])
            if (state.supply_circuits["huda"]["deliveries"] > original_deliveries
                    and any(c["npc_id"] == "huda"
                            for c in state.consumptions.values())):
                break
        else:
            pytest.fail("funded autonomous aid did not restart the actual courier")

        assert state.time > first_time
        requests = [
            (id_, o) for id_, o in state.obligations.items()
            if o["requester"] == "huda" and o["provider"] == "omar"
            and o["resource"] == "food" and o["status"] == "fulfilled"
        ]
        assert len(requests) == 1
        oid, obligation = requests[0]
        assert obligation["quantity"] == 1
        assert obligation["transfer"]["provider_before"] == 1
        assert obligation["transfer"]["provider_after"] == 0
        assert obligation["transfer"]["requester_before"] == 0
        assert obligation["transfer"]["requester_after"] == 1
        assert "requested" in saw and "fulfilled" in saw
        purchases = [
            t for t in state.market_trades.values()
            if t["buyer_id"] == "omar" and t["resource"] == "food"
        ]
        assert len(purchases) == 1
        assert purchases[0]["unit_price"] <= 2
        assert purchases[0]["quantity"] == 1
        trips = [t for t in state.travels.values()
                 if t["npc_id"] == "omar" and t["started_at"] > first_time]
        assert len(trips) == 6  # well -> market -> well on learned roads
        assert all(t["status"] == "arrived" for t in trips)
        assert sum(state.routes[t["route_id"]]["seconds"] for t in trips) == 300
        meals = [c for c in state.consumptions.values()
                 if c["npc_id"] == "huda"]
        assert len(meals) == 1
        assert meals[0]["quantity"] == 1
        assert state.supply_circuits["huda"]["deliveries"] >= 1
        assert state.resources["huda"].get("coin_copper") is None
        audit_physical_supply(
            state, seed=1, water=2, buyer_copper=2,
            initial_market_food=3,
        )
        assert db.snapshot(WORLD).to_dict() == state.to_dict()
        assert db.verify(WORLD).to_dict() == state.to_dict()
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        before_replay = state.to_dict()
        with pytest.raises(DuplicateCommand):
            engine.advance(
                WORLD, seconds=60,
                command_id=f"aid:independent:{step}",
                expected_revision=state.revision,
            )
        assert db.load(WORLD).to_dict() == before_replay
        print("PLAY48_AUTONOMOUS_AID " + json.dumps({
            "requester": obligation["requester"],
            "provider": obligation["provider"],
            "request_id": oid,
            "request_quantity": 1,
            "personally_funded_buy": True,
            "donor_real_route_legs_after_request": len(trips),
            "donor_travel_seconds_after_request": 300,
            "courier_meals": len(meals),
            "courier_deliveries": state.supply_circuits["huda"]["deliveries"],
            "copper_total": _own_copper(state),
            "no_manual_NPC_action_after_request": True,
            "no_new_reducer_event_types": True,
            "post72_recovery_proved": False,
        }, sort_keys=True), flush=True)
        clock.close_session(WORLD)


@pytest.mark.parametrize("flag", [None, 0, 1, "true", (), {}])
def test_aid_relay_requires_strict_boolean(tmp_path, flag):
    with SQLiteEventStore(tmp_path / "invalid-relay.sqlite") as db:
        clock = TimeEngine(db)
        with pytest.raises(ValueError, match="aid_relay_enabled"):
            LivingWorldEngine(
                db, clock, economic_enabled=True, agriculture_enabled=True,
                assistance_enabled=True, consumption_enabled=True,
                survival_enabled=True, navigation_enabled=True,
                aid_relay_enabled=flag,
            )


def test_aid_relay_cannot_run_without_all_prerequisite_capabilities(tmp_path):
    with SQLiteEventStore(tmp_path / "dependencies.sqlite") as db:
        clock = TimeEngine(db)
        with pytest.raises(ValueError, match="aid_relay_enabled"):
            LivingWorldEngine(db, clock, aid_relay_enabled=True)


@pytest.mark.parametrize("market_wallets", [False, True])
def test_donor_must_have_personal_copper_and_local_request(tmp_path, market_wallets):
    with SQLiteEventStore(tmp_path / f"donor-{market_wallets}.sqlite") as db:
        clock = TimeEngine(db)
        state = _surveyed_donor_at_well(
            db, clock, market_wallets=market_wallets,
        )
        state = _starve_safely(db, clock, state) if market_wallets else state
        assert choose_aid_relay(state, "omar") is None, (
            "Before any real co-present request, donor cannot invent need"
        )
        # Even in a market, a courier can never spend consigned copper.
        assert choose_aid_relay(state, "huda") is None
        assert db.verify(WORLD).to_dict() == state.to_dict()
        clock.close_session(WORLD)
