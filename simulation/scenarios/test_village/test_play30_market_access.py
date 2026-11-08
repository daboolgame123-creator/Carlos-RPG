"""PLAY-30B: distinguish real crop production from market purchase access.

All coins are finite and initialized exactly once. The only planned change
between budgeted and unbudgeted scenarios is WHO owns eight existing coins.
No free grants, no automatic wages, and no new food source.
"""
from __future__ import annotations

import pytest

from carlos_sim import SQLiteEventStore
from play_physical_supply import (
    WORLD, PEOPLE, seed_physical_supply, audit_physical_supply,
)
from test_play30_hunger_yield_ab import run_three_day_village

INITIAL_FOOD = 1


@pytest.mark.parametrize("market_wallets", [False, True])
def test_initial_copper_is_12_and_only_wallet_ownership_changes(tmp_path, market_wallets):
    with SQLiteEventStore(tmp_path / "wallet-start.sqlite") as db:
        seed_physical_supply(db, personal_food=INITIAL_FOOD,
                             harvest_yield=3, market_wallets=market_wallets)
        state = db.verify(WORLD)
        assert len(state.npcs) == len(PEOPLE) == 7
        audit = audit_physical_supply(
            state, seed=1, water=2, buyer_copper=2,
            personal_food=INITIAL_FOOD,
        )
        assert audit["copper"] == 12
        rs = state.resources
        assert rs["carlos"]["coin_copper"] == (2 if market_wallets else 10)
        assert rs["adel"]["coin_copper"] == 2
        assert rs["omar"].get("coin_copper", 0) == (4 if market_wallets else 0)
        assert rs["layla"].get("coin_copper", 0) == (4 if market_wallets else 0)
        assert audit["food_equivalent"] == 7
        assert db.verify(WORLD).to_dict() == state.to_dict()


@pytest.mark.parametrize("value", [0, 1, None, "yes", [], {}])
def test_untrusted_wallet_setup_type_is_rejected(tmp_path, value):
    with SQLiteEventStore(tmp_path / "wrong-wallet.sqlite") as db:
        with pytest.raises(ValueError, match="market_wallets"):
            seed_physical_supply(db, market_wallets=value)


def test_72h_full_npc_market_access_counterfactual(tmp_path):
    # Fair controls: 7 autonomous NPCs, identical total copper=12,
    # equal initial food (1 per NPC), identical water/seed/land/time/roles.
    # Scenario A tests production without wages or redistributed cash;
    # B asks whether ownership of eight EXISTING coins changes purchases;
    # C holds wallets constant but increases physical crop yield 1 -> 3.
    without_buying_power = run_three_day_village(
        tmp_path / "one-wallet-three-grain.sqlite", 3,
        personal_provisions=INITIAL_FOOD, market_wallets=False,
    )
    funded_low_yield = run_three_day_village(
        tmp_path / "funded-one-grain.sqlite", 1,
        personal_provisions=INITIAL_FOOD, market_wallets=True,
    )
    funded_high_yield = run_three_day_village(
        tmp_path / "funded-three-grain.sqlite", 3,
        personal_provisions=INITIAL_FOOD, market_wallets=True,
    )
    for world in (without_buying_power, funded_low_yield, funded_high_yield):
        assert world["total_coins"] == 12
        assert world["matured"] == 2
        assert len(world["timeline"]) == 3
        assert world["timeline"][-1]["meals"] >= 7
        assert all(0 <= day["hunger_at_100"] <= 7
                   and 0 <= day["high_risk"] <= 7
                   and day["market_stock"] >= 0
                   for day in world["timeline"])
    assert without_buying_power["wallets"]["omar"] is None
    assert funded_low_yield["wallets"]["omar"] is not None
    assert funded_high_yield["wallets"]["layla"] is not None
    # Do not assume money is enough: a buyer must also be present, hungry,
    # offer visible, and seller available. Print observed outcomes.
    print("PLAY30_MARKET_ACCESS_THREE_WORLD_REAL_72H", {
        "wealth_concentrated_yield3": without_buying_power,
        "wealth_distributed_yield1": funded_low_yield,
        "wealth_distributed_yield3": funded_high_yield,
    })
