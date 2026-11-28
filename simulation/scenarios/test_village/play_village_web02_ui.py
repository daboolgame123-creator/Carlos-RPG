"""WEB-02 Arabic browser presentation ONLY for the genuine Carlos player gateway.

No world state reads, no simulation controls, no private NPC projections:
the caller supplies public/player-scoped gateway views. HTML forms only send
existing player actions back through the original verified executor.

The player has real fixture RPG HP/ST. NEEDS-01 displays hunger/fatigue only
when explicitly initialized by the engine; legacy worlds stay unmodeled.
"""
from __future__ import annotations

from html import escape
from typing import Any

from play_village_ar import LOCATION_NAMES, NPC_NAMES

ACTIVITY_LABELS = {
    "working": "يعمل",
    "resting": "يستريح",
    "waiting": "ينتظر",
    "travelling": "يسافر",
    "traveling": "يسافر",
    "investigating": "يستكشف",
    "foraging": "يجمع الطعام",
}
RESOURCE_LABELS = {
    "coin_copper": "نحاس",
    "food": "طعام",
    "bread": "خبز",
}
STYLE = r"""
:root { color-scheme: dark; font-family: Tahoma,"Segoe UI",Arial,sans-serif; }
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; background: #111820; color: #eaf2f9; line-height: 1.7; }
main { max-width: 1120px; margin: auto; padding: 24px 18px 54px; }
header { padding: 22px 26px; background: linear-gradient(125deg,#273645,#172430);
         border: 1px solid #3b5266; border-radius: 16px; margin-bottom: 18px; }
h1 { font-size: clamp(1.4rem,3vw,2rem); color: #eeb975; margin: 0 0 5px; }
h2 { font-size: 1.16rem; margin: 0 0 12px; }
h3 { font-size: 1rem; margin: 0 0 8px; }
p { margin: 6px 0; }
small,.muted { color: #aebfce; }
.layout { display: grid; grid-template-columns: minmax(0,1.25fr) minmax(290px,.8fr);
          gap: 16px; align-items:start; }
.column { display:grid; gap:16px; min-width:0; }
.card { background: #1b2a37; border: 1px solid #3a5061; padding: 19px;
        border-radius: 14px; min-width:0; }
.card.highlight { background: #213748; border-color: #59718a; }
.meta { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:12px; }
.pill { display:inline-block; border:1px solid #526d81; border-radius: 999px;
        background:#243847; padding:3px 12px; color:#dcecf6; }
.location { font-size:1.28rem; font-weight:700; }
.people, .routes, .offers { display:grid; gap:9px; }
.person { display:flex; align-items:center; gap:10px; justify-content:space-between;
          border-bottom:1px solid #33485a; padding:7px 0; flex-wrap:wrap; }
.person:last-child { border:0; }
.person-note { color:#b7c8d8; font-size:.91rem; }
.group { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 4px; }
button { cursor:pointer; border-radius:9px; border:1px solid #6388a7;
         color:white; font:inherit; background:#375c79; padding:9px 12px; }
button:hover, button:focus-visible { background:#496f8d; outline:2px solid #9fbed6; }
button.primary { background:#ba8749; color:#12202b; font-weight:700; border-color:#e2b26c; }
button.secondary { background: #284657; }
button[disabled] { opacity:.45; cursor:not-allowed; }
button:disabled:hover { background:#375c79; outline:none; }
form { margin:0; }
.action-row { display:flex; flex-wrap:wrap; gap:8px; }
.action-row form { display:inline-block; }
form.command { display:flex; align-items:center; flex-wrap:wrap; gap:10px; margin-top:16px; }
input[type=text] { flex:1; min-width:210px; width:100%; background:#101f2c; color:white;
                   border:1px solid #627f94; border-radius:9px; padding:12px; font:inherit; }
output { color:#daeaf4; }
.result { border-inline-start:4px solid #dfa35e; background:#142738;
          padding:12px 15px; border-radius:7px; white-space:pre-wrap;
          overflow-wrap:anywhere; unicode-bidi:plaintext; }
.stats { display:grid; gap:14px; }
.stat-row { display:grid; gap:5px; }
.stat-title { display:flex; gap:8px; justify-content:space-between; align-items:center; }
.bar { height:12px; width:100%; background:#0b1620; border:1px solid #4a6578;
       overflow:hidden; border-radius:20px; }
.bar>span { display:block; height:100%; background:linear-gradient(90deg,#cb8f43,#f1c883); }
.bar.hp>span { background:linear-gradient(90deg,#5a9d83,#a9e6ba); }
.bar.st>span { background:linear-gradient(90deg,#487aa9,#9fcee9); }
.bar.unknown { background: repeating-linear-gradient(45deg,#27343e 0 9px,#1a2731 9px 18px);
               border-style:dashed; }
.balances { display:flex; gap:8px; flex-wrap:wrap; }
.balance { background:#122635; border:1px solid #3d5b70; border-radius:8px;
           padding:7px 12px; }
.offer { display:grid; gap:8px; padding:12px; border:1px solid #3b5264; border-radius:9px; }
.notice { padding:11px; background:#142737; border-radius:8px; color:#ccdce8; }
.sep { border:0; border-top:1px solid #354c5e; margin:15px 0; }
.code { direction:ltr; unicode-bidi:isolate; display:inline-block; font-size:.94em;
        font-family:Consolas,monospace; color:#cde3ed; }
.help { color:#a9bed0; font-size:.92rem; }
.footer { padding-top:15px; text-align:center; color:#94abba; font-size:.86rem; }
/* WEB-03: finite quantity form and genuine recorded conversations. */
.buy-form { display:flex; flex-wrap:wrap; align-items:center; gap:10px; }
.buy-form label { display:flex; gap:8px; align-items:center; }
.buy-form input[type=number] { color:#fff; background:#122636; border:1px solid #688fa9;
    border-radius:7px; padding:7px; width:80px; font:inherit; direction:ltr; }
.buy-form output { min-width:120px; color:#ecc58d; }
.conversation { background:#122637; border:1px solid #446076; border-radius:9px;
                padding:12px; margin:10px 0; }
.conversation p { white-space:pre-wrap; overflow-wrap:anywhere; }
@media(max-width:760px) { main{padding:12px;} header{padding:17px;} .layout{grid-template-columns:1fr;} }
"""



