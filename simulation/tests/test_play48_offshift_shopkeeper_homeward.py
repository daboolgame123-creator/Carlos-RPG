"""P8: off-duty market steward is no longer forcibly kept behind a stall.

In-world chosen movement still uses the existing known-road/shift/safety gates.
The old merchant behavior is untouched unless the optional rule is active.
"""
import pytest

from carlos_sim.domain import WorldState
from carlos_sim.routines import keeper_must_stay_at_counter
from test_play48_real_watch_income_24h import seed


def sample(tmp_path):
    d = seed(tmp_path / "p8-real-genesis.sqlite").to_dict()
    assert d["market_stalls"]["riverbank"]["keeper_id"] == "layla"
    assert d["npc_routines"]["layla"]["home_id"] == "market"
    assert d["npc_routines"]["layla"]["work_end"] == 20_000
    d["time"] = 18 * 3600
    return d


def test_real_fisher_merchant_off_shift_can_head_home_without_stock_change(tmp_path):
    d = sample(tmp_path)
    before = WorldState(**d).to_dict()
    assert keeper_must_stay_at_counter(WorldState(**d), "layla")
    assert not keeper_must_stay_at_counter(
        WorldState(**d), "layla", offshift_homeward_enabled=True)
    assert WorldState(**d).to_dict() == before


def test_real_fisher_merchant_remains_on_shift_at_counter(tmp_path):
    d = sample(tmp_path)
    d["time"] = 5000
    assert keeper_must_stay_at_counter(
        WorldState(**d), "layla", offshift_homeward_enabled=True)


def test_unconfigured_shift_never_releases_full_time_steward(tmp_path):
    d = sample(tmp_path)
    d["npc_routines"].pop("layla")
    assert keeper_must_stay_at_counter(
        WorldState(**d), "layla", offshift_homeward_enabled=True)


def test_absent_worker_cannot_be_treated_as_onsite_steward(tmp_path):
    d = sample(tmp_path)
    d["entities"]["layla"]["location_id"] = "well"
    assert not keeper_must_stay_at_counter(
        WorldState(**d), "layla", offshift_homeward_enabled=True)


@pytest.mark.parametrize("wrong", [None, "yes", 1, 0, [], {}])
def test_guard_requires_strict_boolean(tmp_path, wrong):
    d = sample(tmp_path)
    with pytest.raises(ValueError, match="offshift steward homeward"):
        keeper_must_stay_at_counter(
            WorldState(**d), "layla", offshift_homeward_enabled=wrong)
