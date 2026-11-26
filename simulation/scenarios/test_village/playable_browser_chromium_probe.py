"""Reproduce REAL Chromium/Windows browser form clicks, not urllib fake-Origin.

CI-only test dependency: playwright + Chromium. This is not shipped/required
by the offline Carlos browser. Never print the anti-CSRF token.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright


def main() -> None:
    src = Path(__file__).resolve()
    simulation = src.parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(simulation / "src"), str(src.parent)])
    env["PYTHONIOENCODING"] = "utf-8"
    server = subprocess.Popen(
        [sys.executable, "-u", str(src.with_name("play_village_browser.py")),
         "--no-browser", "--port", "0"],
        cwd=simulation, env=env, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        startup = server.stdout.readline().strip()
        matched = re.fullmatch(r"Carlos browser: (http://127\.0\.0\.1:\d+/)", startup)
        assert matched, "did not start: " + repr(startup)
        url = matched.group(1)
        with sync_playwright() as playwright:
            # Hosted Windows Actions runners provide Google Chrome without
            # requiring a heavyweight browser install in the game or CI.
            managed_chrome = Path(playwright.chromium.executable_path)
            chrome = ((str(managed_chrome) if managed_chrome.is_file() else None) or
                      shutil.which("google-chrome") or
                      shutil.which("chromium") or
                      shutil.which("chromium-browser"))
            if sys.platform == "win32" and chrome is None:
                chrome = next((str(candidate)
                               for root in (os.environ.get("PROGRAMFILES"),
                                            os.environ.get("PROGRAMFILES(X86)"),
                                            os.environ.get("LOCALAPPDATA"))
                               if root
                               for candidate in (
                                   Path(root) / "Google" / "Chrome" /
                                   "Application" / "chrome.exe",
                               )
                               if candidate.is_file()), None)
            assert chrome, "preinstalled Chrome not found on CI runner"
            browser = playwright.chromium.launch(
                headless=True, executable_path=chrome,
            )
            try:
                page = browser.new_page()
                page.goto(url)
                page.locator('script[src="/ui.js"]').wait_for(state="attached")
                page.get_by_role("button", name="حدّث المشهد", exact=True).wait_for()
                navigation_events = []
                page.on("framenavigated", lambda frame: (
                    navigation_events.append(frame.url)
                    if frame == page.main_frame else None
                ))
                assert "الموقع: المنزل (home)" in page.locator("body").inner_text()

                with page.expect_response(lambda r: r.url.endswith("/act")) as receipt:
                    page.get_by_role("button", name="حدّث المشهد", exact=True).click()
                assert receipt.value.status == 200
                assert receipt.value.headers.get("x-carlos-partial") == "1"
                page.get_by_text("أنت في المنزل.").wait_for()

                with page.expect_response(lambda r: r.url.endswith("/act")) as travel:
                    page.get_by_role("button", name=re.compile("اذهب إلى السوق")).click()
                assert travel.value.status == 200
                page.get_by_text(re.compile("كارلوس في الطريق")).first.wait_for()
                with page.expect_response(lambda r: r.url.endswith("/act")) as advance:
                    page.get_by_role("button", name=re.compile("أكمل الرحلة")).click()
                assert advance.value.status == 200
                page.get_by_text("الموقع: السوق (market)").wait_for()
                assert page.get_by_role("progressbar").count() == 4
                assert "غير مُحاكى بعد" not in page.locator("body").inner_text()
                assert page.get_by_role("progressbar", name="الجوع", exact=True).get_attribute("aria-valuenow") == "20"
                assert page.get_by_role("progressbar", name="التعب", exact=True).get_attribute("aria-valuenow") == "10"

                with page.expect_response(lambda r: r.url.endswith("/act")) as greet:
                    page.get_by_role("button", name="تحدث إلى سلمى").click()
                assert greet.value.status == 200
                page.get_by_text("«مرحبا»").wait_for()
                assert "استقبل التحية" in page.locator("body").inner_text()

                with page.expect_response(lambda r: r.url.endswith("/act")) as waiting:
                    page.get_by_role("button", name="انتظر 30 ثانية").click()
                assert waiting.value.status == 200
                page.get_by_role("spinbutton", name="كمية الشراء").wait_for()
                page.get_by_role("spinbutton", name="كمية الشراء").fill("2")
                page.get_by_text("الإجمالي: 4 نحاس").wait_for()
                with page.expect_response(lambda r: r.url.endswith("/act")) as purchase:
                    page.get_by_role("button", name="اشتر الكمية").click()
                assert purchase.value.status == 200
                page.get_by_text("تم شراء 2 طعام", exact=False).wait_for()
                assert "نحاس: 6" in page.locator("body").inner_text()
                assert "طعام: 2" in page.locator("body").inner_text()

                # Advance actual world time, then consume one of the purchased
                # units. The renderer cannot invent the resulting need values.
                page.get_by_role("textbox", name="أمر كارلوس").fill("انتظر 180")
                with page.expect_response(lambda r: r.url.endswith("/act")):
                    page.get_by_role("button", name="تنفيذ الأمر", exact=True).click()
                page.locator('[aria-label="الجوع"][aria-valuenow="21"]').wait_for()
                with page.expect_response(lambda r: r.url.endswith("/act")):
                    page.get_by_role("button", name="كل وحدة من طعامك", exact=True).click()
                page.get_by_text("أكل كارلوس وحدة من طعامه. المتبقي: 1.", exact=True).wait_for()
                assert page.get_by_role("progressbar", name="الجوع", exact=True).get_attribute("aria-valuenow") == "0"
                assert "طعام: 1" in page.locator("body").inner_text()

                with page.expect_response(lambda r: r.url.endswith("/act")):
                    page.get_by_role("button", name="استرح 30 دقيقة", exact=True).click()
                page.get_by_role("button", name=re.compile("أكمل الراحة")).wait_for()
                assert page.get_by_role("button", name=re.compile("اذهب إلى")).count() == 0
                assert page.get_by_role("button", name="كل وحدة من طعامك", exact=True).count() == 0
                assert page.get_by_role("button", name=re.compile("تحدث إلى")).count() == 0
                assert page.get_by_role("progressbar", name="التعب", exact=True).get_attribute("aria-valuenow") == "10"
                with page.expect_response(lambda r: r.url.endswith("/act")):
                    page.get_by_role("button", name="انتظر 90 ثانية", exact=True).click()
                page.locator('form:has(input[name="command"][value="انتظر 1710"]) button').wait_for()
                assert page.get_by_role("progressbar", name="التعب", exact=True).get_attribute("aria-valuenow") == "10"
                with page.expect_response(lambda r: r.url.endswith("/act")):
                    page.get_by_role("button", name=re.compile("أكمل الراحة")).click()
                page.get_by_text(re.compile("اكتملت راحة كارلوس")).wait_for()
                assert page.get_by_role("progressbar", name="التعب", exact=True).get_attribute("aria-valuenow") == "0"
                assert page.get_by_role("progressbar", name="الجوع", exact=True).get_attribute("aria-valuenow") == "6"
                assert page.get_by_role("progressbar", name="الصحة (HP)", exact=True).get_attribute("aria-valuenow") == "12"
                assert page.get_by_role("progressbar", name="التحمّل (ST)", exact=True).get_attribute("aria-valuenow") == "8"
                assert "نحاس: 6" in page.locator("body").inner_text()
                assert "طعام: 1" in page.locator("body").inner_text()

                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                assert navigation_events == [], (
                    "Actions must update the current document, not navigate "
                    + repr(navigation_events)
                )
                # Native forms still work when JavaScript is disabled.
                fallback = browser.new_context(java_script_enabled=False)
                try:
                    plain = fallback.new_page()
                    plain.goto(url)
                    with plain.expect_navigation():
                        plain.get_by_role("button", name="حدّث المشهد", exact=True).click()
                    assert plain.url == url
                    assert plain.get_by_role("progressbar").count() == 4
                    assert plain.get_by_role("progressbar", name="الجوع", exact=True).get_attribute("aria-valuenow") == "6"
                finally:
                    fallback.close()
                print("CHROMIUM_REAL_WEB03_NO_RELOAD_BULK_BUY_AND_TALK_PASS", flush=True)
                print("CHROMIUM_REAL_NEEDS01_EAT_REST_PARTIAL_MOBILE_AND_NOJS_PASS", flush=True)
            finally:
                browser.close()
    finally:
        if server.poll() is None:
            server.terminate()
        _, stderr = server.communicate(timeout=15)
        if "Traceback" in stderr:
            print("SERVER_TRACEBACK", stderr[-2000:], file=sys.stderr)


if __name__ == "__main__":
    main()
