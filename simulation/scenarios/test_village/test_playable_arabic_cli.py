"""PLAYABLE AR-01: real Arabic player input is only a UI alias for PLAY31."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

from carlos_sim import SQLiteEventStore, TimeEngine
from carlos_sim.store import InvalidEvent
from play_physical_supply import WORLD
from play_village_ar import HELP_AR, lines_ar, translate_command
from play_village_local import create_session, execute


@pytest.mark.parametrize(("text", "expected"), [
    ("المشهد", ["scene"]),
    ("انظر", ["look"]),
    ("الحالة", ["status"]),
    ("المخزون", ["supplies"]),
    ("الاحتياجات", ["needs"]),
    ("الذاكرة", ["remember"]),
    ("العروض", ["offers"]),
    ("المهام", ["quests"]),
    ("اذهب home-market", ["move", "home-market"]),
    ("انتظر 90", ["wait", "90"]),
    ("تحدث salma تحية صباح الخير", ["talk", "salma", "greeting", "صباح", "الخير"]),
    ("تحدث salma طلب_مساعدة 'هل يوجد خبز؟'", ["talk", "salma", "request_help", "هل يوجد خبز؟"]),
    ("اشتر market-quote 1 2", ["buy", "market-quote", "1", "2"]),
    ("كل", ["eat"]),
    ("اعط salma خبز 1", ["give", "salma", "food", "1"]),
    ("أعط salma نحاس 2", ["give", "salma", "coin_copper", "2"]),
    ("ابحث", ["forage"]),
    ("اطلب_طعام salma market", ["askfood", "salma", "market"]),
    ("اقبل quest-1", ["accept", "quest-1"]),
    ("استلم quest-1", ["claim", "quest-1"]),
    ("تسليم", ["handoff"]),
    ("مساعدة", ["help"]),
    ("خروج", ["quit"]),
    ("scene", ["scene"]),
    ("move home-market", ["move", "home-market"]),
])
def test_arabic_commands_translate_only_the_explicit_player_intent(text, expected):
    assert shlex.split(translate_command(text)) == expected


@pytest.mark.parametrize("input_text", [
    "مجهول", "Teleport home-market", "تحدث 'نص دون إغلاق",
])
def test_unknown_or_malformed_commands_fail_closed(input_text):
    with pytest.raises(ValueError):
        translate_command(input_text)


def test_real_arabic_walk_is_same_world_and_events_as_original_english(tmp_path):
    with (SQLiteEventStore(tmp_path / "ar.sqlite") as arabic,
          SQLiteEventStore(tmp_path / "en.sqlite") as english):
        ar_clock, en_clock = TimeEngine(arabic), TimeEngine(english)
        ar, en = create_session(arabic, ar_clock), create_session(english, en_clock)
        try:
            sequence = [
                ("المشهد", "scene"),
                ("اذهب home-market", "move home-market"),
                ("انتظر 89", "wait 89"),
                ("المشهد", "scene"),
                ("انتظر 1", "wait 1"),
                ("المشهد", "scene"),
                ("المخزون", "supplies"),
                ("العروض", "offers"),
                ("الذاكرة", "remember"),
            ]
            for serial, (ar_command, en_command) in enumerate(sequence, 1):
                actual = execute(ar, translate_command(ar_command), serial)
                reference = execute(en, en_command, serial)
                assert actual == reference
                assert arabic.verify(WORLD).to_dict() == english.verify(WORLD).to_dict()
            assert execute(ar, translate_command("المشهد"), 20).details["location_id"] == "market"
            assert "الموقع:" in "\n".join(lines_ar(ar.inspect()))
        finally:
            ar_clock.close_session(WORLD)
            en_clock.close_session(WORLD)


def test_read_only_arabic_views_do_not_advance_or_expose_private_world_state(tmp_path):
    with SQLiteEventStore(tmp_path / "local.sqlite") as db:
        clock = TimeEngine(db)
        gateway = create_session(db, clock)
        try:
            before = db.verify(WORLD).to_dict()
            presentation = "\n".join(lines_ar(execute(
                gateway, translate_command("المشهد"), 1
            )))
            assert "الموقع:" in presentation
            assert "home-market" in presentation
            assert "الأشخاص الحاضرون:" in presentation
            inventory = "\n".join(lines_ar(execute(
                gateway, translate_command("المخزون"), 2
            )))
            assert "ممتلكات كارلوس" in inventory
            assert "نحاس: 10" in inventory
            handoff = execute(gateway, translate_command("تسليم"), 3)
            assert handoff["format"] == "carlos-player-handoff-v1"
            assert handoff["canonical_story"] is False
            assert "npcs" not in handoff and "resources" not in handoff
            output = lines_ar(handoff)[0]
            assert '"format": "carlos-player-handoff-v1"' in output
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


@pytest.mark.parametrize("command", [
    "انتظر 21601", "انتظر 0", "اذهب well-farm",
    "اشتر nonexistent-offer 1 2", "كل",
])
def test_invalid_arabic_input_does_not_change_persistent_events(tmp_path, command):
    with SQLiteEventStore(tmp_path / "denied.sqlite") as db:
        clock = TimeEngine(db)
        gateway = create_session(db, clock)
        try:
            before = db.verify(WORLD).to_dict()
            with pytest.raises((ValueError, PermissionError, InvalidEvent)):
                execute(gateway, translate_command(command), 1)
            assert db.verify(WORLD).to_dict() == before
        finally:
            clock.close_session(WORLD)


def test_arabic_cli_subprocess_executes_a_real_player_walk_and_exits(tmp_path):
    script = Path(__file__).with_name("play_village_ar.py")
    root = script.parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), str(script.parent)]
    )
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(script)],
        input="المشهد\nالحالة\nاذهب home-market\nانتظر 90\nالمشهد\nخروج\n",
        text=True, encoding="utf-8", capture_output=True,
        cwd=str(root), env=env, check=False, timeout=90,
    )
    assert result.returncode == 0, result.stderr + result.stdout[-1800:]
    assert "قرية مستقلة قابلة للعب بالعربية" in result.stdout
    assert "home-market" in result.stdout
    assert "الموقع:" in result.stdout and "(market)" in result.stdout
    assert "حُذفت بيانات التجربة المؤقتة" in result.stdout
    assert "رُفض الأمر:" not in result.stdout


def test_arabic_help_does_not_claim_automated_rescue_or_permanent_save():
    assert "مساعدة" in HELP_AR
    assert "تسليم" in HELP_AR
    assert "معرّفات" in HELP_AR
