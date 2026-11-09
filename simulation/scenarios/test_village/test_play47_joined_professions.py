"""PLAY-47: one shared world with food needs and autonomous smith→repairer.

This is a temporary finite test world, not sustained medieval self-sufficiency.
NPCs decide; no script manually moves, buys, deposits, starts, or pays for them.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from play_physical_supply import PEOPLE, WORLD, seed_physical_supply


def _e(kind, data):
    return DomainEvent(kind, None, "trusted combined world only at t=0", 0, data)


def _joined_bootstrap(db):
    """Build the *entire* eleven-NPC world in one trusted genesis event batch.

    No second bootstrap may reinterpret a known wallet or silently mint money.
    """
    def extend(events):
        # Redistribute four of the twelve existing opening copper coins BEFORE
        # the one and only authoritative genesis is committed.
        adjusted = set()
        for idx, event in enumerate(events):
            if (event.event_type == "ResourceChanged"
                    and event.data["resource"] == "coin_copper"
                    and event.data["owner_id"] in ("omar", "layla")):
                assert event.data["previous"] is None
                assert event.data["current"] == 4
                updated = dict(event.data)
                updated["current"] = 2
                events[idx] = _e("ResourceChanged", updated)
                adjusted.add(updated["owner_id"])
        assert adjusted == {"omar", "layla"}

        sites = ("smithy", "iron_mine", "charcoal_kiln", "repair_shop")
        staff = (
            ("smith", "blacksmith", "smithy"),
            ("miner", "miner", "iron_mine"),
            ("burner", "charcoal_burner", "charcoal_kiln"),
            ("repairman", "repairer", "repair_shop"),
        )
        events.extend(_e("LocationCreated", {"id": site, "name": site})
                      for site in sites)
        for rid, a, b, duration in (
            ("bakery-smithy", "bakery", "smithy", 60),
            ("smith-mine", "smithy", "iron_mine", 30),
            ("smith-kiln", "smithy", "charcoal_kiln", 40),
            ("smith-repair", "smithy", "repair_shop", 50),
        ):
            events.append(_e("RouteCreated", {
                "id": rid, "a": a, "b": b, "seconds": duration,
            }))
        for name, role, site in staff:
            events.extend((
                _e("EntityCreated", {
                    "id": name, "name": name.title(),
                    "location_id": site, "controller": "npc",
                }),
                _e("NPCConfigured", {
                    "npc_id": name, "role": role,
                    "needs": {"hunger": 10, "fatigue": 0, "safety": 0},
                    "goals": {"earn": 10, "explore": 10, "survive": 30},
                }),
            ))

        resources = {
            "smithy": {"iron_ore": 0, "charcoal": 0, "anvil": 1,
                       "iron_fitting": 0},
            "iron_mine": {"iron_ore": 1},
            "charcoal_kiln": {"charcoal": 1},
            "repair_shop": {"iron_fitting": 0, "repaired_gear": 0,
                            "wrench": 1},
            "smith": {"iron_ore": 0, "charcoal": 0, "food": 0,
                      "coin_copper": 2},
            "repairman": {"iron_fitting": 0, "food": 0, "coin_copper": 2},
            "miner": {"food": 0},
            "burner": {"food": 0},
        }
        for owner, owned in resources.items():
            for resource, amount in owned.items():
                events.append(_e("ResourceChanged", {
                    "owner_id": owner, "resource": resource,
                    "previous": None, "current": amount,
                    "source": "initialization",
                }))

        existing_wallets = {
            event.data["owner_id"] for event in events
            if event.event_type == "ResourceChanged"
            and event.data["resource"] == "coin_copper"
        }
        all_owners = (
            {who for who, *_ in PEOPLE}
            | {"carlos", "well", "farm", "bakery", "market", "home"}
            | set(sites) | {who for who, _, _ in staff}
        )
        for owner in sorted(all_owners - existing_wallets):
            events.append(_e("ResourceChanged", {
                "owner_id": owner, "resource": "coin_copper",
                "previous": None, "current": 0, "source": "initialization",
            }))

        for owner, home, workplace, start in (
            ("smith", "iron_mine", "smithy", 0),
            ("miner", "bakery", "iron_mine", 0),
            ("burner", "bakery", "charcoal_kiln", 0),
            ("repairman", "charcoal_kiln", "repair_shop", 250),
        ):
            events.append(_e("NPCRoutineConfigured", {
                "npc_id": owner, "home_id": home,
                "workplace_id": workplace,
                "work_start": start, "work_end": 20_000,
            }))
        for site, keeper in (
            ("iron_mine", "miner"),
            ("charcoal_kiln", "burner"),
            ("smithy", "smith"),
        ):
            events.append(_e("MarketStallConfigured", {
                "site_id": site, "keeper_id": keeper,
            }))
        events.extend((
            _e("ProductionRecipeConfigured", {
                "id": "iron-plus-fuel", "site_id": "smithy",
                "role": "blacksmith",
                "inputs": [
                    {"resource": "iron_ore", "amount": 1},
                    {"resource": "charcoal", "amount": 1},
                ],
                "output_resource": "iron_fitting",
                "output_amount": 1,
                "tool_resource": "anvil", "duration_seconds": 90,
                "wage_coin": 1,
            }),
            _e("ProductionRecipeConfigured", {
                "id": "repair-tools", "site_id": "repair_shop",
                "role": "repairer", "input_resource": "iron_fitting",
                "input_amount": 1,
                "output_resource": "repaired_gear", "output_amount": 1,
                "tool_resource": "wrench", "duration_seconds": 90,
            }),
        ))

    seed_physical_supply(
        db, water=2, harvest_yield=3,
        market_wallets=True, hungry_market_buyers=True,
        initial_market_food=3, trusted_genesis_hook=extend,
    )
    state = db.load(WORLD)
    audit = audit_npc_economy(state)
    assert len(state.npcs) == 11
    assert state.resources["omar"]["coin_copper"] == 2
    assert state.resources["layla"]["coin_copper"] == 2
    assert audit["copper_scope_complete"] is True
    assert audit["copper_known_total"] == 12
    assert db.verify(WORLD).to_dict() == state.to_dict()
    return state


def _engine(db, clock, full_life=True):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=5000,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=not full_life,
        navigation_enabled=True, routines_enabled=True,
        consumption_enabled=full_life, survival_enabled=full_life,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        professional_full_life_enabled=full_life,
    )


@pytest.mark.parametrize("bad", [None, 0, 1, [], {}, "yes"])
def test_full_life_flag_rejects_non_boolean(bad, tmp_path):
    with SQLiteEventStore(tmp_path / "reject-flags.sqlite") as db:
        with pytest.raises(ValueError, match="professional_full_life_enabled"):
            LivingWorldEngine(db, TimeEngine(db),
                              professional_full_life_enabled=bad)


def test_full_life_flag_rejects_incompatible_modes(tmp_path):
    with SQLiteEventStore(tmp_path / "no-modes.sqlite") as db:
        with pytest.raises(ValueError, match="professional_full_life_enabled"):
            LivingWorldEngine(db, TimeEngine(db),
                              professional_full_life_enabled=True)


def test_joined_full_life_npcs_really_trade_smelt_and_get_hungry(tmp_path):
    with SQLiteEventStore(tmp_path / "joined-food-and-smith.sqlite") as db:
        start = _joined_bootstrap(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            result = engine.advance(
                WORLD, seconds=900,
                command_id="play47:joined:900",
                expected_revision=start.revision,
            )
            state = result.state
            assert state.time == 900
            trades = {(t["buyer_id"], t["resource"])
                      for t in state.market_trades.values()}
            # Genuine autonomous multi-input smith procurement alongside food.
            assert ("smith", "iron_ore") in trades
            assert ("smith", "charcoal") in trades
            assert any(t["resource"] == "food"
                       for t in state.market_trades.values())
            completed = [j for j in state.production_jobs.values()
                         if j["status"] == "completed"]
            assert any(j["recipe_id"] == "iron-plus-fuel" for j in completed)
            assert state.npcs["basim"]["needs"]["hunger"] > 0
            audit = audit_npc_economy(state)
            assert audit["copper_scope_complete"] is True
            assert audit["copper_known_total"] == 12
            assert all(value >= 0
                       for stock in state.resources.values()
                       for value in stock.values()
                       if type(value) is int)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY47_JOINED_FULL_LIFE", json.dumps({
                "npcs": len(state.npcs),
                "copper": audit["copper_known_total"],
                "trades": audit["trades_by_resource"],
                "jobs": audit["completed_jobs"],
                "hunger": audit["npc_hunger"],
                "wages": audit["wage_receipts"],
            }, sort_keys=True))
        finally:
            clock.close_session(WORLD)
