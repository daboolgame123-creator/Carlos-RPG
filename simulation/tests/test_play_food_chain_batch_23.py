"""PLAY-23: evidence from real grain, oven, site ownership, NPC purchase/meal."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SIM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SIM / "scenarios" / "test_village"))
from play_food_chain import (  # noqa: E402
    INITIAL_FOOD_EQUIVALENT, INITIAL_COPPER, OFFER_ID, RECIPE_ID,
    run_food_chain, setup_living_food_chain_world,
)
from living_player_fixture import (  # noqa: E402
    WORLD, PLAYER, living_player_gateway, setup_living_npc_ecology_world,
)

from carlos_sim import NPCMarketService, NPCProductionService
from carlos_sim.resumable_play import ResumableTestSession
from carlos_sim.store import InvalidEvent


@pytest.mark.parametrize("choice,trade,meal,site_food", [
    ("sell", 1, 1, 0),
    ("hold", 0, 0, 1),
])
def test_one_physically_created_meal_needs_real_sale_and_npc_decision(
        tmp_path, choice, trade, meal, site_food):
    result = run_food_chain(tmp_path / (choice + ".sqlite"), choice,
                            horizon_seconds=180)
    assert result["canonical_story"] is False
    assert result["player_visible"]["time"] == 180
    audit = result["test_audit_only"]
    assert audit["npc_count_not_mortality"] == 7
    assert audit["production_jobs"] == 1
    assert audit["market_transactions"] == trade
    first = audit["first_autonomous_tick"]
    assert first["adel_meals"] == meal
    assert first["site_food"] == site_food
    assert first["adel_food"] == 0
    assert first["total_npc_meals"] >= 2
    assert audit["production_scripted_not_autonomous"] is True
    assert audit["trade_scripted_not_autonomous"] is True
    stocks = audit["end_balances"]
    assert stocks["unprocessed_grain"] == 0
    assert stocks["site_produced_food"] == site_food
    assert stocks["copper_total"] == INITIAL_COPPER
    assert (stocks["npc_food_eaten"] + stocks["npc_food_owned"]
            + stocks["wild_food"] + stocks["unprocessed_grain"]
            + stocks["site_produced_food"] + stocks["player_food"]
            ) == INITIAL_FOOD_EQUIVALENT
    assert set(audit["refusals_without_mutation"]) == {
        "wrong_profession", "double_work", "premature_sale",
        "remote_buyer", "wrong_price", "duplicate_wait",
        "stale_revision", *({"double_sale"} if choice == "sell" else set()),
    }
    assert result["restart"] == {
        "verified_full_replay": True, "handoff_stable": True,
        "duplicate_and_stale_rejected": True, "explicit_resumed_time": 190,
    }


def test_counterfactuals_diverge_only_when_buyer_receives_food(tmp_path):
    sale = run_food_chain(tmp_path / "sale.sqlite", "sell",
                          horizon_seconds=180)
    hold = run_food_chain(tmp_path / "hold.sqlite", "hold",
                          horizon_seconds=180)
    s = sale["test_audit_only"]["first_autonomous_tick"]
    h = hold["test_audit_only"]["first_autonomous_tick"]
    assert s["adel_meals"] == 1 and h["adel_meals"] == 0
    assert s["adel_hunger"] < h["adel_hunger"]
    assert s["site_food"] == 0 and h["site_food"] == 1
    assert (sale["test_audit_only"]["end_balances"]["copper_total"] ==
            hold["test_audit_only"]["end_balances"]["copper_total"])


def test_full_replay_is_deterministic_across_two_sqlite_files(tmp_path):
    a = run_food_chain(tmp_path / "a.sqlite", "sell",
                       horizon_seconds=180)
    b = run_food_chain(tmp_path / "b.sqlite", "sell",
                       horizon_seconds=180)
    assert a == b


def test_player_handoff_leaves_market_and_npc_hidden(tmp_path):
    result = run_food_chain(tmp_path / "private.sqlite", "sell",
                            horizon_seconds=180)
    public = json.dumps(result["player_visible"], ensure_ascii=False)
    for secret in (
        '"npcs"', '"production_jobs"', '"market_trades"',
        '"consumptions"', '"foraging_attempts"', '"obligations"',
        '"site_produced_food"', '"adel_hunger"', '"test_audit_only"',
    ):
        assert secret not in public


@pytest.mark.parametrize("choice,seconds", [
    ("not-a-choice", 180), ("sell", 90), ("sell", 1201),
    ("sell", True), ("sell", "180"), ("hold", 180.0),
])
def test_reject_invalid_choice_or_horizon_before_sqlite_file(
        tmp_path, choice, seconds):
    path = tmp_path / "absent.sqlite"
    with pytest.raises(ValueError):
        run_food_chain(path, choice, horizon_seconds=seconds)
    assert not path.exists()


def test_no_raw_grain_does_not_mint_a_loaf(tmp_path):
    def seed(store):
        setup_living_food_chain_world(store, grain=0)
    with ResumableTestSession.create(
        tmp_path / "empty-grain.sqlite", WORLD, PLAYER, seed,
        disposable_test=True,
    ) as session:
        db = session.store
        before = db.load(WORLD).to_dict()
        with pytest.raises(InvalidEvent):
            NPCProductionService(db, session.clock).start(
                WORLD, "basim", RECIPE_ID, "no-grain",
                expected_revision=before["revision"])
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before
        assert before["resources"]["square"]["food"] == 0


def test_real_insufficient_copper_fails_without_creating_sale(tmp_path):
    def seed(store):
        setup_living_food_chain_world(store, buyer_copper=1)
    with ResumableTestSession.create(
        tmp_path / "poor-buyer.sqlite", WORLD, PLAYER, seed,
        disposable_test=True,
    ) as session:
        db, clock = session.store, session.clock
        NPCProductionService(db, clock).start(
            WORLD, "basim", RECIPE_ID, "valid-batch",
            expected_revision=db.load(WORLD).revision)
        clock.advance(WORLD, seconds=90, command_id="wait90",
                      expected_revision=db.load(WORLD).revision)
        market = NPCMarketService(db, clock)
        market.post(WORLD, "salma", "square", "square", OFFER_ID,
                    "food", 1, "coin_copper", 2,
                    expected_revision=db.load(WORLD).revision)
        before = db.load(WORLD).to_dict()
        with pytest.raises(InvalidEvent):
            market.buy(WORLD, "adel", "too-poor", OFFER_ID, 1, 2,
                       expected_revision=before["revision"])
        assert db.load(WORLD).to_dict() == before
        assert db.verify(WORLD).to_dict() == before
        assert db.load(WORLD).resources["square"]["food"] == 1
        assert db.load(WORLD).resources["adel"]["food"] == 0


def test_food_chain_fixture_does_not_change_old_ecology_or_enable_production(
        tmp_path):
    with ResumableTestSession.create(
        tmp_path / "old.sqlite", WORLD, PLAYER, setup_living_npc_ecology_world,
        disposable_test=True,
    ) as session:
        before = session.store.load(WORLD).to_dict()
        assert session.store.db.execute(
            "SELECT COUNT(*) FROM commands WHERE world_id=? AND command_id=?",
            (WORLD, "living-chain-recipe-stall")).fetchone()[0] == 0
        assert living_player_gateway(
            session.store, session.clock,
            npc_survival_demo=True, npc_ecology_demo=True)
        assert not session.store.load(WORLD).production_recipes
        assert not session.store.load(WORLD).market_stalls
        assert session.store.load(WORLD).to_dict() == before
        assert session.store.verify(WORLD).to_dict() == before


def test_invalid_bootstrap_resources_do_not_create_world(tmp_path):
    for idx, bad in enumerate(({"grain": -1}, {"grain": True},
                               {"grain": 2}, {"buyer_copper": -1},
                               {"buyer_copper": True},
                               {"buyer_copper": 3})):
        target = tmp_path / f"invalid-{idx}.sqlite"
        with pytest.raises(ValueError):
            with ResumableTestSession.create(
                target, WORLD, PLAYER,
                lambda store, args=bad: setup_living_food_chain_world(store, **args),
                disposable_test=True,
            ):
                pass
        assert not target.exists()
