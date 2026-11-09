"""PLAY-47 rain and drought across the joined professions economy."""

import pytest

from carlos_sim import DomainEvent, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
import test_play38_multi_farm_couriers as east
import test_play39_rain_drought_real_day as reference
from test_play47_joined_professions import _engine, _joined_bootstrap

@pytest.mark.parametrize("wet", [False, True])
def test_joined_two_field_food_and_liquidity(tmp_path, wet):
    path = tmp_path / "two-field.sqlite"
    world = east.WORLD
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=reference.DAY, east_grain_yield=7,
            initial_water=2, initial_market_food=3, market_wallets=True,
            hungry_market_buyers=True, bootstrap=_joined_supply_genesis,
        )
        state = db.load(world)
        state = db.append(world, "joined-two-field-policy", state.revision, [
            DomainEvent("WaterSourceConfigured", None, "finite scenario well", 0,
                        {"site_id": "well", "capacity": 8}),
            DomainEvent("MetabolismPolicyConfigured", None, "existing slower policy", 0,
                        {"hunger_seconds_per_point": 3600, "activity_hunger_percent": 20}),
            *(DomainEvent("ResourceChanged", None, "explicit opening zero wallet", 0,
                          {"owner_id": who, "resource": "coin_copper", "previous": None,
                           "current": 0, "source": "initialization"})
              for who in (east.EAST, east.FARMER, east.COURIER)),
        ], bootstrap=True)
    day = reference.DAY
    readings = []
    for end in (day, 2 * day, 3 * day):
        with SQLiteEventStore(path) as db:
            assert db.load(world).to_dict() == state.to_dict()
            clock = TimeEngine(db)
            clock.open_session(world)
            try:
                engine = _engine(db, clock)
                for tick in range(end - 3 * day // 4, end + 1, day // 4):
                    state = engine.advance(world, seconds=tick-state.time,
                                           command_id=f"tick-{tick}",
                                           expected_revision=state.revision).state
                    assert state.time == tick
                    audit = audit_npc_economy(state)
                    assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
                    reference._bound_ledger(
                        state, rain_units=state.hydrology_sources["well"]["received_total"],
                        people=13,
                    )
                if wet and end < 3 * day:
                    state = FiniteWaterService(db, clock).record(
                        world, "well", f"observed-rain-{end}", 2,
                        command_id=f"rain-{end}", expected_revision=state.revision,
                    ).state
                snapshot = db.snapshot(world)
                assert db.verify(world).to_dict() == snapshot.to_dict() == state.to_dict()
                readings.append(reference._bound_ledger(
                    state, rain_units=state.hydrology_sources["well"]["received_total"],
                    people=13,
                ))
            finally:
                clock.close_session(world)
    assert readings[-1]["matured"] == {"farm": 1, east.EAST: 2 if wet else 1}
    assert readings[-1]["rain_units"] == (4 if wet else 0)
    assert readings[-1]["water_used_for_growth"] == (3 if wet else 2)
    assert readings[-1]["baked"] == 7
    assert state.resources["market"]["food"] == 7
    for buyer in ("adel", "layla", "omar"):
        assert state.resources[buyer]["coin_copper"] == 0
    assert sum(trade["resource"] == "food" for trade in state.market_trades.values()) == 3
    assert readings[-1]["npc_hunger_cap"] == 13


def _joined_supply_genesis(db, **options):
    assert options == {
        "water": 2, "seed": 1, "initial_market_food": 3, "harvest_yield": 3,
        "personal_food": 0, "market_wallets": True, "hungry_market_buyers": True,
        "one_hungry_market_buyer": False,
    }
    _joined_bootstrap(db)
