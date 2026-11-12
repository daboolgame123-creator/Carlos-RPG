"""PLAY-48H3: same-funded-escrow A/B, earlier physical market wage timing.

Same thirteen NPCs, same actual original market stock, same signed obligations,
same input rain and copper. The ONLY policy difference is WHEN an employer
hands out an already owned loaf upon completed courier service at the market.
The engine is allowed to keep failing after 72h. Neither CI pass nor a ration
count proves economic recovery.
"""
from __future__ import annotations

import json
import shutil

from carlos_sim import LivingWorldEngine, SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play47_closure_endurance import _seed, WORLD, DAY
from test_play48h1_funded_courier_provision import _sign
from test_play48_13npc_post72_relay import _stats
import test_play39_rain_drought_real_day as ref


def _original_engine(db, clock, *, early: bool,
                     hungry_woodcutter_work_enabled=False,
                     retry_known_supplier_enabled=False,
                     market_sourced_wage_refill_enabled=False,
                     farm_sourced_wage_refill_enabled=False,
                     remember_unbought_stalls_enabled=False):
    return LivingWorldEngine(
        db, clock, max_events_per_advance=5000,
        decision_cooldown=3600,
        economic_enabled=True, agriculture_enabled=True,
        economy_only_enabled=False,
        navigation_enabled=True, routines_enabled=True,
        consumption_enabled=True, survival_enabled=True,
        multi_professional_markets_enabled=True,
        compound_procurement_enabled=True,
        supply_enabled=True,
        shopping_routes_enabled=True,
        professional_full_life_enabled=True,
        early_courier_food_wage_enabled=early,
        market_sourced_wage_refill_enabled=market_sourced_wage_refill_enabled,
        farm_sourced_wage_refill_enabled=farm_sourced_wage_refill_enabled,
        remember_unbought_stalls_enabled=remember_unbought_stalls_enabled,
        hungry_woodcutter_work_enabled=hungry_woodcutter_work_enabled,
        retry_known_supplier_enabled=retry_known_supplier_enabled,
    )


def _conserve(state):
    assert len(state.npcs) == 13
    cash = audit_npc_economy(state)
    assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
    escrow = sum(c["remaining"] for c in state.courier_provisions.values())
    stock = state.resources
    food = sum(b.get("food", 0) for b in stock.values()) + escrow
    grain = sum(b.get("grain", 0) for b in stock.values())
    consumed = sum(m["quantity"] for m in state.consumptions.values())
    pending_bakes = sum(
        state.production_recipes[j["recipe_id"]]["input_amount"]
        for j in state.production_jobs.values()
        if j["status"] == "running"
        and state.production_recipes[j["recipe_id"]]["output_resource"] == "food"
    )
    # Read each frozen, authenticated physical harvest recipe, never a
    # hardcoded fixture yield: the 3/7 historic worlds and the isolated
    # fertile-field 3/12 experiment must use their OWN true grain ledgers.
    # Reading is forensic only and cannot alter a running crop or actor.
    yields = {}
    for site_id in sorted(state.farm_plots):
        candidates = [
            rec["output_amount"] for rec in state.production_recipes.values()
            if rec["site_id"] == site_id
            and rec.get("input_resource") == "crop_ready"
            and rec["output_resource"] == "grain"
        ]
        assert len(candidates) == 1 and candidates[0] > 0
        yields[site_id] = candidates[0]
    assert set(yields) == set(ref.CROP_YIELD)
    pending_harvest = sum(
        yields[j["site_id"]]
        for j in state.production_jobs.values()
        if j["status"] == "running"
        and state.production_recipes[j["recipe_id"]].get("input_resource") == "crop_ready"
    )
    ripe = sum(stock[f]["crop_ready"] * yields[f] for f in yields)
    grown = sum(plot["matured"] * yields[f]
                for f, plot in state.farm_plots.items())
    assert food + grain + consumed + pending_bakes + pending_harvest + ripe == (
        ref.START_FOOD + grown
    )
    water = sum(stock[who]["water"] for who in
                ("well", "farm", "farm_east", "huda", "hana")
                if who in stock and "water" in stock[who])
    used = sum(p["started"] for p in state.farm_plots.values())
    assert water + used == ref.START_WATER + state.hydrology_sources["well"]["received_total"]
    return escrow


