"""PLAY-48H1 GENUINE 13-NPC 0->96h economic A/B, no fake positive gate.

Both worlds have identical real PLAY-47 genesis and initial total food/coins.
Treatment reserves (does not mint) two of the original three market loaves at
time zero. No direct NPC commands after the trusted original setup.
"""
from __future__ import annotations

import json
import hashlib
import shutil

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.hydrology import FiniteWaterService
from test_play47_closure_endurance import _seed, _day, WORLD, DAY
from test_play47_joined_professions import _engine
from test_play48h1_funded_courier_provision import _sign
from test_play48_13npc_post72_relay import _stats
import test_play39_rain_drought_real_day as ref


def _physical_conservation(state):
    holdings = state.resources
    escrowed = sum(p["remaining"] for p in state.courier_provisions.values())
    water = sum(holdings[who]["water"] for who in
                ("well", "farm", "east_field", "huda", "hana")
                if who in holdings and "water" in holdings[who])
    # Cross-check the water with all actual recorded authorized rain and crop
    # starts; avoid counting unknown slots as free water.
    rain_units = state.hydrology_sources["well"]["received_total"]
    used_water = sum(plot["started"] for plot in state.farm_plots.values())
    assert water + used_water == ref.START_WATER + rain_units

    real_food = sum(h.get("food", 0) for h in holdings.values()) + escrowed
    real_grain = sum(h.get("grain", 0) for h in holdings.values())
    consumed = sum(m["quantity"] for m in state.consumptions.values())
    pending_bakes = sum(
        state.production_recipes[j["recipe_id"]]["input_amount"]
        for j in state.production_jobs.values()
        if j["status"] == "running"
        and state.production_recipes[j["recipe_id"]]["output_resource"] == "food")
    pending_grain = sum(
        ref.CROP_YIELD[j["site_id"]]
        for j in state.production_jobs.values()
        if j["status"] == "running"
        and state.production_recipes[j["recipe_id"]]["input_resource"] == "crop_ready")
    ripe = sum(holdings[f]["crop_ready"] * ref.CROP_YIELD[f]
               for f in ref.CROP_YIELD)
    produced_grain = sum(plot["matured"] * ref.CROP_YIELD[f]
                         for f, plot in state.farm_plots.items())
    assert (real_food + real_grain + consumed + pending_bakes
            + pending_grain + ripe == ref.START_FOOD + produced_grain)
    audit = audit_npc_economy(state)
    assert audit["copper_scope_complete"] and audit["copper_known_total"] == 12
    return {"escrow": escrowed, "real_food_plus_escrow": real_food,
            "consumed": consumed, "rain_units": rain_units}


def _treatment_day(path, end, *, rain=False, step=DAY // 4):
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
                    command_id=f"h1:day4:{target}", expected_revision=state.revision
                ).state
                assert state.time == target
                _physical_conservation(state)
                assert db.snapshot(WORLD).to_dict() == state.to_dict()
            if rain:
                state = FiniteWaterService(db, clock).record(
                    WORLD, "well", f"observed-rain-{end}", 2,
                    command_id=f"rain-{end}", expected_revision=state.revision
                ).state
            _physical_conservation(state)
            assert db.load(WORLD).to_dict() == state.to_dict()
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            clock.close_session(WORLD)
    with SQLiteEventStore(path) as reopened:
        assert reopened.verify(WORLD).to_dict() == state.to_dict()
    return state


def _activity_since(previous, current):
    return {key: current[key] - previous[key] for key in
            ("jobs", "trades", "wages", "meals", "food_sales")}


def test_genuine_13npc_0_to_96h_market_reservation_versus_unchanged_economy(tmp_path):
    control = tmp_path / "h1-control-original.sqlite"
    treatment = tmp_path / "h1-market-funded-wages.sqlite"
    _seed(control)
    shutil.copyfile(control, treatment)
    assert hashlib.sha256(control.read_bytes()).hexdigest() == (
        hashlib.sha256(treatment.read_bytes()).hexdigest()
    )
    with SQLiteEventStore(treatment) as db:
        initial = db.load(WORLD)
        assert initial.resources["market"]["food"] == 3
        assert len(initial.npcs) == 13
        setup = _sign(db)
        assert setup.resources["market"]["food"] == 1
        assert sum(p["remaining"] for p in setup.courier_provisions.values()) == 2
        _physical_conservation(setup)
    control72 = treated72 = None
    history = []
    for day in range(1, 5):
        end = day * DAY
        plain = _day(control, end, rain=day <= 3)
        treated = _treatment_day(treatment, end, rain=day <= 3)
        history.append({
            "day": day, "control": _stats(plain),
            "treatment": _stats(treated),
            "treatment_food_escrow": _physical_conservation(treated),
            "food_wages_paid": sum(len(c["payments"])
                                   for c in treated.courier_provisions.values()),
        })
        if day == 3:
            control72, treated72 = _stats(plain), _stats(treated)
            alternate = tmp_path / "treatment-day4-partitioned.sqlite"
            shutil.copyfile(treatment, alternate)

    old, new = _stats(plain), _stats(treated)
    assert control72 is not None and treated72 is not None
    assert old["copper"] == new["copper"] == 12
    assert old["deliveries"] == control72["deliveries"]
    assert all(new["deliveries"][who] >= treated72["deliveries"][who]
               for who in ("huda", "hana"))
    split = _treatment_day(alternate, 4 * DAY, step=DAY // 8)
    state_full = treated.to_dict()
    state_split = split.to_dict()
    state_full.pop("revision")
    state_split.pop("revision")
    assert state_full == state_split

    # A true recovery would need a NEW physical delivery *after* 72h plus
    # a subsequent, causally credible economic receipt; do not fabricate it.
    post72_delivery = any(
        new["deliveries"][who] > treated72["deliveries"][who]
        for who in ("huda", "hana")
    )
    extra = _activity_since(treated72, new)
    post72_economy = any(extra[key] > 0 for key in ("jobs", "trades", "meals"))
    improved = post72_delivery and post72_economy
    print("PLAY48H1_GENUINE_DAY4_AB", json.dumps({
        "identical_genesis_except_explicit_t0_reserved_stock": True,
        "identical_rain_and_known_copper": True,
        "history": history,
        "plain_72_to_96_delta": _activity_since(control72, old),
        "treatment_72_to_96_delta": extra,
        "post72_extra_physical_delivery": post72_delivery,
        "post72_extra_real_economy": post72_economy,
        "recovered_at_minimum_receipt_gate": improved,
        "causal_job_or_sale_attribution_independently_verified": False,
        "permanent_economic_sustainability_claim": False,
    }, sort_keys=True))
