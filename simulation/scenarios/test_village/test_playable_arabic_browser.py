"""PLAYABLE WEB-01: RTL Arabic browser is a safe LOCAL view of real gateway."""
from __future__ import annotations

from html import unescape
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from play_physical_supply import WORLD
from play_village_browser import BrowserPlaySession
from play_village_local import create_session


def session(tmp_path):
    db = SQLiteEventStore(tmp_path / "test-browser.sqlite")
    clock = TimeEngine(db)
    gateway = create_session(db, clock)
    return db, clock, BrowserPlaySession(gateway)


def test_html_is_real_rtl_player_view_with_no_world_mutation(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        before = db.verify(WORLD).to_dict()
        page = ui.page().decode("utf-8")
        assert '<html lang="ar" dir="rtl">' in page
        assert "كارلوس — القرية الحيّة" in page
        assert "الموقع: المنزل (home)" in page
        assert "home-market" in page
        assert "ممتلكات كارلوس" in page
        assert "نحاس: 10" in page
        assert '<input type="hidden" name="csrf"' in page
        assert '<script' not in page
        assert db.verify(WORLD).to_dict() == before
    finally:
        clock.close_session(WORLD)
        db.close()


def test_actual_arabic_browser_actions_keep_ledger_authoritative(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        before = db.verify(WORLD).to_dict()
        ui.command("مشهد")
        assert "المشهد الحالي" in ui.notice
        assert db.verify(WORLD).to_dict() == before
        ui.command("اذهب home-market")
        assert "في الطريق" in ui.notice
        assert db.verify(WORLD).time == 0
        ui.command("انتظر 90")
        assert db.verify(WORLD).time == 90
        assert "الموقع: السوق (market)" in ui.page().decode("utf-8")
        ui.command("اشتر made-up-offer 1 2")
        assert "رُفض الأمر:" in ui.notice
        assert db.verify(WORLD).time == 90
        assert db.verify(WORLD).to_dict() == db.load(WORLD).to_dict()
    finally:
        clock.close_session(WORLD)
        db.close()


def test_untrusted_text_is_html_escaped_and_zero_world_events(tmp_path):
    db, clock, ui = session(tmp_path)
    try:
        before = db.verify(WORLD).to_dict()
        ui.notice = '<script>alert("XSS")</script> & <b>forged</b>'
        page = ui.page().decode("utf-8")
        assert "<script>" not in page and "<b>forged</b>" not in page
        assert "&lt;script&gt;" in page and "&lt;b&gt;" in page
        assert db.verify(WORLD).to_dict() == before
    finally:
        clock.close_session(WORLD)
        db.close()


@pytest.fixture
def live_browser():
    """A child process owns SQLite and the HTTP event loop in one thread."""
    script = Path(__file__).with_name("play_village_browser.py")
    simulation = script.parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(simulation / "src"), str(script.parent)]
    )
    env["PYTHONIOENCODING"] = "utf-8"
    process = subprocess.Popen(
        [sys.executable, "-u", str(script), "--no-browser", "--port", "0"],
        cwd=simulation, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    )
    try:
        first = process.stdout.readline().strip()
        match = re.fullmatch(r"Carlos browser: (http://127\.0\.0\.1:\d+/)", first)
        if match is None:
            raise AssertionError(f"browser did not start: {first!r}")
        yield match.group(1)
    finally:
        if process.poll() is None:
            process.terminate()
        out, err = process.communicate(timeout=15)
        if process.returncode not in (0, -15, 1):
            # Windows terminate returns a signed error code; abnormal exit is
            # expected only after the test has force-closed the child.
            assert "Traceback (most recent call last)" not in err, err[-2000:]


def _get(url, **headers):
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"
        assert response.headers["Cache-Control"] == "no-store"
        # A native HTML form POST under 'no-referrer' sends Origin: null,
        # which would be 403 here. same-origin preserves the correct origin
        # without leaking a Referer to another website.
        assert response.headers["Referrer-Policy"] == "same-origin"
        assert response.headers["Content-Security-Policy"].startswith(
            "default-src 'none';"
        )
        return response.read().decode("utf-8")


def _post(url, csrf, command, *, origin=None, host=None):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if origin is not None:
        headers["Origin"] = origin
    if host is not None:
        headers["Host"] = host
    data = urlencode({"csrf": csrf, "command": command}).encode("ascii")
    with urlopen(Request(url + "act", data=data, headers=headers), timeout=45) as response:
        # urllib follows safe 303 and gets the resulting GET page.
        assert response.status == 200
        return response.read().decode("utf-8")


def test_real_loopback_http_interaction_in_arabic_and_csrf_guard(live_browser):
    url = live_browser
    html = _get(url)
    assert '<html lang="ar" dir="rtl">' in html
    assert "الموقع: المنزل (home)" in html
    assert "<script" not in html
    csrf_match = re.search(r'name="csrf" value="([^"]+)"', html)
    assert csrf_match, "anti-CSRF field missing"
    csrf = unescape(csrf_match.group(1))
    assert len(csrf) >= 20

    # No external Host or forged CSRF/Origin can command the local world.
    with pytest.raises(HTTPError) as exc:
        _get(url, Host="not-local.example")
    assert exc.value.code == 403
    with pytest.raises(HTTPError) as exc:
        _post(url, "wrong", "انتظر 90")
    assert exc.value.code == 403
    with pytest.raises(HTTPError) as exc:
        _post(url, csrf, "انتظر 90", origin="https://evil.example")
    assert exc.value.code == 403
    # Regression: do not weaken the strict Origin gate to accept "null".
    # The browser-facing Referrer-Policy must instead preserve the origin.
    with pytest.raises(HTTPError) as exc:
        _post(url, csrf, "انتظر 90", origin="null")
    assert exc.value.code == 403
    assert "الزمن: 0 ثانية" in _get(url)

    html = _post(url, csrf, "مشهد", origin=url.rstrip("/"))
    assert "المشهد الحالي" in html and "الزمن: 0 ثانية" in html
    html = _post(url, csrf, "اذهب home-market", origin=url.rstrip("/"))
    assert "في الطريق" in html
    html = _post(url, csrf, "انتظر 90", origin=url.rstrip("/"))
    assert "الموقع: السوق (market)" in html
    assert "الزمن: 90 ثانية" in html

    html = _post(url, csrf, "اشتر impossible 1 2")
    assert "رُفض الأمر" in html
    assert "الزمن: 90 ثانية" in _get(url)
