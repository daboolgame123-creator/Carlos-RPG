"""PLAY48Y check original 1-farm/2-market default stays byte-for-byte plausible.

The special two-farm-loaf counterfactual must not change old 13-NPC
market/farm genesis or silently enable special payroll for another world.
"""
from __future__ import annotations

import pytest
from carlos_sim import SQLiteEventStore
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play47_closure_endurance import DAY, WORLD
from test_play47_joined_professions import _joined_bootstrap
from test_play48s_authentic_courier_food_wages import _wood_farm_employed_genesis
import test_play38_multi_farm_couriers as east


def test_historical_farm_one_market_two_default_unchanged(tmp_path):
    path = tmp_path / "unchanged-default.sqlite"
    with SQLiteEventStore(path) as db:
        east.seed_two_field_world(
            db, east_growth_seconds=DAY, east_grain_yield=12,
            initial_water=2, initial_market_food=3,
            market_wallets=True, hungry_market_buyers=True,
            cash_return=True, waged_harvest=True, harvest_wage_copper=2,
            bootstrap=_wood_farm_employed_genesis,
        )
        s = db.verify(WORLD)
        assert len(s.npcs) == 13
        assert (s.schema_version, s.rules_version) == (45, 62)
        assert s.resources["market"]["food"] == 2
        assert s.resources["farm"]["food"] == 1
        assert sum(v.get("food", 0) for v in s.resources.values()) == 3
        assert audit_npc_economy(s)["copper_known_total"] == 12
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


@pytest.mark.parametrize("invalid", (0, 3, True, 2.0, "2", -1))
def test_bad_initial_farm_allocation_rejected_without_world_creation(tmp_path, invalid):
    path = tmp_path / ("bad-" + str(invalid).replace(".", "_") + ".sqlite")
    with SQLiteEventStore(path) as db:
        with pytest.raises(ValueError, match="farm 2-loaf start"):
            _joined_bootstrap(
                db, initial_market_food=3, site_payroll_enabled=True,
                farm_opening_food_wage=True,
                farm_initial_food_loaves=invalid,
            )
        assert db.db.execute("SELECT count(*) FROM worlds").fetchone() == (0,)
        assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_cannot_enable_extra_farm_food_without_real_farm_employer(tmp_path):
    with SQLiteEventStore(tmp_path / "unauthorized.sqlite") as db:
        with pytest.raises(ValueError, match="farm 2-loaf start"):
            _joined_bootstrap(
                db, initial_market_food=3, site_payroll_enabled=True,
                farm_opening_food_wage=False,
                farm_initial_food_loaves=2,
            )
        assert db.db.execute("SELECT count(*) FROM worlds").fetchone() == (0,)
