"""PLAY-47: one shared world with food needs and autonomous smith→repairer.

This is a temporary finite test world, not sustained medieval self-sufficiency.
NPCs decide; no script manually moves, buys, deposits, starts, or pays for them.
"""
from __future__ import annotations

import json

import pytest

from carlos_sim import DomainEvent, LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.supply_diagnostics import audit_courier
from play_physical_supply import PEOPLE, WORLD, audit_physical_supply, seed_physical_supply


def _e(kind, data):
    return DomainEvent(kind, None, "trusted combined world only at t=0", 0, data)


def _joined_bootstrap(db, *, smith_hunger=10, water=2):
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
                    "needs": {"hunger": smith_hunger if name == "smith" else 10,
                              "fatigue": 0, "safety": 0},
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
                      "coin_copper": 2, "labor_units": 0,
                      "investigation_attempts": 0},
            "repairman": {"iron_fitting": 0, "food": 0, "coin_copper": 2,
                          "labor_units": 0, "investigation_attempts": 0},
            "miner": {"food": 0, "labor_units": 0,
                      "investigation_attempts": 0},
            "burner": {"food": 0, "labor_units": 0,
                       "investigation_attempts": 0},
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
        db, water=water, harvest_yield=3,
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
        decision_cooldown=3600,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=not full_life,
        navigation_enabled=True, routines_enabled=True,
        consumption_enabled=full_life, survival_enabled=full_life,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        supply_enabled=True,
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
            circuit = state.supply_circuits["huda"]
            assert circuit["loads"] >= 1
            assert circuit["deliveries"] >= 1
            assert state.resources["well"]["water"] < 2
            courier_observed = audit_courier(
                state, "huda", supply_enabled=True,
            )
            assert courier_observed["deliveries"] >= 1
            assert "engine_supply_flag_disabled" not in courier_observed["blocked_reasons"]
            # Independent physical conservation proof for water, seed,
            # grains, bread, owned meals and copper, despite the joined
            # smith's separate material/copper trade activities.
            audit_physical_supply(
                state, seed=1, water=2, buyer_copper=2,
                personal_food=0, initial_market_food=3,
            )
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


def test_urgent_hunger_preempts_professional_ore_shopping(tmp_path):
    """Full-life NPC survival must win over nonessential professional travel."""
    with SQLiteEventStore(tmp_path / "play47-hungry-smith.sqlite") as db:
        initial = _joined_bootstrap(db, smith_hunger=80)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            final = _engine(db, clock).advance(
                WORLD, seconds=180,
                command_id="play47:hungry:180",
                expected_revision=initial.revision,
            ).state
            assert final.time == 180
            assert not any(t["buyer_id"] == "smith"
                           for t in final.market_trades.values())
            assert not any(j["npc_id"] == "smith"
                           for j in final.production_jobs.values())
            assert not any(t["npc_id"] == "smith"
                           for t in final.travels.values())
            assert audit_npc_economy(final)["copper_known_total"] == 12
            assert db.verify(WORLD).to_dict() == final.to_dict()
        finally:
            clock.close_session(WORLD)


def test_joined_world_partitioned_clock_preserves_economic_receipts(tmp_path):
    """Compare actual finite trades and jobs, not command/revision metadata."""
    outcomes = []
    for label, checkpoints in (
        ("one", (900,)),
        ("segmented", (30, 100, 230, 450, 700, 900)),
    ):
        with SQLiteEventStore(tmp_path / f"{label}.sqlite") as db:
            start = _joined_bootstrap(db)
            clock = TimeEngine(db)
            clock.open_session(WORLD)
            try:
                engine = _engine(db, clock)
                current = start
                for point in checkpoints:
                    current = engine.advance(
                        WORLD, seconds=point-current.time,
                        command_id=f"play47:parity:{label}:{point}",
                        expected_revision=current.revision,
                    ).state
                    assert db.verify(WORLD).to_dict() == current.to_dict()
                receipts = sorted((
                    t["buyer_id"], t["resource"], t["site_id"],
                    t["executed_at"], t["total_paid"]
                ) for t in current.market_trades.values())
                jobs = sorted((
                    j["npc_id"], j["recipe_id"], j["started_at"],
                    j["finished_at"], j["status"]
                ) for j in current.production_jobs.values())
                audit = audit_npc_economy(current)
                outcomes.append((
                    receipts, jobs, audit["copper_known_total"],
                    audit["stock_known_by_resource"],
                    audit["npc_hunger"],
                ))
            finally:
                clock.close_session(WORLD)
    assert outcomes[0] == outcomes[1]


def test_joined_eleven_npcs_reach_full_day_without_money_or_material_minting(tmp_path):
    """A bad famine is an observed world outcome, not a reason to add gifts."""
    with SQLiteEventStore(tmp_path / "play47-one-day-joined.sqlite") as db:
        state = _joined_bootstrap(db)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock)
            checkpoints = (900, 21600, 43200, 64800, 86400)
            readings = []
            for target in checkpoints:
                state = engine.advance(
                    WORLD, seconds=target-state.time,
                    command_id=f"play47:day:{target}",
                    expected_revision=state.revision,
                ).state
                audit = audit_npc_economy(state)
                assert audit["copper_scope_complete"]
                assert audit["copper_known_total"] == 12
                assert audit["trades"] >= 6
                assert len(state.npcs) == 11
                assert state.resources["iron_mine"]["iron_ore"] == 0
                assert state.resources["charcoal_kiln"]["charcoal"] == 0
                assert state.resources["repair_shop"]["repaired_gear"] == 1
                assert db.verify(WORLD).to_dict() == state.to_dict()
                readings.append({
                    "hour": target // 3600,
                    "hunger_at_100": sum(h == 100 for h in audit["npc_hunger"].values()),
                    "trades": audit["trades"],
                    "jobs": audit["completed_jobs"],
                    "wages": audit["wage_receipts"],
                    "copper": audit["copper_known_total"],
                })
            db.snapshot(WORLD)
            assert db.verify(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("PLAY47_JOINED_FULL_DAY", json.dumps(readings, sort_keys=True))
        finally:
            clock.close_session(WORLD)


def test_joined_dry_world_courier_does_not_invent_water(tmp_path):
    """An empty actual well is not a reason for a courier to fabricate water."""
    with SQLiteEventStore(tmp_path / "play47-dry-courier.sqlite") as db:
        start = _joined_bootstrap(db, water=0)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            state = _engine(db, clock).advance(
                WORLD, seconds=900,
                command_id="play47:dry-courier:900",
                expected_revision=start.revision,
            ).state
            report = audit_physical_supply(
                state, seed=1, water=0, buyer_copper=2,
                personal_food=0, initial_market_food=3,
            )
            assert report["initial_water"] == 0
            assert state.resources["well"]["water"] == 0
            assert state.resources["farm"]["water"] == 0
            assert state.resources["huda"]["water"] == 0
            assert not any(
                job["recipe_id"] == "finite-harvest"
                for job in state.production_jobs.values()
                if job["status"] == "completed"
            )
            assert audit_npc_economy(state)["copper_known_total"] == 12
            assert db.verify(WORLD).to_dict() == state.to_dict()
        finally:
            clock.close_session(WORLD)
