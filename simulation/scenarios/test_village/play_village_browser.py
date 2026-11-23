"""CARLOS AR browser: genuine offline seven-NPC village with readable RTL Arabic.

Zero third-party dependencies, network bound to 127.0.0.1 ONLY, no script
resources, no external calls, no production/canonical save. All actions are
executed by the pre-existing player-authorized gateway, not by HTML/AI.
Use Ctrl+C in the parent console to discard the temporary SQLite test world.
"""
from __future__ import annotations

import argparse
import hmac
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
import shlex
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs
import webbrowser

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed
from play_physical_supply import WORLD
from play_village_ar import HELP_AR, lines_ar, translate_command
from play_village_local import create_session, execute
from play_village_web02_ui import friendly_result, render_web02


# This is a LOCAL app, not an HTTP API for an untrusted or remote network.
MAX_POST_BYTES = 8192
MAX_COMMAND_CHARS = 1000
BUTTONS = (
    ("مشهد", "مشهد"),
    ("انظر", "انظر"),
    ("المخزون", "المخزون"),
    ("الحالة", "الحالة"),
    ("العروض", "العروض"),
    ("مساعدة", "مساعدة"),
)
PAGE_START = """<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>كارلوس | القرية الحيّة</title>
  <style>
    :root { color-scheme: dark; font-family: "Segoe UI", Tahoma, Arial, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #111820; color: #eaf2fa; line-height: 1.75; }
    main { max-width: 960px; margin: 0 auto; padding: 24px 18px 48px; }
    header { margin-bottom: 20px; border-bottom: 1px solid #3b4f5f; padding-bottom: 16px; }
    h1 { font-size: 1.65rem; margin: 0 0 5px; color: #e8b46a; }
    h2 { font-size: 1.12rem; margin: 0 0 12px; color: #d7e5f1; }
    p { margin: 4px 0; }
    .sub { color: #b7c4ce; font-size: .94rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
    section { background: #1c2a36; border: 1px solid #405363; border-radius: 12px;
              padding: 18px; min-width: 0; margin-bottom: 14px; }
    .wide { grid-column: 1 / -1; }
    .display { white-space: pre-wrap; overflow-wrap: anywhere; unicode-bidi: plaintext;
               font-family: "Segoe UI", Tahoma, Arial, sans-serif; line-height: 1.8;
               margin: 0; text-align: start; }
    .buttons { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
    button { background: #365773; color: white; border: 1px solid #7290aa;
             padding: 9px 15px; border-radius: 8px; font: inherit; cursor: pointer; }
    button:hover, button:focus { background: #486c89; }
    button.primary { background: #b87837; border-color: #dc9f57; color: #10151a; font-weight: bold; }
    .command { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
    input[type=text] { flex: 1; min-width: 190px; width: 100%; border-radius: 8px;
                       background: #111b25; color: white; border: 1px solid #72879c;
                       padding: 12px; font: inherit; }
    .notice { background: #142738; border-inline-start: 3px solid #e0ab6c;
              padding: 14px; margin: 0; border-radius: 6px; }
    .hint { color: #a9b9c6; margin-top: 12px; font-size: .91rem; }
    code, bdi { unicode-bidi: isolate; }
  </style>
</head>
<body>
<main>
<header>
  <h1>كارلوس — القرية الحيّة</h1>
  <p class="sub">نسخة لعب تجريبية محلية بالعربية. سبع شخصيات مستقلة، وقت حقيقي داخل المحاكاة، وموارد محدودة.</p>
  <p class="sub">هذه ليست القصة الأصلية. الحفظ مؤقت ويُحذف عند إغلاق البرنامج. لا يوجد اتصال بخادم خارجي.</p>
  <p class="sub">إصدار الواجهة: WEB-01 / AUTH-DIAGNOSTIC-2</p>
</header>
"""
PAGE_END = """<p class="hint">تحرك بالأوامر الفعلية مثل: اذهب home-market ، ثم انتظر 90.
لإيقاف اللعبة وحذف حفظ التجربة اضغط Ctrl+C في نافذة تشغيل Python.</p>
</main></body></html>"""


