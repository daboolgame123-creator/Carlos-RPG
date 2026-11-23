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
            chrome = (shutil.which("google-chrome") or
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
                assert page.get_by_role("progressbar").count() == 2
                assert "غير مُحاكى بعد" in page.locator("body").inner_text()

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
                assert navigation_events == [], (
                    "Actions must update the current document, not navigate "
                    + repr(navigation_events)
                )
                print("CHROMIUM_REAL_WEB03_NO_RELOAD_BULK_BUY_AND_TALK_PASS", flush=True)
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
