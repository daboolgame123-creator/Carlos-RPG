"""Controlled same-source PLAY48 13NPC economy: funded real guard job vs no job.

Both worlds start with the same 13 people, original 12 copper and 3 loaves.
The sole treatment is a disclosed signed finite guard contract with Carlos'
two existing idle coins moved to the real watch employer. No post-genesis
assignments, money or food, no injected market/meal action, no forced choices.
The experiment is not 96h/168h sustainability.
"""
from __future__ import annotations

import json

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from test_play38_multi_farm_couriers import WORLD
from test_play48_peddler_fast import seed as seed_baseline
from test_play48_real_watch_income_24h import seed as seed_watch, engine, HOUR
from test_play48_finite_hunt_fish_roads import conserve_diverse
from test_play48_peddler_24h_diagnostic import measures


def _actual_metrics(state):
    out = measures(state)
    out["hunger_by_person"] = {
        who: state.npcs[who]["needs"]["hunger"] for who in sorted(state.npcs)
    }
    out["meals_by_person"] = {
        who: sum(meal["npc_id"] == who
                 for meal in state.consumptions.values())
        for who in sorted(state.npcs)
    }
    out["adel_market_purchases"] = sum(
        t["buyer_id"] == "adel" and t["resource"] == "food"
        for t in state.market_trades.values()
    )
    out["peddler_sales_to_adel"] = sum(
        t["buyer_id"] == "adel" and t["seller_id"] == "repairman"
        and t["stock_owner_id"] == "repairman" and t["site_id"] == "market"
        for t in state.market_trades.values()
    )
    out["watch_pay"] = sum(
        "work_wage" in j and j["recipe_id"] == "finite-watch-duty"
        for j in state.production_jobs.values()
    )
    out["guard_paid_at"] = [
        j["work_wage"]["paid_at"]
        for j in state.production_jobs.values()
        if j["recipe_id"] == "finite-watch-duty" and "work_wage" in j
    ]
    out["guard_peddler_purchase_at"] = [
        t["executed_at"] for t in state.market_trades.values()
        if t["buyer_id"] == "adel" and t["seller_id"] == "repairman"
        and t["stock_owner_id"] == "repairman" and t["site_id"] == "market"
    ]
    out["guard_meal_times"] = sorted(
        meal["consumed_at"] for meal in state.consumptions.values()
        if meal["npc_id"] == "adel"
    )
    out["cash_nonzero_owners"] = {
        who: amount
        for who, amount in audit_npc_economy(state)[
            "copper_known_by_owner"
        ].items() if amount
    }
    return out


def _simulate(path, *, signed):
    if signed:
        opening = seed_watch(path)
    else:
        opening = seed_baseline(path)
    outputs = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            runner = engine(db, clock)
            for hour in (6, 12, 18, 24):
                previous = db.verify(WORLD)
                state = runner.advance(
                    WORLD, seconds=hour * HOUR - previous.time,
                    expected_revision=previous.revision,
                    command_id=f"controlled-ab:{signed}:{hour}",
                ).state
                assert len(state.npcs) == 13
                assert state.time == hour * HOUR
                assert db.verify(WORLD).to_dict() == state.to_dict()
                assert db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
                conserve_diverse(state)
                cash = audit_npc_economy(state)
                assert cash["copper_scope_complete"]
                assert cash["copper_known_total"] == 12
                outputs.append(_actual_metrics(state))
        finally:
            clock.close_session(WORLD)
    return opening, outputs


def test_physical_13npc_causal_guard_job_funds_genuine_second_meal_without_robbing_couriers(tmp_path):
    cgenesis, control = _simulate(tmp_path / "original.sqlite", signed=False)
    tgenesis, treatment = _simulate(tmp_path / "watch.sqlite", signed=True)
    assert set(cgenesis.npcs) == set(tgenesis.npcs)
    assert sum(b.get("food", 0) for b in cgenesis.resources.values()) == 3
    assert sum(b.get("food", 0) for b in tgenesis.resources.values()) == 3
    assert audit_npc_economy(cgenesis)["copper_known_total"] == 12
    assert audit_npc_economy(tgenesis)["copper_known_total"] == 12
    assert cgenesis.resources["carlos"]["coin_copper"] == 2
    assert tgenesis.resources["carlos"]["coin_copper"] == 0
    assert tgenesis.resources["watch_post"]["coin_copper"] == 2

    print("PLAY48_TRUE_SAME_GENESIS_GUARD_WAGE_TO_MEAL_AB_24H " +
          json.dumps({"control": control, "funded_watch": treatment},
                     sort_keys=True), flush=True)

    before, after = control[-1], treatment[-1]
    assert before["watch_pay"] == 0
    assert after["watch_pay"] == 1
    assert after["adel_market_purchases"] > before["adel_market_purchases"]
    assert after["peddler_sales_to_adel"] >= 1
    assert after["meals_by_person"]["adel"] > before["meals_by_person"]["adel"]
    assert after["hunger100"] < before["hunger100"]
    assert after["courier_deliveries"] == before["courier_deliveries"]
    assert len(after["guard_paid_at"]) == 1
    assert len(after["guard_peddler_purchase_at"]) == 1
    assert after["guard_paid_at"][0] < after["guard_peddler_purchase_at"][0]
    assert any(at >= after["guard_peddler_purchase_at"][0]
               for at in after["guard_meal_times"])
    # Disclosed limits: a single signed watch order and salary cannot
    # finance two weeks of livelihoods and does not refill the well.
    assert after["watch_pay"] == 1
    assert after["well_water"] == 0