class BrowserPlaySession:
    """Holds only one trusted player gateway; never expose the raw world."""
    def __init__(self, gateway):
        self.gateway = gateway
        self.csrf = secrets.token_urlsafe(32)
        self.serial = 0
        self.notice = "اكتب «مساعدة» للأوامر أو استعمل الأزرار. التحرك يحتاج طريقًا معروفًا."

    def command(self, raw: str) -> None:
        if len(raw) > MAX_COMMAND_CHARS:
            self.notice = "الأمر طويل جدًا."
            return
        try:
            line = translate_command(raw)
            if not line:
                self.notice = "اكتب أمرًا أولًا."
                return
            if line == "quit":
                self.notice = "للخروج وحذف العالم المؤقت اضغط Ctrl+C في نافذة Python."
                return
            if line == "help":
                self.notice = HELP_AR
                return
            # Display only real gateway-confirmed effects. Inspecting is read-only.
            before = self.gateway.inspect()
            self.serial += 1
            result = execute(self.gateway, line, self.serial)
            after = self.gateway.inspect()
            self.notice = friendly_result(result, line, before, after)
        except (ValueError, PermissionError, InvalidEvent, RevisionConflict,
                DuplicateCommand, AdvanceLimitExceeded, SessionClosed) as exc:
            self.notice = "رُفض الأمر: " + str(exc)

    def page(self) -> bytes:
        # WEB-02: presentation only. All generated controls still submit to
        # the exact same CSRF-protected, local PlayerGateway POST executor.
        return render_web02(self.gateway, self.csrf, self.notice)


