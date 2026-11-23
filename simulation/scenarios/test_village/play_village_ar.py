"""Arabic player-facing CLI for the existing finite, offline PLAY-31 village.

Presentation/command aliases only. The existing PlayerGateway executes every
action, enforces ownership and local knowledge, and owns event persistence.
The underlying SQLite test world is temporary and is destroyed on exit.
No narrator/LLM is allowed to assert or modify world state.
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent, RevisionConflict, DuplicateCommand
from carlos_sim.time_engine import AdvanceLimitExceeded, SessionClosed
from play_physical_supply import WORLD
from play_village_local import HELP, create_session, execute

# These are aliases for commands the original player gateway ALREADY supports.
# IDs remain explicit, original and case-sensitive (e.g. "home-market").
ALIASES = {
    "المشهد": "scene", "مشهد": "scene", "المكان": "scene", "انظر": "look",
    "الذاكرة": "remember", "تذكر": "remember",
    "الحالة": "status", "المخزون": "supplies", "الاحتياجات": "needs",
    "العروض": "offers", "الطعام": "food", "المشتريات": "purchases",
    "الوجبات": "meals", "الهدايا": "gifts", "المحادثات": "conversations",
    "المهام": "quests", "تسليم": "handoff",
    "اذهب": "move", "تحرك": "move", "انتظر": "wait",
    "تحدث": "talk", "اشتر": "buy", "كل": "eat", "كُل": "eat",
    "اعط": "give", "أعط": "give", "ابحث": "forage",
    "اطلب_طعام": "askfood", "اقبل": "accept", "استلم": "claim",
    "مساعدة": "help", "خروج": "quit", "اخرج": "quit",
}
KINDS = {
    "تحية": "greeting", "عرض_مساعدة": "offer_help",
    "طلب_مساعدة": "request_help", "تهديد": "threat",
}
RESOURCES = {"خبز": "food", "طعام": "food", "نحاس": "coin_copper"}
ORIGINAL = {
    "scene", "look", "remember", "status", "supplies", "needs",
    "offers", "food", "purchases", "meals", "gifts", "conversations",
    "quests", "handoff", "move", "wait", "talk", "buy", "eat",
    "give", "forage", "askfood", "accept", "claim", "help", "quit", "exit",
}
KEYS = {
    "location_id": "معرف_الموقع", "location_name": "اسم_الموقع",
    "occupants": "الحاضرون", "exits": "الطرق", "route_id": "معرف_الطريق",
    "destination": "الوجهة", "seconds": "الثواني", "remaining_seconds": "الوقت_المتبقي",
    "activities": "أنشطة_مرئية", "balances": "الممتلكات", "coin_copper": "نحاس",
    "food": "طعام", "resource": "المورد", "quantity": "الكمية",
    "offers": "العروض", "offer_id": "معرف_العرض", "seller_id": "البائع",
    "unit_price": "سعر_الوحدة", "available": "الكمية_المتاحة",
    "payment_resource": "عملة_الدفع", "total_paid": "الإجمالي_المدفوع",
    "recipient_id": "المستلم", "total": "المجموع", "recent": "الأحدث",
    "profile": "الملف", "configured": "مُهيأ", "quest_id": "معرف_المهمة",
}
LOCATION_NAMES = {
    "home": "المنزل", "market": "السوق", "bakery": "المخبز",
    "farm": "الحقل", "well": "البئر",
}
NPC_NAMES = {
    "carlos": "كارلوس", "basim": "باسم", "salma": "سلمى",
    "adel": "عادل", "nora": "نورا", "huda": "هدى",
    "omar": "عمر", "layla": "ليلى",
}
STATUS = {
    "present": "المشهد الحالي", "traveling": "في الطريق",
    "rpg_status": "حالة كارلوس", "supplies": "ممتلكات كارلوس",
    "offers": "عروض البيع المحلية", "purchased": "شراء موثق",
    "gifted": "هدية موثقة", "foraging": "بحث عن طعام",
    "needs": "احتياجات كارلوس", "memory": "ذكريات كارلوس",
    "quests": "المهام", "quest_accepted": "مهمة مقبولة",
    "quest_reward_claimed": "مكافأة مستلمة",
}

HELP_AR = """الأوامر العربية (ويمكنك استخدام الأوامر الإنجليزية القديمة):
  المشهد، انظر، الحالة، المخزون، الاحتياجات، الذاكرة، العروض، المهام
  الطعام، المشتريات، الوجبات، الهدايا، المحادثات
  اذهب home-market          بدء رحلة على طريق معروف (لا انتقال فوري)
  انتظر 90                   تمرير 90 ثانية من وقت العالم
  تحدث salma تحية مرحبا      حوار مع شخصية موجودة في موقعك
  اشتر <معرف_العرض> 1 2       شراء وحدة بالسعر الفعلي المعروض
  كل                         أكل طعام يملكه كارلوس بالفعل
  اعط salma food 1           منح مورد مملوك لشخصية قريبة
  ابحث                       محاولة جمع طعام محلي موجود
  اطلب_طعام <npc-id> <site-id>
  اقبل <quest-id>، استلم <quest-id>
  تسليم                      سجل كارلوس المسموح نسخه فقط بصيغة JSON
  مساعدة، خروج
