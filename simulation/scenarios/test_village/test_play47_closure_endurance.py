"""Final PLAY-47 scarcity gates in the real thirteen-resident economy.

No recovery claim: all rain is bounded, all actors decide for themselves,
and the unrecovered control retains its finite food, cash and physical roads.
"""
import json
import shutil

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from carlos_sim.supply_diagnostics import audit_courier
import test_play38_multi_farm_couriers as east
import test_play39_rain_drought_real_day as reference
from test_play47_joined_professions import _engine
from test_play47_two_field_liquidity import _joined_supply_genesis

DAY = reference.DAY
WORLD = east.WORLD


def _seed(path):
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=7,
            initial_water=2, initial_market_food=3, market_wallets=True,
            hungry_market_buyers=True, bootstrap=_joined_supply_genesis,
            cash_return=True, waged_harvest=True, harvest_wage_copper=2,
        )
        state = db.load(WORLD)
        return db.append(WORLD, "closure-policy", state.revision, [
            DomainEvent("WaterSourceConfigured", None, "bounded observed rain", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "existing policy", 0,
                        {"hunger_seconds_per_point": 3600,
                         "activity_hunger_percent": 20}),
        ], bootstrap=True)


def _reading(state):
    audit = audit_npc_economy(state)
    assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
    reading = reference._bound_ledger(
        state, rain_units=state.hydrology_sources["well"]["received_total"],
        people=13,
    )
    reading["wages"] = audit["wage_receipts"]
    return reading


def _day(path, end, *, step=DAY // 4, rain=False):
    with SQLiteEventStore(path) as db:
        state = db.load(WORLD)
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock, shopping=True)
            while state.time < end:
                target = min(state.time + step, end)
                state = engine.advance(
                    WORLD, seconds=target - state.time,
                    command_id=f"closure:{target}",
                    expected_revision=state.revision,
                ).state
                assert state.time == target
                _reading(state)
                # Bound replay work between advances without skipping the
                # independent full-genesis replay after the daily reopen.
                assert db.snapshot(WORLD).to_dict() == state.to_dict()
            if rain:
                state = FiniteWaterService(db, clock).record(
                    WORLD, "well", f"observed-rain-{end}", 2,
                    command_id=f"rain-{end}", expected_revision=state.revision,
                ).state
            assert db.snapshot(WORLD).to_dict() == db.load(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            clock.close_session(WORLD)
    # Verify the FINAL checkpoint too, after the connection has really closed.
    with SQLiteEventStore(path) as reopened:
        assert reopened.verify(WORLD).to_dict() == reopened.load(WORLD).to_dict() == state.to_dict()
    return state


@pytest.mark.parametrize("wet", [False, True])
def test_thirteen_residents_seven_days_and_post_stall_clock_partitions(tmp_path, wet):
    path = tmp_path / "seven-days.sqlite"
    _seed(path)
    readings = []
    for day in range(1, 8):
        # Exactly the established six observed units; no unbounded replenishment.
        state = _day(path, day * DAY, rain=wet and day <= 3)
        readings.append(_reading(state))
        if day == 3:
            partitioned = tmp_path / "partitioned.sqlite"
            # Copy only a closed SQLite database, including its authentic ledger.
            shutil.copyfile(path, partitioned)
        if day == 4:
            split_state = _day(partitioned, 4 * DAY, step=DAY // 8)
            left, right = state.to_dict(), split_state.to_dict()
            # Extra waits change revision only. Compare the entire state at
            # the 96-hour gate, then continue the control to seven days.
            left.pop("revision")
            right.pop("revision")
            assert left == right
    for row in readings[3:]:
        for key in ("matured", "water_used_for_growth", "grain", "baked",
                    "owned_food", "eaten", "market_sales", "courier_deliveries", "wages"):
            assert row[key] == readings[2][key], (wet, key, readings)
    assert readings[-1]["npc_hunger_cap"] == 13
    assert state.resources["market"]["food"] > 0
    assert not any(t["buyer_id"] == east.COURIER for t in state.market_trades.values())
    courier = audit_courier(state, east.COURIER, supply_enabled=True)
    assert "hunger_at_or_above_90" in courier["blocked_reasons"]
    assert state.resources[east.COURIER]["coin_copper"] == 0
    print("PLAY47_SEVEN_DAY_CLOSURE", json.dumps({
        "wet": wet, "readings": readings, "courier": courier,
    }, sort_keys=True))