REACTIONS = {
    "acknowledged": "استقبل التحية.",
    "welcomed": "رحّب بعرض المساعدة.",
    "considered": "أبدى استعداده للنظر في طلب المساعدة.",
    "refused": "رفض طلب المساعدة.",
    "distrusted": "تعامل مع عرض المساعدة بريبة.",
    "alarmed": "أبدى انزعاجًا من التهديد.",
}
SPEECH_KINDS = {
    "greeting": "تحية",
    "offer_help": "عرض مساعدة",
    "request_help": "طلب مساعدة",
    "threat": "تهديد",
}


def _reaction_label(value: Any) -> str:
    # Never invent an NPC's spoken words or convert a behavioral outcome to a quote.
    return REACTIONS.get(str(value), "رد فعل مسجل: " + str(value))


def _conversation_panel(conversations: Any) -> str:
    details = conversations.details if hasattr(conversations, "details") else {}
    recent = details.get("recent", ()) if isinstance(details, dict) else ()
    parts = ['<section class="card" id="conversations"><h2>محادثات كارلوس</h2>']
    if not recent:
        parts.append('<p class="muted">لم تتحدث مع أحد بعد. تحدث مع شخصية حاضرة لرؤية النتيجة.</p>')
    for entry in list(recent)[:4]:
        recipient = _person_name(entry.get("recipient_id"))
        words = str(entry.get("text", ""))
        kind = SPEECH_KINDS.get(str(entry.get("kind")), str(entry.get("kind")))
        reaction = _reaction_label(entry.get("reaction"))
        parts.extend([
            '<div class="conversation">',
            f'<h3>محادثة مع {_h(recipient)} · {_h(kind)}</h3>',
            f'<p><strong>قلت:</strong> «{_h(words)}»</p>',
            f'<p><strong>استجابة {_h(recipient)} المسجلة:</strong> {_h(reaction)}</p>',
            '</div>',
        ])
    parts.append('<p class="help">هذه استجابات سلوكية مسجلة فعلًا، '
                 'وليست جملًا منطوقة أو حوارات حرة اخترعها النظام.</p>')
    parts.append('</section>')
    return "".join(parts)


