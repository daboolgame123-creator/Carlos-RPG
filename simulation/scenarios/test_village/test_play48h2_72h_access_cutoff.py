"""PLAY-48H2 actual 13-NPC spatial food and money blockers at 24/48/72h.

This is one genuine from-genesis experimental world. Its event-driven NPCs
remain free to act or not act. Signed food escrow is genuine t=0 existing
market inventory, and only observed bounded rain is introduced later.
"""
from __future__ import annotations

import json

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.economic_diagnostics import audit_npc_economy
from carlos_sim.food_access_diagnostics import audit_food_access_barriers
from carlos_sim.hydrology import FiniteWaterService
from test_play47_closure_endurance import _seed, WORLD, DAY
from test_play47_joined_professions import _engine
from test_play48h1_funded_courier_provision import _sign


def test_genuine_treatment_thirteen_residents_causal_access_at_72h(tmp_path):
    path = tmp_path / "real-thirteen-escrow-72h.sqlite"
    opening = _seed(path)
    assert len(opening.npcs) == 13
    assert opening.resources["market"]["food"] == 3

    readings = []
    with SQLiteEventStore(path) as db:
        state = _sign(db)
        assert state.resources["market"]["food"] == 1
        assert sum(v["remaining"] for v in state.courier_provisions.values()) == 2
        clock = TimeEngine(db)
        clock.open_session(WORLD)
        try:
            engine = _engine(db, clock, shopping=True)
            for day in range(1, 4):
                end = day * DAY
                while state.time < end:
                    target = min(state.time + DAY // 4, end)
                    state = engine.advance(
                        WORLD, seconds=target - state.time,
                        command_id=f"h2:food-access:{target}",
                        expected_revision=state.revision
                    ).state
                    assert state.time == target
                state = FiniteWaterService(db, clock).record(
                    WORLD, "well", f"observed-rain-{end}", 2,
                    command_id=f"rain-{end}",
                    expected_revision=state.revision
                ).state
                audit = audit_food_access_barriers(state)
                cash = audit_npc_economy(state)
                assert cash["copper_scope_complete"] and cash["copper_known_total"] == 12
                assert audit["npc_count"] == 13
                assert audit["schema"] == 43 and audit["rules"] == 58
                assert db.snapshot(WORLD).to_dict() == state.to_dict()
                assert db.load(WORLD).to_dict() == state.to_dict()

                # Aggregate counts are operator-only, never future actions
                # assigned to NPCs; human-readable causes remain per actor.
                readings.append({
                    "day": day,
                    "time": state.time,
                    "market_saleable_loaves": audit["market_saleable_food_known"],
                    "market_employer_food_escrow": audit["market_site_owned_escrow_food"],
                    "hunger_at_cap": audit["hunger_at_100"],
                    "personally_spendable_copper_known_actors": sum(
                        x["personally_spendable_copper"] is not None
                        and x["personally_spendable_copper"] >= 2
                        for x in audit["actors"]),
                    "no_personally_known_road_to_market": sum(
                        x["known_road_path_to_market"] is None
                        for x in audit["actors"]),
                    "courier_hunger_blocked": [
                        x["npc_id"] for x in audit["actors"]
                        if "hunger_at_or_above_90" in x["courier_leg_blockers"]],
                    "courier_locations_and_cash_scope": {
                        x["npc_id"]: {
                            "location": x["location"],
                            "cash_scope": x["copper_scope"],
                            "personally_owned_food": x["known_personal_food"],
                            "hunger": x["hunger"],
                            "known_road_seconds_to_market":
                                x["known_road_seconds_to_market"],
                        } for x in audit["actors"]
                        if x["npc_id"] in ("huda", "hana")
                    },
                })
            assert db.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert db.db.execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            clock.close_session(WORLD)

        final = audit_food_access_barriers(state)
        assert state.time == 72 * 3600
        assert final["hunger_at_100"] == 12
        assert final["market_saleable_food_known"] == 3
        assert final["market_site_owned_escrow_food"] == 1
        assert sum(len(c["payments"])
                   for c in state.courier_provisions.values()) == 1
        assert all(x["npc_id"] in state.npcs for x in final["actors"])
        assert db.verify(WORLD).to_dict() == state.to_dict()
        print("PLAY48H2_CAUSAL_ACCESS_72H", json.dumps({
            "days": readings,
            "at_72h": final,
            "post72_economic_recovery_claimed": False,
            "operator_report_not_npc_knowledge": True,
        }, sort_keys=True))
    with SQLiteEventStore(path) as reopened:
        assert reopened.verify(WORLD).to_dict() == state.to_dict()
