"""WEB-02 acceptance: clear Arabic UI, verified player-only bars and one-click actions.

Exactly the existing seven-NPC disposable real world; UI never changes state on
GET nor invents player hunger, fatigue, cash, events or distant knowledge.
"""
from __future__ import annotations

import re

from carlos_sim import SQLiteEventStore, TimeEngine
from play_physical_supply import WORLD
from play_village_browser import BrowserPlaySession
from play_village_local import create_session


def session(tmp_path):
    db = SQLiteEventStore(tmp_path / "web02.sqlite")
    clock = TimeEngine(db)
    gateway = create_session(db, clock)
    return db, clock, BrowserPlaySession(gateway)


def test_verified_vitals_and_unimplemented_hunger_fatigue_are_distinct(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        before = db.verify(WORLD).to_dict()
        html = ui.page().decode("utf-8")
        assert "WEB-02" in html
        assert "الصحة (HP)" in html
        assert "التحمّل (ST)" in html
        assert 'aria-valuenow="12"' in html
        assert 'aria-valuemax="12"' in html
        assert 'aria-valuenow="8"' in html
        assert 'aria-valuemax="8"' in html
        # Never mistake ST for actual physical fatigue, and NEVER invent
        # NPC hunger percent for player Carlos. Disabled indicators remain.
        assert "الجوع" in html and "التعب" in html
        assert html.count("غير مُحاكى بعد") == 2
        assert html.count('role="progressbar"') == 2
        assert "لا توجد نسبة جوع لكارلوس" in html
        assert "لا توجد نسبة تعب لكارلوس" in html
        assert "لم تُسجل وجبة بعد" in html
        assert "نحاس" in html and "10" in html
        assert db.verify(WORLD).to_dict() == before
    finally:
        clock.close_session(WORLD)
        db.close()


def test_location_specific_actions_are_generated_from_visible_local_routes_only(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        home = ui.page().decode("utf-8")
        assert "الموقع: المنزل (home)" in home
        assert 'name="command" value="اذهب home-market"' in home
        assert "اذهب إلى السوق" in home
        assert "تحدث إلى سلمى" not in home
        assert "اذهب إلى المخبز" not in home
        assert "اشتر وحدة واحدة" not in home
        assert 'name="command" value="كل"' not in home

        ui.command("اذهب home-market")
        en_route = ui.page().decode("utf-8")
        assert "كارلوس في الطريق" in en_route
        assert "أكمل الرحلة" in en_route
        assert 'name="command" value="انتظر 90"' in en_route
        assert 'name="command" value="تحدث salma تحية مرحبا"' not in en_route

        ui.command("انتظر 90")
        market = ui.page().decode("utf-8")
        assert "الموقع: السوق (market)" in market
        assert "وصل كارلوس إلى السوق" in market
        assert "تحدث إلى سلمى" in market
        assert 'name="command" value="تحدث salma تحية مرحبا"' in market
        assert 'name="command" value="اذهب bakery-market"' in market
        assert "اذهب إلى المخبز" in market
        assert "اذهب إلى المنزل" in market
        # Production/orientation remains private unless visible at this site.
        assert "نورا (nora)" not in market
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_market_buy_button_appears_only_when_actual_offer_can_be_paid(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        ui.command("اذهب home-market")
        ui.command("انتظر 90")
        page = ui.page().decode("utf-8")
        assert "اشتر وحدة واحدة" not in page  # shopkeeper resting until t=120

        ui.command("انتظر 30")
        page = ui.page().decode("utf-8")
        offers = ui.gateway.offers().details["offers"]
        assert offers
        quote = next(x for x in offers if x["resource"] == "food")
        assert quote["unit_price"] == 2
        assert "اشتر وحدة واحدة" in page
        assert f'name="command" value="اشتر {quote["offer_id"]} 1 2"' in page

        ui.command(f"اشتر {quote['offer_id']} 1 2")
        assert "تم شراء 1 طعام" in ui.notice
        after = ui.page().decode("utf-8")
        assert "نحاس" in after and "8" in after
        assert 'name="command" value="كل"' in after
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_render_does_not_reveal_private_state_and_never_inserts_events(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        ui.notice = '<script>alert("fake")</script>'
        before = db.verify(WORLD).to_dict()
        for _ in range(3):
            page = ui.page().decode("utf-8")
            assert "<script>" not in page
            assert "&lt;script&gt;" in page
            assert "npcs" not in page and "registered_claims" not in page
        assert before == db.verify(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_needs_panel_only_shows_verified_last_meal_not_guessed_hunger(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        ui.command("اذهب home-market")
        ui.command("انتظر 90")
        ui.command("انتظر 30")
        quote = next(
            x for x in ui.gateway.offers().details["offers"]
            if x["resource"] == "food"
        )
        ui.command(f"اشتر {quote['offer_id']} 1 2")
        ui.command("كل")
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
        html = ui.page().decode("utf-8")
        assert "آخر وجبة موثقة: منذ 0 ثانية" in html
        assert "غير مُحاكى بعد" in html
        assert html.count('role="progressbar"') == 2
    finally:
        clock.close_session(WORLD)
        db.close()
