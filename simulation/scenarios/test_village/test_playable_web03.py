"""WEB-03: one factual bulk buy, dialogue evidence, and no-refresh HTTP updates."""
from __future__ import annotations

from html import unescape
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from play_physical_supply import WORLD
from play_village_browser import BrowserPlaySession
from play_village_local import create_session
from test_playable_arabic_browser import live_browser


def setup(tmp_path):
    store = SQLiteEventStore(tmp_path / "web03.sqlite")
    clock = TimeEngine(store)
    session = BrowserPlaySession(create_session(store, clock))
    return store, clock, session


def walk_to_open_market(ui):
    ui.command("اذهب home-market")
    ui.command("انتظر 90")
    ui.command("انتظر 30")
    return next(
        quote for quote in ui.gateway.offers().details["offers"]
        if quote["resource"] == "food"
    )


def test_bulk_buy_is_single_authorized_event_not_two_clicks(tmp_path):
    store, clock, ui = setup(tmp_path)
    try:
        quote = walk_to_open_market(ui)
        assert quote["available"] >= 2
        assert quote["unit_price"] == 2
        before_stock = ui.gateway.supplies().details["balances"]
        before_purchases = ui.gateway.purchases().details["total"]
        markup = ui.page().decode("utf-8")
        assert 'class="buy-form"' in markup
        assert 'name="quantity"' in markup
        assert f'name="offer_id" value="{quote["offer_id"]}"' in markup
        assert 'max="2"' in markup  # two real finite loaves in seeded village
        ui.command(f"اشتر {quote['offer_id']} 2 {quote['unit_price']}")
        balances = ui.gateway.supplies().details["balances"]
        assert balances["coin_copper"] == before_stock["coin_copper"] - 4
        assert balances["food"] == before_stock["food"] + 2
        receipts = ui.gateway.purchases().details
        assert receipts["total"] == before_purchases + 1
        assert receipts["recent"][0]["quantity"] == 2
        assert receipts["recent"][0]["total_paid"] == 4
        assert "تم شراء 2 طعام" in ui.notice
        assert store.verify(WORLD).to_dict() == store.load(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        store.close()


def test_conversation_shows_exact_player_words_and_only_recorded_reaction(tmp_path):
    store, clock, ui = setup(tmp_path)
    try:
        ui.command("اذهب home-market")
        ui.command("انتظر 90")
        ui.command("تحدث salma تحية مرحبا")
        records = ui.gateway.conversations().details["recent"]
        assert len(records) == 1
        saved = records[0]
        assert saved["text"] == "مرحبا"
        assert saved["recipient_id"] == "salma"
        assert saved["reaction"] == "acknowledged"
        page = ui.page().decode("utf-8")
        assert "قلت:" in page and "«مرحبا»" in page
        assert "استقبل التحية" in page
        assert "ليست جملًا منطوقة" in page
        assert "رد فعله المسجل" in ui.notice
        assert "قالت سلمى" not in page  # no fictitious quote attributed to her
        assert store.verify(WORLD).to_dict() == store.load(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        store.close()


def test_page_and_script_get_never_advance_world_or_spend_money(tmp_path):
    store, clock, ui = setup(tmp_path)
    try:
        before = store.verify(WORLD).to_dict()
        for _ in range(3):
            html = ui.page().decode("utf-8")
            assert '<script src="/ui.js" defer></script>' in html
            assert "<script>alert" not in html
            assert before == store.verify(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        store.close()


def _post(url, fields, *, partial=False, origin=None):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if partial:
        headers["X-Carlos-Partial"] = "1"
    if origin:
        headers["Origin"] = origin
    req = Request(url + "act", data=urlencode(fields).encode("ascii"), headers=headers)
    with urlopen(req, timeout=45) as response:
        assert response.status == 200  # partial 200, or browser fallback 303 -> 200
        return response.headers, response.read().decode("utf-8")


def test_live_local_buy_quantity_over_partial_post_with_csrf_and_bad_input_rejection(live_browser):
    url = live_browser
    with urlopen(url + "ui.js", timeout=15) as response:
        script = response.read().decode("utf-8")
        assert response.headers["Content-Type"].startswith("text/javascript")
        assert "fetch(" in script
    with urlopen(url, timeout=15) as response:
        first = response.read().decode("utf-8")
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    token = unescape(re.search(r'name="csrf" value="([^"]+)"', first).group(1))
    origin = url.rstrip("/")
    for command in ("اذهب home-market", "انتظر 90", "انتظر 30"):
        headers, page = _post(url, {"csrf": token, "command": command},
                              partial=True, origin=origin)
        assert headers["X-Carlos-Partial"] == "1"
        assert "WEB-03" in page
    quote_match = re.search(r'name="offer_id" value="([^"]+)"', page)
    assert quote_match
    quote_id = unescape(quote_match.group(1))
    assert 'name="quantity"' in page
    assert "نحاس: 10" in page

    with pytest.raises(HTTPError) as wrong:
        _post(url, {"csrf": "wrong", "action": "buy",
                    "offer_id": quote_id, "quantity": "2", "unit_price": "2"},
              partial=True, origin=origin)
    assert wrong.value.code == 403
    with pytest.raises(HTTPError) as negative:
        _post(url, {"csrf": token, "action": "buy",
                    "offer_id": quote_id, "quantity": "0", "unit_price": "2"},
              partial=True, origin=origin)
    assert negative.value.code == 400

    _, page = _post(url, {"csrf": token, "action": "buy", "offer_id": quote_id,
                          "quantity": "2", "unit_price": "2"},
                    partial=True, origin=origin)
    assert "تم شراء 2 طعام" in page
    assert "نحاس: 6" in page
    assert "طعام: 2" in page
    with urlopen(url, timeout=15) as response:
        reread = response.read().decode("utf-8")
    assert "نحاس: 6" in reread
    assert "طعام: 2" in reread
