"""Isolated finite hydrology counterfactuals: NOT an integrated world claim."""
import pytest

from prototypes.hydrology_pure import (
    Well, audit_water, recorded_rain, local_load,
    local_delivery, consume_for_crop,
)


def setup():
    return Well(site="well", capacity=3, initial=2, balance=2)


def test_drought_cannot_replenish_during_any_number_of_idle_days():
    base = setup()
    for tick in (86400, 172800, 259200):
        assert base.balance == 2
        assert not base.observations
        assert audit_water(base, farm_water=0, cargo_water=0, water_used=0)["recorded_rain"] == 0
    assert base == setup()


def test_observed_rain_is_finite_reproducible_and_capacity_checked():
    base = setup()
    rainy = recorded_rain(base, observation_id="measurement-001",
                          units=1, logical_time=86400)
    assert rainy.balance == 3
    assert rainy.received_total == 1
    assert base.balance == 2
    assert audit_water(rainy, farm_water=0, cargo_water=0, water_used=0)["recorded_rain"] == 1
    assert rainy == recorded_rain(base, observation_id="measurement-001",
                                 units=1, logical_time=86400)
    with pytest.raises(ValueError, match="capacity"):
        recorded_rain(rainy, observation_id="measurement-002",
                      units=1, logical_time=86401)


@pytest.mark.parametrize("bad", [0, -1, True, False, 1.5, "1", None])
def test_nonpositive_noninteger_and_boolean_rain_fail_without_state_change(bad):
    base = setup()
    with pytest.raises(ValueError):
        recorded_rain(base, observation_id="bad-input",
                      units=bad, logical_time=1)
    assert base.balance == 2


@pytest.mark.parametrize("bad", ["", "a" * 65, "bad space", "☂", None, 4])
def test_invalid_observation_names_cannot_enter_ledger(bad):
    with pytest.raises(ValueError):
        recorded_rain(setup(), observation_id=bad, units=1, logical_time=2)


def test_replayed_measurement_and_time_reversal_are_rejected():
    base = Well(site="well", capacity=2, initial=0, balance=0)
    one = recorded_rain(base, observation_id="r1", units=1, logical_time=100)
    with pytest.raises(ValueError, match="repeated"):
        recorded_rain(one, observation_id="r1", units=1, logical_time=101)
    with pytest.raises(ValueError, match="previous time"):
        recorded_rain(one, observation_id="r2", units=1, logical_time=99)
    assert one.balance == 1 and one.received_total == 1


def test_route_is_physical_and_water_can_reach_real_crop_once():
    well = setup()
    before = audit_water(well, farm_water=0, cargo_water=0, water_used=0)
    with pytest.raises(ValueError, match="courier present"):
        local_load(well, courier_location="market", cargo_water=0)
    well, cargo = local_load(well, courier_location="well", cargo_water=0)
    assert audit_water(well, farm_water=0, cargo_water=cargo, water_used=0)["courier"] == 1
    with pytest.raises(ValueError, match="real farm"):
        local_delivery(courier_location="well", farm_site="farm",
                       cargo_water=cargo, farm_water=0)
    farm, cargo = local_delivery(courier_location="farm", farm_site="farm",
                                 cargo_water=cargo, farm_water=0)
    assert cargo == 0 and farm == 1
    farm, crop = consume_for_crop(farm, water_used=0)
    after = audit_water(well, farm_water=farm, cargo_water=cargo, water_used=crop)
    assert before["initial"] == after["initial"]
    assert crop == 1 and well.balance == 1


def test_dry_vs_rainy_three_days_with_no_hidden_replenishment():
    results = []
    for rain in (False, True):
        well = Well(site="well", capacity=2, initial=1, balance=1)
        farm, cargo, crop = 0, 0, 0
        for day in (1, 2, 3):
            if day == 2 and rain:
                well = recorded_rain(well, observation_id="day2-gauge",
                                     units=1, logical_time=day * 86400)
            if well.balance:
                well, cargo = local_load(well, courier_location="well",
                                         cargo_water=cargo)
                farm, cargo = local_delivery(courier_location="farm",
                                             farm_site="farm",
                                             cargo_water=cargo, farm_water=farm)
                farm, crop = consume_for_crop(farm, water_used=crop)
            audit_water(well, farm_water=farm, cargo_water=cargo, water_used=crop)
        results.append((crop, well.received_total))
    assert results == [(1, 0), (2, 1)]


@pytest.mark.parametrize("loc,cargo", [("market", 0), ("well", 1),
                                        ("well", True), ("well", -1)])
def test_remote_double_or_invalid_cargo_fails(loc, cargo):
    base = setup()
    with pytest.raises(ValueError):
        local_load(base, courier_location=loc, cargo_water=cargo)


def test_audit_rejects_missing_doubled_and_fabricated_water():
    w = setup()
    for n in (1, 3, -1, True):
        with pytest.raises(ValueError):
            audit_water(w, farm_water=n, cargo_water=0, water_used=0)
    assert audit_water(w, farm_water=0, cargo_water=0, water_used=0)["well"] == 2


def test_invalid_well_and_fake_provenance_rejected():
    with pytest.raises(ValueError):
        Well(site="well", capacity=1, initial=2, balance=0)
    with pytest.raises(ValueError):
        Well(site="well", capacity=3, initial=2, balance=2,
             received_total=1, observations=())
    with pytest.raises(ValueError):
        Well(site="well", capacity=3, initial=2, balance=2,
             received_total=1,
             observations=(("dup", 1, 7), ("dup", 1, 8)))