def _h(value: Any) -> str:
    return escape(str(value), quote=True)


def _known_place(key: Any) -> str:
    return LOCATION_NAMES.get(str(key), str(key))


def _person_name(key: Any, fallback: Any = None) -> str:
    key = str(key)
    return NPC_NAMES.get(key, str(fallback) if fallback else key)


def _num(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _button(csrf: str, command: str, caption: str, *, primary: bool = False) -> str:
    # Every player action is an explicit POST, with a working no-JS fallback.
    return (
        '<form method="post" action="/act">'
        f'<input type="hidden" name="csrf" value="{_h(csrf)}">'
        f'<input type="hidden" name="command" value="{_h(command)}">'
        f'<button type="submit" class="{"primary" if primary else "secondary"}">'
        f'{_h(caption)}</button></form>'
    )


def _bar(label: str, record: Any, *, color: str, note: str) -> str:
    if not isinstance(record, dict):
        return _unknown_bar(label, note)
    now, cap = _num(record.get("current")), _num(record.get("max"))
    if now is None or cap is None or cap == 0 or now > cap:
        return _unknown_bar(label, note)
    ratio = round(now / cap * 100)
    return (
        '<div class="stat-row">'
        f'<div class="stat-title"><strong>{_h(label)}</strong>'
        f'<span>{now} / {cap}</span></div>'
        f'<div class="bar {color}" role="progressbar" aria-label="{_h(label)}" '
        f'aria-valuemin="0" aria-valuemax="{cap}" aria-valuenow="{now}">'
        f'<span style="width:{ratio}%"></span></div>'
        f'<small>{_h(note)}</small></div>'
    )


def _unknown_bar(label: str, note: str) -> str:
    return (
        '<div class="stat-row">'
        f'<div class="stat-title"><strong>{_h(label)}</strong>'
        '<span class="muted">غير مُحاكى بعد</span></div>'
        f'<div class="bar unknown" aria-label="{_h(label)} غير مُفعّل"></div>'
        f'<small>{_h(note)}</small></div>'
    )


def _time_label(seconds: Any) -> str:
    n = _num(seconds)
    if n is None:
        return "لم تُسجّل مدة"
    if n < 60:
        return f"{n} ثانية"
    if n < 3600:
        return f"{n // 60} دقيقة"
    return f"{n // 3600} ساعة و{n % 3600 // 60} دقيقة"


def _status_panel(status: Any, needs: Any, supplies: Any) -> str:
    profile = status.details.get("profile", {}) if hasattr(status, "details") else {}
    vitals = profile.get("vitals", {}) if isinstance(profile, dict) else {}
    if not isinstance(vitals, dict):
        vitals = {}
    need = needs.details if hasattr(needs, "details") else {}
    if not isinstance(need, dict):
        need = {}
    owned = supplies.details.get("balances", {}) if hasattr(supplies, "details") else {}
    if not isinstance(owned, dict):
        owned = {}
    pieces = ['<section class="card" id="status"><h2>حالة كارلوس</h2><div class="stats">']
    pieces.append(_bar("الصحة (HP)", vitals.get("hp"), color="hp",
                       note="قيمة الشخصية الحقيقية في ملف الاختبار"))
    pieces.append(_bar("التحمّل (ST)", vitals.get("st"), color="st",
                       note="تحمّل RPG؛ ليس مقياس التعب الجسدي"))
    for key, label, note in (
        ("hunger", "الجوع", "يزداد مع مرور وقت العالم، ويخف بتناول طعامك."),
        ("fatigue", "التعب", "يزداد مع مرور الوقت خارج الراحة، ويخف عند اكتمالها."),
    ):
        value = _num(need.get(key))
        if value is not None and value <= 100:
            pieces.append(_bar(label, {"current": value, "max": 100},
                               color="need", note=note))
        else:
            pieces.append(_unknown_bar(
                label, f"لا توجد نسبة {label[2:]} لكارلوس في المحرك حاليًا"))
    last = need.get("seconds_since_last_meal")
    pieces.append(
        f'<p class="muted">آخر وجبة موثقة: '
        f'{_h("لم تُسجل وجبة بعد" if last is None else "منذ " + _time_label(last))}'
        '</p>'
    )
    pieces.append('</div><hr class="sep"><h3>ممتلكات كارلوس</h3><div class="balances">')
    for res in ("coin_copper", "food", "bread"):
        q = _num(owned.get(res))
        if q is not None:
            pieces.append(
                f'<span class="balance">{_h(RESOURCE_LABELS[res])}: {q}</span>'
            )
    pieces.append('</div></section>')
    return "".join(pieces)


def _scene_panel(scene: Any, csrf: str) -> str:
    details = scene.details
    now = scene.time
    pieces = [
        '<section class="card highlight" id="scene"><h2>المشهد الحالي</h2>',
        f'<div class="meta"><span class="pill">الزمن: {now} ثانية</span>',
        '<span class="pill">عالم اختبار مستقل</span></div>',
    ]
    if scene.status == "traveling":
        route = details["route_id"]
        remaining = _num(details.get("remaining_seconds")) or 0
        pieces.append('<p class="location">كارلوس في الطريق</p>')
        pieces.append(
            f'<p>المسار: <bdi class="code">{_h(route)}</bdi> · '
            f'متبقّي {_h(_time_label(remaining))}</p>'
        )
        pieces.append('<p class="muted">سيتحدد الوصول بعد مرور الزمن في المحرك.</p>')
        if remaining > 0:
            pieces.append(_button(csrf, "انتظر " + str(min(remaining, 21600)),
                                  f"أكمل الرحلة ({_time_label(min(remaining, 21600))})",
                                  primary=True))
        return "".join(pieces) + "</section>"

    if scene.status != "present":
        pieces.append('<p>لا تتوفر معلومات موقع قابلة للعرض الآن.</p></section>')
        return "".join(pieces)

    place = str(details["location_id"])
    name = _known_place(place)
    activity = details.get("activity", {})
    busy = isinstance(activity, dict) and activity.get("kind") in ("resting", "foraging")
    pieces.extend([
        f'<div class="location">الموقع: {_h(name)} ({_h(place)})</div>',
        '<p class="muted">ما تراه هنا فقط؛ لا نكشف مواقع الشخصيات البعيدة.</p>',
    ])
    if busy:
        resting = activity["kind"] == "resting"
        remaining = _num(activity.get("remaining_seconds")) or 0
        pieces.append(
            '<p class="notice">' + ("كارلوس يستريح" if resting else "كارلوس يبحث عن الطعام")
            + " · متبقّي " + _h(_time_label(remaining)) + ".</p>"
        )
        if remaining > 0:
            caption = "أكمل الراحة" if resting else "أكمل البحث"
            pieces.append(_button(
                csrf, "انتظر " + str(min(remaining, 21600)),
                caption + " (" + _time_label(min(remaining, 21600)) + ")", primary=True))
    pieces.append('<hr class="sep"><h3>الأشخاص الموجودون هنا</h3><div class="people">')
    activities = {
        str(a.get("actor_id")): a.get("activity")
        for a in details.get("activities", ())
        if isinstance(a, dict)
    }
    people = [p for p in details.get("occupants", ())
              if isinstance(p, dict) and str(p.get("id")) != "carlos"]
    if not people:
        pieces.append('<p class="muted">لا توجد شخصيات أخرى قرب كارلوس حاليًا.</p>')
    for p in people:
        person_id = str(p.get("id"))
        person = _person_name(person_id, p.get("name"))
        action = activities.get(person_id)
        action_label = ACTIVITY_LABELS.get(action, "نشاط ظاهر: " + str(action)) if action else "موجود هنا"
        pieces.append(
            '<div class="person"><span>'
            f'<strong>{_h(person)}</strong> '
            f'<span class="person-note">— {_h(action_label)}</span>'
            '</span>'
            + ("" if busy else _button(
                csrf, f"تحدث {person_id} تحية مرحبا", f"تحدث إلى {person}"))
            + '</div>'
        )
    pieces.append('</div><hr class="sep"><h3>الطرق من موقعك</h3><div class="routes">')
    exits = details.get("exits", ())
    if not exits:
        pieces.append('<p class="muted">لا يوجد طريق ظاهر من هنا.</p>')
    for road in exits:
        route = str(road.get("route_id"))
        destination = str(road.get("destination"))
        seconds = _num(road.get("seconds"))
        # Exact route IDs from this player's local, public scene.
        label = f"اذهب إلى {_known_place(destination)}"
        if seconds is not None:
            label += f" · {seconds} ثانية"
        pieces.append(
            '<div class="person"><span><bdi class="code">'
            + _h(route) + '</bdi></span>'
            + (f'<span class="muted">{_h(label)}</span>' if busy else
               _button(csrf, "اذهب " + route, label, primary=True))
            + '</div>'
        )
    pieces.append('</div></section>')
    return "".join(pieces)


def _offers_panel(offers: Any, supplies: Any, csrf: str) -> str:
    available = offers.details.get("offers", ()) if hasattr(offers, "details") else ()
    owned = supplies.details.get("balances", {}) if hasattr(supplies, "details") else {}
    wallet = _num(owned.get("coin_copper")) if isinstance(owned, dict) else None
    bits = ['<section class="card" id="offers"><h2>عروض البيع القريبة</h2>']
    if not available:
        bits.append(
            '<p class="notice">لا يوجد عرض قابل للتنفيذ هنا الآن. '
            'قد يتغير الوضع بعد مرور الوقت أو عند انتقالك إلى مكان آخر.</p>'
        )
    for offer in available:
        name = str(offer["offer_id"])
        price = _num(offer.get("unit_price"))
        qty = _num(offer.get("available"))
        res = str(offer["resource"])
        seller = _person_name(offer["seller_id"])
        payment = str(offer["payment_resource"])
        bits.extend([
            '<div class="offer"><div>',
            f'<strong>{_h(RESOURCE_LABELS.get(res, res))}</strong> '
            f'لدى {_h(seller)}'
            f' — {_h(qty if qty is not None else "؟")} متاح، '
            f'سعر الوحدة {_h(price if price is not None else "؟")} '
            f'{_h(RESOURCE_LABELS.get(payment, payment))}'
            '</div>'
        ])
        if (payment == "coin_copper" and price is not None
                and wallet is not None and qty is not None and qty > 0
                and (price == 0 or wallet >= price)):
            # This limit is only a UI convenience. Server/ledger recheck all
            # stock, owner, price and copper values when the user submits.
            limit = min(qty, 1000, wallet // price if price > 0 else qty)
            bits.extend([
                f'<form method="post" action="/act" class="buy-form" '
                f'data-unit-price="{price}">',
                f'<input type="hidden" name="csrf" value="{_h(csrf)}">',
                '<input type="hidden" name="action" value="buy">',
                f'<input type="hidden" name="offer_id" value="{_h(name)}">',
                f'<input type="hidden" name="unit_price" value="{price}">',
                '<label>الكمية',
                f'<input type="number" name="quantity" min="1" max="{limit}" '
                'value="1" required aria-label="كمية الشراء">',
                '</label>',
                f'<output aria-live="polite">الإجمالي: {price} نحاس</output>',
                '<button type="submit" class="primary">اشتر الكمية</button>',
                '</form>',
            ])
        else:
            bits.append('<span class="muted">الشراء غير متاح حاليًا بموارد كارلوس.</span>')
        bits.append('</div>')
    bits.append('</section>')
    return "".join(bits)


def _actions_panel(scene: Any, supplies: Any, local_food: Any, csrf: str,
                   needs: Any = None) -> str:
    bits = ['<section class="card" id="actions"><h2>ماذا تريد أن تفعل؟</h2>']
    bits.append('<p class="muted">اختر فعلًا واضحًا. لن يتحرك كارلوس تلقائيًا.</p>')
    activity = scene.details.get("activity", {})
    busy = isinstance(activity, dict) and activity.get("kind") in ("resting", "foraging")
    bits.append('<h3>الوقت والمراقبة</h3><div class="group">')
    choices = [
        ("مشهد", "حدّث المشهد"),
        ("انتظر 30", "انتظر 30 ثانية"), ("انتظر 90", "انتظر 90 ثانية"),
        ("مساعدة", "كيف ألعب؟"),
    ]
    if scene.status == "present" and not busy:
        choices.insert(1, ("انظر", "انظر حولك"))
    bits.extend(_button(csrf, command, label) for command, label in choices)
    bits.append('</div>')
    if scene.status == "present" and not busy:
        need = needs.details if hasattr(needs, "details") else {}
        if (isinstance(need, dict) and _num(need.get("fatigue")) is not None
                and _num(need.get("hunger")) is not None):
            bits.append('<h3>الراحة</h3><div class="group">')
            bits.append(_button(csrf, "استرح", "استرح 30 دقيقة"))
            bits.append('</div>')
        own = supplies.details.get("balances", {})
        food = _num(own.get("food")) if isinstance(own, dict) else None
        if food is not None and food > 0:
            bits.append('<h3>طعامك</h3><div class="group">')
            bits.append(_button(csrf, "كل", "كل وحدة من طعامك"))
            bits.append('</div>')
        if local_food.details.get("status") == "present":
            bits.append('<h3>الموارد الموجودة</h3><div class="group">')
            bits.append(_button(csrf, "ابحث", "ابحث عن طعام محلي"))
            bits.append('</div>')
    bits.extend([
        '<hr class="sep"><h3>أمر إضافي</h3>',
        '<p class="muted">يمكنك أيضًا كتابة أمر يدوي عند الحاجة. '
        'الأزرار أعلاه تنفذ الأفعال نفسها.</p>',
        '<form method="post" action="/act" class="command">',
        f'<input type="hidden" name="csrf" value="{_h(csrf)}">',
        '<input type="text" name="command" dir="auto" maxlength="1000" '
        'aria-label="أمر كارلوس" autocomplete="off" '
        'placeholder="مثال: تحدث salma تحية مرحبا" required>',
        '<button type="submit" class="primary">تنفيذ الأمر</button>',
        '</form></section>',
    ])
    return "".join(bits)


def friendly_result(result: Any, command: str, before: Any, after: Any) -> str:
    """Translate ONLY confirmed player gateway outcomes, not an invented story."""
    if isinstance(result, dict):
        return "ملخص معلومات كارلوس المسموح بعرضها متاح في الأمر «تسليم»."
    if isinstance(result, str):
        return result
    status = getattr(result, "status", "")
    details = getattr(result, "details", {})
    if status == "present":
        place = after.details.get("location_id") if after.status == "present" else None
        return ("أنت في " + _known_place(place) + ".") if place else "تم تحديث المشهد."
    if status == "traveling":
        remaining = details.get("remaining_seconds")
        return "كارلوس في الطريق. الوقت المتبقي: " + _time_label(remaining) + "."
    if command.startswith("wait "):
        elapsed = details.get("elapsed")
        if before.status == "traveling" and after.status == "present":
            return "وصل كارلوس إلى " + _known_place(after.details.get("location_id")) + "."
        if details.get("rest_result") == "completed":
            return "اكتملت راحة كارلوس. حُدّث التعب بعد الراحة الفعلية؛ راجع حالتك."
        if "rest_remaining_seconds" in details:
            return ("كارلوس يستريح. الوقت المتبقي: "
                    + _time_label(details["rest_remaining_seconds"]) + ".")
        if details.get("forage_result") == "collected":
            return "انتهى البحث، وجمع كارلوس وحدة طعام فعلية من المكان."
        if details.get("forage_result") == "depleted":
            return "انتهى البحث دون طعام؛ المصدر لم يعد متاحًا عند اكتماله."
        if status == "foraging":
            return "مرّ الوقت وما زال كارلوس يبحث عن الطعام."
        return "مرّ من الزمن " + _time_label(elapsed) + ". تواصل القرية نشاطها وفق المحرك."
    if status == "purchased":
        return (
            "تم شراء " + str(details.get("quantity", "?")) + " "
            + RESOURCE_LABELS.get(str(details.get("resource")), str(details.get("resource")))
            + " مقابل " + str(details.get("total_paid", "?")) + " من النقود الفعلية."
        )
    if status == "ate":
        return ("أكل كارلوس وحدة من طعامه. المتبقي: "
                + str(details.get("remaining_owned", "؟")) + ".")
    if status == "resting":
        return ("بدأ كارلوس الراحة في مكانه. الوقت المتبقي: "
                + _time_label(details.get("remaining_seconds")) + ".")
    if status == "interacted":
        who = _person_name(details.get("recipient_id"))
        return ("تحدث كارلوس مع " + who + ". رد فعله المسجل: "
                + _reaction_label(details.get("reaction"))
                + " اقرأ كلماتك كما سجلت في لوحة المحادثات.")
    if status == "gifted":
        return "سُلّمت الهدية إلى " + _person_name(details.get("recipient_id")) + " وسُجّل نقلها."
    if status == "foraging":
        return "بدأ كارلوس البحث عن طعام موجود في المكان. النتيجة تُحسم عند انتهاء الوقت."
    if status in ("rpg_status", "rpg_uninitialized"):
        return "راجع أشرطة الصحة والتحمّل في لوحة حالة كارلوس."
    if status == "supplies":
        return "ممتلكات كارلوس معروضة في اللوحة الجانبية."
    if status == "offers":
        return "عروض البيع المتاحة معروضة في لوحة السوق."
    if status == "needs":
        return "راجع الجوع والتعب وآخر وجبة في لوحة حالة كارلوس."
    if status == "ready":
        elapsed = details.get("elapsed")
        return "مرّ من الزمن " + _time_label(elapsed) + "."
    if status == "local_food":
        return "اطّلع على مصادر الطعام المتاحة في موقع كارلوس."
    # Do not pretend unsupported status is a confirmed positive result.
    return "استُخدم الأمر في المحرك. الحالة المسجلة: " + str(status)


def render_web02(gateway: Any, csrf: str, notice: str) -> bytes:
    """Read-only HTML presentation; every action remains an actual POST."""
    with gateway.store.read_consistent(gateway.world_id):
        return _render_web02_read(gateway, csrf, notice)


def _render_web02_read(gateway: Any, csrf: str, notice: str) -> bytes:
    scene = gateway.inspect()
    supplies = gateway.supplies()
    status = gateway.status()
    needs = gateway.needs()
    offers = gateway.offers()
    food = gateway.check_food()
    conversations = gateway.conversations()
    modeled_needs = (type(needs.details.get("hunger")) is int
                     and type(needs.details.get("fatigue")) is int)

    bits = [
        '<!doctype html><html lang="ar" dir="rtl"><head>',
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta name="referrer" content="same-origin">',
        '<title>كارلوس — القرية الحيّة</title><style>',
        STYLE, '</style><script src="/ui.js" defer></script></head><body><main>',
        '<header><h1>كارلوس — القرية الحيّة</h1>',
        '<p>مرحبًا بك في القرية. تحرّك بحرية، تحدث مع الناس، وتابع ما يحدث حولك.</p>',
        '<p class="muted">العالم مستقل وموارده محدودة؛ لا تفرض الواجهة تصرفات على السكان.</p>',
        '<small>تجربة محلية مؤقتة · WEB-03'
        + (' · NEEDS-01' if modeled_needs else '') + '</small></header>',
        '<div class="layout"><div class="column">',
        _scene_panel(scene, csrf),
        _offers_panel(offers, supplies, csrf),
        _actions_panel(scene, supplies, food, csrf, needs),
        _conversation_panel(conversations),
        '<section class="card"><h2>آخر نتيجة</h2>',
        f'<div class="result" role="status">{_h(notice)}</div></section>',
        '</div><div class="column">',
        _status_panel(status, needs, supplies),
        '<section class="card"><h2>كيف ألعب؟</h2>',
        '<p>اضغط على وجهة من «الطرق»، ثم استخدم الانتظار لإكمال الرحلة.</p>',
        '<p>تحدّث فقط إلى شخص موجود أمامك. لا تظهر عروض شراء إلا عند توافرها فعلًا.</p>',
        ('<p class="help">الجوع والتعب من حالة كارلوس الفعلية. '
         'الوقت يمر بأوامرك؛ اختر الراحة ثم أكمل مدتها.</p>' if modeled_needs else
         '<p class="help">التحمّل ST ليس مؤشر التعب، والجوع والتعب لم يُنفّذا لكارلوس بعد.</p>'),
        '</section></div></div>',
        '<p class="footer">هذه ليست القصة الأصلية، ولا يوجد حفظ دائم. '
        'لإنهاء الجلسة وحذف العالم المؤقت اضغط Ctrl+C في نافذة Python.</p>',
        '</main></body></html>',
    ]
    return "".join(bits).encode("utf-8")