def _run(path, end, *, early: bool,
         hungry_woodcutter_work_enabled=False,
         retry_known_supplier_enabled=False,
         market_sourced_wage_refill_enabled=False,
         farm_sourced_wage_refill_enabled=False,
         remember_unbought_stalls_enabled=False):
    day_summaries = []
    with SQLiteEventStore(path) as db:
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        state = db.verify(WORLD)
        engine = _original_engine(
            db, clock, early=early,
            hungry_woodcutter_work_enabled=hungry_woodcutter_work_enabled,
            retry_known_supplier_enabled=retry_known_supplier_enabled,
            market_sourced_wage_refill_enabled=market_sourced_wage_refill_enabled,
            farm_sourced_wage_refill_enabled=farm_sourced_wage_refill_enabled,
            remember_unbought_stalls_enabled=remember_unbought_stalls_enabled,
        )
        try:
            for t in range(DAY // 4, end + 1, DAY // 4):
                # Six-hour simulation slices, original deterministic NPC autonomy.
                if t <= state.time:
                    continue
                state = engine.advance(
                    WORLD, seconds=t-state.time,
                    command_id=f"h3:comparison:{t}",
                    expected_revision=state.revision,
                ).state
                assert state.time == t
                if t % DAY == 0 and t // DAY <= 3:
                    state = FiniteWaterService(db, clock).record(
                        WORLD, "well", f"observed-rain-{t}", 2,
                        command_id=f"rain-{t}", expected_revision=state.revision,
                    ).state
                _conserve(state)
                if t % DAY == 0:
                    day_summaries.append({
                        "day": t // DAY, "economy": _stats(state),
                        "escrow": sum(c["remaining"]
                                      for c in state.courier_provisions.values()),
                        "earned_food_wages": sum(len(c["payments"])
                                                  for c in state.courier_provisions.values()),
                    })
            assert db.snapshot(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
            rows = [json.loads(row[0]) for row in db.db.execute(
                "SELECT payload FROM events WHERE world_id=? ORDER BY seq", (WORLD,)
            )]
            for n, event in enumerate(rows):
                if event["event_type"] != "CourierProvisionPaid":
                    continue
                earlier = [
                    e for e in rows[:n]
                    if e["event_type"] == "SupplyCargoDelivered"
                    and e["data"]["courier_id"] == event["data"]["courier_id"]
                    and e["time"] <= event["time"]
                ]
                assert len(earlier) >= 1
                assert event["data"]["service_deliveries"] <= len(earlier)
                assert event["data"]["courier_id"] in state.supply_circuits
        finally:
            clock.close_session(WORLD)
        assert db.verify(WORLD).to_dict() == state.to_dict()
    with SQLiteEventStore(path) as db:
        assert db.verify(WORLD).to_dict() == state.to_dict()
    return state, day_summaries


def _pair(tmp_path):
    standard = tmp_path / "normal-food-delivery-only-pay.sqlite"
    early = tmp_path / "completed-services-before-food-market-pay.sqlite"
    _seed(standard)
    shutil.copyfile(standard, early)
    with SQLiteEventStore(standard) as db:
        orig = _sign(db)
        assert orig.resources["market"]["food"] == 1
        assert _conserve(orig) == 2
    with SQLiteEventStore(early) as db:
        orig = _sign(db)
        assert orig.resources["market"]["food"] == 1
        assert _conserve(orig) == 2
    return standard, early


def _result(a, b):
    plain, ah = a
    treatment, bh = b
    first = _stats(plain)
    improved = _stats(treatment)
    delta = {key: improved[key]-first[key]
             for key in ("jobs","trades","wages","meals","food_sales")}
    h1 = sum(len(c["payments"]) for c in plain.courier_provisions.values())
    h3 = sum(len(c["payments"]) for c in treatment.courier_provisions.values())
    return {
        "standard": first, "early": improved,
        "wages_paid_h1": h1, "wages_paid_h3": h3,
        "actual_real_economic_differences": delta,
        "h1_day_by_day": ah, "h3_day_by_day": bh,
        "new_food_created": False, "new_coin_created": False,
        "labor_not_forged": True,
        "persistent_recovery_claimed": False,
    }


def test_h3_13_npc_early_service_wages_first_twelve_hours(tmp_path):
    standard, early = _pair(tmp_path)
    a = _run(standard, DAY // 2, early=False)
    b = _run(early, DAY // 2, early=True)
    outcome = _result(a, b)
    assert b[0].time == a[0].time == DAY // 2
    assert outcome["wages_paid_h3"] >= outcome["wages_paid_h1"]
    print("PLAY48H3_EARLY_REAL_A_B", json.dumps(outcome, sort_keys=True))


def test_h3_13_npc_two_matching_contracts_genuine_96h_counterfactual(tmp_path):
    standard, early = _pair(tmp_path)
    a = _run(standard, 4*DAY, early=False)
    b = _run(early, 4*DAY, early=True)
    outcome = _result(a, b)
    assert b[0].time == a[0].time == 4*DAY
    assert b[0].resources["market"]["food"] >= 0
    assert sum(len(c["payments"]) for c in b[0].courier_provisions.values()) <= 2
    # The result is measured, not manufactured by asserting a happy economy.
    assert all(outcome["early"]["deliveries"][who] >= 0
               for who in ("huda","hana"))
    print("PLAY48H3_GENUINE_96H_A_B", json.dumps(outcome, sort_keys=True))


def test_h3_early_payment_cannot_be_claimed_without_real_same_command_service(tmp_path):
    import pytest
    from carlos_sim import DomainEvent
    from carlos_sim.store import InvalidEvent

    path = tmp_path / "forged-early-wage.sqlite"
    _seed(path)
    with SQLiteEventStore(path) as db:
        opening = _sign(db, workers=("huda",), units=1)
        frozen = db.verify(WORLD).to_dict()
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            claim = DomainEvent(
                "CourierProvisionPaid", None, "forged early wage without service", 0,
                {"id": "food-wage-huda", "courier_id": "huda",
                 "service_deliveries": 1, "proof": "prior_market_service"},
            )
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "h3:forged-no-delivery",
                          opening.revision, [claim], supply_authorized=True)
            assert db.verify(WORLD).to_dict() == frozen

            fake_delivery = DomainEvent(
                "SupplyCargoDelivered", "huda", "pretend unloaded nonexistent food", 0,
                {"courier_id": "huda", "resource": "food"},
            )
            with pytest.raises((InvalidEvent, ValueError)):
                db.append(WORLD, "h3:forged-with-untrue-cargo",
                          opening.revision, [fake_delivery, claim], supply_authorized=True)
            assert db.verify(WORLD).to_dict() == frozen
        finally:
            clock.close_session(WORLD)
