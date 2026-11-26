"""NEEDS-01: real player nutrition/rest through the Arabic playable village.

These tests drive the shared player executor, render its player-only views,
and verify actual SQLite state. The existing disabled demo remains covered.
"""
from __future__ import annotations

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from play_physical_supply import WORLD, seed_physical_supply
from play_village_ar import translate_command
from play_village_browser import BrowserPlaySession
from play_village_local import create_session
from play_village_web02_ui import friendly_result


def make_ui(tmp_path, *, enabled=True):
    store = SQLiteEventStore(tmp_path / "playable-needs.sqlite")
    clock = TimeEngine(store)
    gateway = create_session(store, clock, player_needs_enabled=enabled)
    return store, clock, BrowserPlaySession(gateway)


@pytest.mark.parametrize("enabled", [False, True])
def test_player_bars_match_actual_configuration_without_get_events(tmp_path, enabled):
    store, clock, ui = make_ui(tmp_path, enabled=enabled)
    try:
        before = store.verify(WORLD).to_dict()
        html = ui.page().decode("utf-8")
        assert html.count('role="progressbar"') == (4 if enabled else 2)
        assert ('name="command" value="استرح"' in html) is enabled
        assert ("غير مُحاكى بعد" in html) is not enabled
        if enabled:
            assert 'aria-label="الجوع" aria-valuemin="0" aria-valuemax="100" aria-valuenow="20"' in html
            assert 'aria-label="التعب" aria-valuemin="0" aria-valuemax="100" aria-valuenow="10"' in html
        assert 'aria-label="الصحة (HP)" aria-valuemin="0" aria-valuemax="12" aria-valuenow="12"' in html
        assert 'aria-label="التحمّل (ST)" aria-valuemin="0" aria-valuemax="8" aria-valuenow="8"' in html
        assert store.verify(WORLD).to_dict() == before
        assert "نورا" not in html  # she is at the remote farm, not Carlos's home
    finally:
        clock.close_session(WORLD)
        store.close()


def test_real_buy_eat_partial_rest_loop_and_rejected_busy_actions(tmp_path):
    store, clock, ui = make_ui(tmp_path)
    try:
        profile = store.load(WORLD).rpg_profiles["carlos"]
        for command in ("اذهب home-market", "انتظر 90", "انتظر 30"):
            ui.command(command)
            assert not ui.notice.startswith("رُفض الأمر:")
        offer = next(o for o in ui.gateway.offers().details["offers"]
                     if o["resource"] == "food")
        ui.command(f"اشتر {offer['offer_id']} 2 {offer['unit_price']}")
        assert "تم شراء 2 طعام" in ui.notice
        ui.command("انتظر 180")
        assert ui.gateway.needs().details["hunger"] == 21
        ui.command("كل")
        assert ui.notice == "أكل كارلوس وحدة من طعامه. المتبقي: 1."
        assert ui.gateway.needs().details["hunger"] == 0
        assert ui.gateway.supplies().details["balances"] == {"coin_copper": 6, "food": 1}
        ui.command("انتظر 300")
        assert ui.gateway.needs().details["fatigue"] == 11

        ui.command("استرح")
        assert "بدأ كارلوس الراحة" in ui.notice
        assert store.load(WORLD).time == 600  # requesting rest earns no recovery
        assert ui.gateway.needs().details["fatigue"] == 11
        page = ui.page().decode("utf-8")
        assert "أكمل الراحة" in page
        assert 'name="command" value="انتظر 1800"' in page
        assert 'name="command" value="كل"' not in page
        assert 'name="command" value="اذهب ' not in page
        assert 'name="command" value="تحدث ' not in page
        assert 'name="command" value="انظر"' not in page
        assert 'class="buy-form"' not in page
        before_rejections = store.load(WORLD).to_dict()
        for command in ("كل", "اذهب home-market", "تحدث salma تحية مرحبا",
                        "استرح", "ابحث",
                        f"اشتر {offer['offer_id']} 1 {offer['unit_price']}"):
            ui.command(command)
            assert ui.notice.startswith("رُفض الأمر:"), command
            assert store.load(WORLD).to_dict() == before_rejections

        ui.command("انتظر 900")
        assert "كارلوس يستريح" in ui.notice
        assert ui.gateway.inspect().details["activity"] == {
            "kind": "resting", "remaining_seconds": 900}
        assert ui.gateway.needs().details["fatigue"] == 11
        assert ui.gateway.needs().details["hunger"] == 4
        ui.command("انتظر 900")
        assert "اكتملت راحة كارلوس" in ui.notice
        final = store.load(WORLD)
        assert final.time == 2400
        assert ui.gateway.needs().details["fatigue"] == 0
        assert ui.gateway.needs().details["hunger"] == 7
        assert "activity" not in ui.gateway.inspect().details
        assert final.rpg_profiles["carlos"] == profile
        assert final.resources["carlos"] == {"coin_copper": 6, "food": 1}
        assert sum(row.get("coin_copper", 0) for row in final.resources.values()) == 12
        assert len(final.npcs) == 7
        assert store.verify(WORLD).to_dict() == final.to_dict()
        assert 'name="command" value="استرح"' in ui.page().decode("utf-8")
    finally:
        clock.close_session(WORLD)
        store.close()


def test_foraging_busy_scene_hides_conflicting_actions_and_shows_completion(tmp_path):
    from living_player_fixture import (
        WORLD as forage_world, living_player_gateway, setup_living_foraging_world,
    )

    with SQLiteEventStore(tmp_path / "foraging-ui.sqlite") as store:
        setup_living_foraging_world(store)
        clock = TimeEngine(store)
        clock.open_session(forage_world)
        try:
            gateway = living_player_gateway(store, clock)
            gateway.forage(command_id="forage-ui", expected_revision=store.load(forage_world).revision)
            ui = BrowserPlaySession(gateway)
            before = gateway.inspect()
            page = ui.page().decode("utf-8")
            assert "أكمل البحث" in page
            assert 'name="command" value="انتظر 60"' in page
            assert 'name="command" value="اذهب ' not in page
            assert 'name="command" value="تحدث ' not in page
            result = gateway.wait(60, command_id="finish-ui", expected_revision=before.revision)
            message = friendly_result(result, "wait 60", before, gateway.inspect())
            assert message == "انتهى البحث، وجمع كارلوس وحدة طعام فعلية من المكان."
            assert gateway.supplies().details["balances"]["food"] == 1
            assert store.verify(forage_world).to_dict() == store.load(forage_world).to_dict()
        finally:
            clock.close_session(forage_world)


@pytest.mark.parametrize("command", ["استرح", "راحة", "ارتاح", "rest"])
def test_arabic_rest_is_an_explicit_existing_gateway_action(command):
    assert translate_command(command) == "rest"


@pytest.mark.parametrize("enabled,playable", [(True, False), (1, True), ("yes", True)])
def test_player_needs_bootstrap_requires_explicit_playable_flag(tmp_path, enabled, playable):
    with SQLiteEventStore(tmp_path / "invalid-fixture.sqlite") as store:
        with pytest.raises(ValueError, match="player_needs_enabled"):
            seed_physical_supply(store, playable_demo=playable, player_needs_enabled=enabled)
        assert store.db.execute("SELECT count(*) FROM worlds").fetchone()[0] == 0