def handler_for(session: BrowserPlaySession):
    class Handler(BaseHTTPRequestHandler):
        server_version = "CarlosOffline/1"

        def log_message(self, fmt, *args):
            # Avoid printing user speech and route commands to a console.
            pass

        def _host_ok(self):
            host = self.headers.get("Host", "")
            expected = "127.0.0.1:" + str(self.server.server_address[1])
            return self.client_address[0] == "127.0.0.1" and host == expected

        def _forbidden(self, reason: str):
            """Explain a denied request without echoing secrets or user input."""
            reasons = {
                "HOST": "عنوان الصفحة أو الاتصال ليس من جهازك المحلي.",
                "PATH": "مسار الأمر غير صحيح.",
                "ORIGIN": "المتصفح أرسل مصدرًا مختلفًا عن عنوان اللعبة.",
                "NULL_ORIGIN": "المتصفح أرسل مصدرًا مجهولًا من صفحة أخرى.",
                "CSRF": "رمز حماية الجلسة غير صحيح أو غير موجود. افتح صفحة اللعبة من جديد.",
            }
            explanation = reasons.get(reason, "رُفض الطلب بسبب فحص الأمان.")
            body = (
                '<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">'
                '<title>كارلوس — طلب مرفوض</title>'
                '<body style="font:18px Tahoma,Arial,sans-serif;'
                'background:#121c27;color:#edf3f9;padding:2rem">'
                '<h1>تعذر تنفيذ الأمر (403)</h1>'
                f'<p>{escape(explanation)}</p><p>رمز التشخيص: '
                f'<b dir="ltr">{escape(reason)}</b></p>'
                '<p>WEB-01 / AUTH-DIAGNOSTIC-2</p>'
                '<a href="/" style="color:#edb76f">العودة إلى صفحة اللعبة</a>'
                '</body></html>'
            ).encode("utf-8")
            self.send_response(403, "Forbidden")
            self._security_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _security_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            # Native HTML form POSTs send Origin: null under no-referrer,
            # which the strict same-origin guard correctly rejects.
            # same-origin retains referrer information ONLY for this
            # loopback origin and sends the real Origin for local POSTs.
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; "
                "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            )

        def do_GET(self):
            if not self._host_ok():
                self._forbidden("HOST")
                return
            if self.path == "/ui.js":
                body = Path(__file__).with_name("play_village_web03.js").read_bytes()
                self.send_response(200)
                self._security_headers()
                self.send_header("Content-Type", "text/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path != "/":
                self.send_error(404)
                return
            body = session.page()
            self.send_response(200)
            self._security_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if not self._host_ok():
                self._forbidden("HOST")
                return
            if self.path != "/act":
                self._forbidden("PATH")
                return
            expected_origin = "http://127.0.0.1:" + str(self.server.server_address[1])
            origin = self.headers.get("Origin")
            if origin not in (None, "null", expected_origin):
                self._forbidden("ORIGIN")
                return
            if origin == "null":
                # Some browser privacy modes strip a same-page form's Origin.
                # Never allow a cross-site null Origin. A valid random CSRF
                # token remains REQUIRED below, even for same-site requests.
                fetch_site = self.headers.get("Sec-Fetch-Site")
                referer = self.headers.get("Referer")
                if (fetch_site not in (None, "same-origin")
                        or (referer is not None
                            and not referer.startswith(expected_origin + "/"))):
                    self._forbidden("NULL_ORIGIN")
                    return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
            length = self.headers.get("Content-Length", "")
            if (content_type != "application/x-www-form-urlencoded"
                    or not length.isascii() or not length.isdecimal()
                    or not 1 <= int(length) <= MAX_POST_BYTES):
                self.send_error(400)
                return
            try:
                fields = parse_qs(
                    self.rfile.read(int(length)).decode("utf-8"),
                    keep_blank_values=True, strict_parsing=True,
                    max_num_fields=5,
                )
                if (len(fields.get("csrf", [])) != 1
                        or not hmac.compare_digest(fields["csrf"][0], session.csrf)):
                    self._forbidden("CSRF")
                    return
                if set(fields) == {"csrf", "command"} and len(fields["command"]) == 1:
                    raw = fields["command"][0]
                elif (set(fields) ==
                      {"csrf", "action", "offer_id", "quantity", "unit_price"}
                      and fields.get("action") == ["buy"]
                      and all(len(values) == 1 for values in fields.values())):
                    offer_id = fields["offer_id"][0]
                    qty_text, price_text = fields["quantity"][0], fields["unit_price"][0]
                    if (not offer_id or len(offer_id) > 128 or
                            not qty_text.isascii() or not qty_text.isdecimal() or
                            not price_text.isascii() or not price_text.isdecimal()):
                        self.send_error(400)
                        return
                    quantity, price = int(qty_text), int(price_text)
                    if not 1 <= quantity <= 1000 or not 0 <= price <= 100000000:
                        self.send_error(400)
                        return
                    # A single genuinely player-chosen buy action; the ledger
                    # rechecks physical quantity and quote price before transfer.
                    raw = ("buy " + shlex.quote(offer_id) + " " +
                           str(quantity) + " " + str(price))
                else:
                    self.send_error(400)
                    return
            except (UnicodeDecodeError, ValueError, KeyError):
                self.send_error(400)
                return
            session.command(raw)
            if self.headers.get("X-Carlos-Partial") == "1":
                # Same-origin progressive enhancement. The old POST/303/GET
                # remains the functioning no-JS fallback.
                body = session.page()
                self.send_response(200)
                self._security_headers()
                self.send_header("X-Carlos-Partial", "1")
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(303)
                self._security_headers()
                self.send_header("Location", "/")
                self.send_header("Content-Length", "0")
                self.end_headers()

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Arabic Carlos browser play")
    parser.add_argument("--no-browser", action="store_true",
                        help="Print the loopback URL without launching a browser")
    parser.add_argument("--port", type=int, default=0,
                        help="TCP loopback port; 0 chooses an unused port")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be in 0..65535")
    with TemporaryDirectory(prefix="carlos-play-browser-") as directory:
        with SQLiteEventStore(Path(directory) / "demo.sqlite") as db:
            clock = TimeEngine(db)
            gateway = create_session(db, clock)
            session = BrowserPlaySession(gateway)
            try:
                with HTTPServer(("127.0.0.1", args.port), handler_for(session)) as server:
                    url = "http://127.0.0.1:" + str(server.server_address[1]) + "/"
                    print("Carlos browser: " + url, flush=True)
                    print("Ctrl+C stops game and deletes its temporary SQLite world.", flush=True)
                    if not args.no_browser:
                        webbrowser.open(url)
                    try:
                        server.serve_forever(poll_interval=0.25)
                    except KeyboardInterrupt:
                        pass
            finally:
                clock.close_session(WORLD)
    print("Disposable Carlos world closed and deleted.", flush=True)


if __name__ == "__main__":
    main()
