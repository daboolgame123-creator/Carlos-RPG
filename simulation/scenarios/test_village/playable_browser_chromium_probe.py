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
                assert "الموقع: المنزل (home)" in page.locator("body").inner_text()
                with page.expect_response(lambda r: r.url.endswith("/act")) as receipt:
                    page.get_by_role("button", name="حدّث المشهد", exact=True).click()
                response = receipt.value
                req = response.request
                interesting = {
                    k: v for k, v in req.headers.items()
                    if k.lower() in ("host", "origin", "referer",
                                    "sec-fetch-site", "sec-fetch-mode",
                                    "content-type")
                }
                print("CHROMIUM_REAL_FORM_STATUS", response.status, flush=True)
                print("CHROMIUM_REAL_FORM_HEADERS", interesting, flush=True)
                print("CHROMIUM_REFERRER_POLICY",
                      response.headers.get("referrer-policy"), flush=True)
                assert response.status == 303, (
                    "Real browser did not pass first form POST; status=" +
                    str(response.status) + " headers=" + repr(interesting)
                )
                page.wait_for_url(url)
                assert "المشهد الحالي" in page.locator("body").inner_text()
                # WEB-02: test location-derived visible buttons rather than
                # manually typed raw commands.
                with page.expect_response(lambda r: r.url.endswith("/act")) as travel:
                    page.get_by_role("button", name=re.compile("اذهب إلى السوق")).click()
                assert travel.value.status == 303
                page.wait_for_url(url)
                assert "في الطريق" in page.locator("body").inner_text()
                with page.expect_response(lambda r: r.url.endswith("/act")) as advance:
                    page.get_by_role("button", name=re.compile("أكمل الرحلة")).click()
                assert advance.value.status == 303
                page.wait_for_url(url)
                assert "الموقع: السوق (market)" in page.locator("body").inner_text()
                assert "تحدث إلى سلمى" in page.locator("body").inner_text()
                assert page.get_by_role("progressbar").count() == 2
                assert "غير مُحاكى بعد" in page.locator("body").inner_text()
                print("CHROMIUM_REAL_WEB02_BUTTONS_AND_BARS_PASS", flush=True)
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