مهم: معرّفات الطرق والشخصيات والعروض تُكتب كما تظهر؛ لا تخترع معرّفًا.
"""

def translate_command(line: str) -> str:
    """Parse one explicit Arabic/English instruction without changing semantics.

    shlex.join safely re-quotes free-text speech. No NPC command is inferred.
    Invalid commands must be rejected by the same gateway as English commands.
    """
    words = shlex.split(line)
    if not words:
        return ""
    verb = ALIASES.get(words[0], words[0])
    if verb not in ORIGINAL:
        raise ValueError("أمر غير معروف؛ اكتب مساعدة لعرض الأوامر")
    args = words[1:]
    if verb == "talk" and len(args) >= 2:
        args[1] = KINDS.get(args[1], args[1])
    if verb == "give" and len(args) == 3:
        args[1] = RESOURCES.get(args[1], args[1])
    if verb == "exit":
        verb = "quit"
    return shlex.join([verb, *args])


def localize_keys(value):
    """Only relabel keys from already player-scoped projections, never query state."""
    if isinstance(value, dict):
        return {KEYS.get(k, k): localize_keys(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [localize_keys(x) for x in value]
    return value


def lines_ar(result) -> list[str]:
    if result is None:
        return []
    if isinstance(result, str):
        if result == "quit":
            return ["انتهت الجلسة."]
        return [HELP_AR if result == HELP else result]
    if isinstance(result, dict):
        # The handoff's schema must stay byte-field compatible with consumers.
        # It already contains ONLY the player-authorized public projection.
        return [json.dumps(result, ensure_ascii=False, sort_keys=True)]
    status = STATUS.get(result.status, result.status)
    details = result.details
    lines = [f"{status} | الزمن: {result.time} ثانية"]
    if result.status == "present":
        location_id = details["location_id"]
        place_name = LOCATION_NAMES.get(location_id, details["location_name"])
        lines.append(f"الموقع: {place_name} ({location_id})")
        people = details["occupants"]
        lines.append("الأشخاص الحاضرون: " + (
            "، ".join(
                f"{NPC_NAMES.get(p['id'], p['name'])} ({p['id']})"
                for p in people
            ) if people
            else "لا أحد"
        ))
        exits = details["exits"]
        lines.append("الطرق المعروفة من هنا: " + (
            "، ".join(
                f"{p['route_id']} إلى "
                f"{LOCATION_NAMES.get(p['destination'], p['destination'])} "
                f"({p['seconds']} ثانية)"
                for p in exits
            ) if exits else "لا توجد"
        ))
        if details["activities"]:
            lines.append("أنشطة مرئية: " + json.dumps(
                localize_keys(details["activities"]), ensure_ascii=False
            ))
    elif result.status == "traveling":
        lines.append(
            f"الطريق: {details['route_id']} | المتبقي: {details['remaining_seconds']} ثانية"
        )
    elif result.status == "supplies":
        balances = details["balances"]
        lines.append("الممتلكات: " + (
            "، ".join(f"{KEYS.get(k, k)}: {v}" for k, v in balances.items())
            if balances else "لا توجد ممتلكات مسجلة"
        ))
    else:
        lines.append(json.dumps(localize_keys(details), ensure_ascii=False, sort_keys=True))
    return lines


def render_ar(result) -> None:
    for line in lines_ar(result):
        print(line)


def configure_windows_console_utf8() -> None:
    """Use UTF-8 for Arabic on a real Windows console, never a redirected pipe.

    This fixes the classic Windows PowerShell OEM-code-page mismatch without
    changing the player's commands or the underlying world. Other consoles,
    unsupported Windows APIs and redirected test processes remain untouched.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if kernel32.GetConsoleWindow():
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
            for stream in (sys.stdin, sys.stdout, sys.stderr):
                if stream.isatty() and hasattr(stream, "reconfigure"):
                    stream.reconfigure(encoding="utf-8", errors="replace")
    except (OSError, AttributeError, ValueError):
        # Do not prevent playable startup on unusual terminal hosts.
        pass


def main() -> None:
    configure_windows_console_utf8()
    print("كارلوس — قرية مستقلة قابلة للعب بالعربية (تجربة مؤقتة)")
    print("7 شخصيات مستقلة، طرق حقيقية، موارد محدودة. لا يوجد حفظ دائم أو اتصال بالإنترنت.")
    print("هذه ليست القصة الأصلية. اكتب «مساعدة» للأوامر.")
    with TemporaryDirectory(prefix="carlos-play-ar-") as folder:
        with SQLiteEventStore(Path(folder) / "demo.sqlite") as db:
            clock = TimeEngine(db)
            gateway = create_session(db, clock)
            serial = 0
            try:
                render_ar(gateway.inspect())
                while True:
                    try:
                        line = input("كارلوس> ")
                    except (EOFError, KeyboardInterrupt):
                        break
                    if not line.strip():
                        continue
                    try:
                        cmd = translate_command(line)
                        if cmd == "quit":
                            break
                        if cmd == "help":
                            print(HELP_AR)
                            continue
                        serial += 1
                        render_ar(execute(gateway, cmd, serial))
                    except (ValueError, InvalidEvent, RevisionConflict,
                            DuplicateCommand, AdvanceLimitExceeded,
                            SessionClosed, PermissionError) as error:
                        print(f"رُفض الأمر: {error}")
            finally:
                clock.close_session(WORLD)
    print("انتهت الجلسة، وحُذفت بيانات التجربة المؤقتة. لم تتغير قصة كارلوس الأصلية.")


if __name__ == "__main__":
    main()
