"""Fast fail-closed contract tests. They do NOT simulate 168 real hours."""
from dataclasses import replace
from types import SimpleNamespace

from carlos_sim.phase48_acceptance import (
    HOURS, EconomicCheckpoint, IndependentEvidence, checkpoint_from_state,
    evaluate_play48,
)


NAMES = tuple(sorted((
    "adel", "basim", "burner", "farid", "hana", "huda", "layla",
    "miner", "nora", "omar", "repairman", "salma", "smith",
)))
CONFIRMED = IndependentEvidence(True, True, True, True, True)


def point(hour, **updates):
    # Illustrative synthetic counter only: never publish as an actual world.
    row = EconomicCheckpoint(
        hour=hour, resident_ids=NAMES, hunger100=(),
        known_copper=12, copper_scope_complete=True,
        npc_copper=2, site_copper=10, other_copper=0, npc_food=0,
        completed_production=hour * 2, food_trades=hour, consumed_meals=hour,
        paid_work_receipts=hour // 2, paid_food_work_receipts=hour // 3,
        paid_courier_receipts=hour // 4,
        courier_deliveries=(("hana", hour * 2), ("huda", hour)),
    )
    return replace(row, **updates)


def profile():
    base = {h: point(h) for h in HOURS}
    return base, dict(base)


def test_full_synthetic_counter_still_requires_independent_source_evidence():
    baseline, trial = profile()
    result = evaluate_play48(trial, baseline)
    assert result.status == "PLAY48_ECONOMIC_NO_GO"
    assert any("CI_incomplete" in e for e in result.failures)
    # Even when all independently verified flags are supplied by a caller,
    # the function NEVER returns PLAY48_GO or merges code.
    assert evaluate_play48(trial, baseline, evidence=CONFIRMED).status == (
        "METRICS_MET_AWAITING_HUMAN_RELEASE_REVIEW"
    )


def test_original_h72_mass_starvation_and_h168_frozen_economy_cannot_pass():
    old, new = profile()
    starving = ("adel", "burner", "hana", "huda", "miner", "nora", "salma", "smith")
    for h in (72, 96, 120, 144, 168):
        new[h] = replace(new[h], hunger100=starving)
    frozen = new[72]
    for h in (96, 120, 144, 168):
        new[h] = replace(
            new[h], completed_production=frozen.completed_production,
            food_trades=frozen.food_trades,
            paid_work_receipts=frozen.paid_work_receipts,
            paid_food_work_receipts=frozen.paid_food_work_receipts,
            paid_courier_receipts=frozen.paid_courier_receipts,
            courier_deliveries=frozen.courier_deliveries,
        )
    result = evaluate_play48(new, old, evidence=CONFIRMED)
    assert result.status == "PLAY48_ECONOMIC_NO_GO"
    assert "no_real_post72_completed_production" in result.failures
    assert "no_real_post72_food_trades" in result.failures
    assert "no_real_post72_hana_cargo" in result.failures
    assert "no_real_post72_huda_cargo" in result.failures
    assert any(x.startswith("hunger100:168:") for x in result.failures)


def test_salmas_meal_improvement_does_not_hide_hana_loaded_freight_regression():
    control, trial = profile()
    control[72] = replace(control[72], consumed_meals=21,
                          courier_deliveries=(("hana", 47), ("huda", 5)))
    trial[72] = replace(trial[72], consumed_meals=23,
                        courier_deliveries=(("hana", 43), ("huda", 5)),
                        hunger100=("adel", "burner", "hana", "huda",
                                   "miner", "nora", "smith"))
    result = evaluate_play48(trial, control, evidence=CONFIRMED)
    assert "regression_loaded_delivery_hana:72" in result.failures
    assert result.status == "PLAY48_ECONOMIC_NO_GO"


def test_absent_checkpoints_unaccounted_money_and_missing_physical_courier_fail():
    control, trial = profile()
    del trial[120]
    trial[48] = replace(trial[48], copper_scope_complete=False,
                        courier_deliveries=(("hana", 0),))
    result = evaluate_play48(trial, control, evidence=CONFIRMED)
    assert "missing_same_hour_control_candidate=[120]" in result.failures
    assert "candidate:original_12_copper_not_proven:48" in result.failures
    assert "candidate:missing_real_courier:48" in result.failures


def test_diagnostics_take_exact_owners_and_completed_real_receipts_not_site_cash_as_salary():
    residents = {n: {"needs": {"hunger": 100 if n == "salma" else 30}}
                 for n in NAMES}
    resources = {n: {"coin_copper": 0, "food": 0} for n in NAMES}
    resources.update({
        "market": {"coin_copper": 12, "food": 10},
        "well": {"coin_copper": 0},
    })
    state = SimpleNamespace(
        world_id="synthetic-test-only", time=48 * 3600, revision=1,
        entities={n: {} for n in NAMES},
        locations={"market": {}, "well": {}},
        resources=resources, npcs=residents, supply_circuits={
            "hana": {"deliveries": 43}, "huda": {"deliveries": 5}},
        courier_provisions={}, market_trades={"real-sale": {
            "resource": "food", "payment_resource": "coin_copper",
            "buyer_id": "adel", "seller_id": "salma",
            "stock_owner_id": "market", "total_paid": 2}},
        production_jobs={"worked": {
            "status": "completed", "work_wage": {
                "site_id": "market", "worker_id": "farid", "amount": 1}}},
        consumptions={"meal": {"npc_id": "farid"}},
        travels={},
    )
    before = state.resources["market"].copy()
    x = checkpoint_from_state(state)
    assert x.hour == 48 and x.site_copper == 12 and x.npc_copper == 0
    assert x.food_trades == 1 and x.consumed_meals == 1
    assert x.earned_receipts == 1 and x.hunger100 == ("salma",)
    assert x.deliveries("hana") == 43 and x.deliveries("huda") == 5
    assert state.resources["market"] == before


def test_48h_nominal_all_money_in_sites_without_paid_jobs_or_food_rejected():
    base, trial = profile()
    trial[36] = replace(trial[36], earned_receipts=trial[36].earned_receipts) if False else trial[36]
    prior = trial[36]
    trial[48] = replace(
        trial[48], npc_copper=0, site_copper=12, npc_food=0,
        paid_work_receipts=prior.paid_work_receipts,
        paid_food_work_receipts=prior.paid_food_work_receipts,
        paid_courier_receipts=prior.paid_courier_receipts,
    )
    result = evaluate_play48(trial, base, evidence=CONFIRMED)
    assert "48h_no_personal_food_cash_or_new_wage_receipt" in result.failures
