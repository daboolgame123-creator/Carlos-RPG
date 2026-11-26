"""Reject an authentic WEB-03 save without changing its bytes or old meaning.

Run with the current runtime on PYTHONPATH and a separate checkout at the
frozen predecessor SHA. All databases are disposable; neither checkout nor
any user save is modified. This verifies rejection, never migration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from carlos_sim import SQLiteEventStore, UnsupportedVersion
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION

PREDECESSOR_SHA = "985977b42fb41e4f56e751c70ef8cd3495c7f503"

CREATE_OLD_SAVE = """
import json, sys
from carlos_sim import SQLiteEventStore, TimeEngine
from play_physical_supply import WORLD
from play_village_local import create_session, execute
with SQLiteEventStore(sys.argv[1]) as db:
    clock = TimeEngine(db)
    player = create_session(db, clock)
    execute(player, 'move home-market', 1)
    execute(player, 'wait 120', 2)
    quote = next(q for q in player.offers().details['offers'] if q['resource'] == 'food')
    execute(player, 'buy ' + quote['offer_id'] + ' 1 ' + str(quote['unit_price']), 3)
    execute(player, 'eat', 4)
    assert player.needs().details['hunger'] == 'not_modeled'
    execute(player, 'move bakery-market', 5)
    execute(player, 'wait 10', 6)
    state = db.snapshot(WORLD)
    assert len(state.npcs) == 7 and state.time == 130
    assert state.resources['carlos']['food'] == 0
    assert state.resources['carlos']['coin_copper'] == 8
    assert player.inspect().status == 'traveling'
    assert player.meals().details['total'] == 1
    assert db.verify(WORLD).to_dict() == state.to_dict()
    clock.close_session(WORLD)
    print(json.dumps(state.to_dict(), ensure_ascii=False))
"""

READ_OLD_SAVE = """
import json, sys
from carlos_sim import SQLiteEventStore
with SQLiteEventStore(sys.argv[1]) as db:
    assert db.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert db.db.execute('PRAGMA foreign_key_check').fetchall() == []
    print(json.dumps(db.verify(sys.argv[2]).to_dict(), ensure_ascii=False))
"""


def verify(predecessor: Path) -> dict:
    predecessor = predecessor.resolve(strict=True)
    actual_sha = subprocess.check_output(
        ["git", "-C", str(predecessor), "rev-parse", "HEAD"],
        text=True, encoding="utf-8",
    ).strip()
    if actual_sha != PREDECESSOR_SHA:
        raise ValueError("predecessor checkout must be the exact frozen WEB-03 SHA")
    # A matching HEAD with modified source would not be an authentic writer.
    source_changes = subprocess.check_output(
        ["git", "-C", str(predecessor), "status", "--porcelain", "--", "simulation"],
        text=True, encoding="utf-8",
    ).strip()
    if source_changes:
        raise ValueError("predecessor simulation source must be unchanged")
    if (SCHEMA_VERSION, RULES_VERSION) != (46, 72):
        raise AssertionError("candidate must use the explicit player-needs version")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join((
        str(predecessor / "simulation" / "src"),
        str(predecessor / "simulation" / "scenarios" / "test_village"),
    ))
    env["PYTHONIOENCODING"] = "utf-8"
    with TemporaryDirectory(prefix="carlos-web03-compatibility-") as folder:
        path = Path(folder) / "authentic-web03.sqlite"
        original = json.loads(subprocess.check_output(
            [sys.executable, "-c", CREATE_OLD_SAVE, str(path)],
            cwd=predecessor, env=env, text=True, encoding="utf-8",
        ))
        assert (original["schema_version"], original["rules_version"]) == (45, 71)
        assert "player_needs" not in original
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        with SQLiteEventStore(path) as db:
            for reader in (db.load, db.verify):
                try:
                    reader(original["world_id"])
                except UnsupportedVersion:
                    pass
                else:
                    raise AssertionError("current runtime silently accepted the old save")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        reopened = json.loads(subprocess.check_output(
            [sys.executable, "-c", READ_OLD_SAVE, str(path), original["world_id"]],
            cwd=predecessor, env=env, text=True, encoding="utf-8",
        ))
        assert reopened == original
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before
        return {
            "status": "AUTHENTIC_WEB03_SAVE_REJECTED_UNCHANGED",
            "predecessor_sha": actual_sha,
            "source_version": [45, 71], "candidate_version": [46, 72],
            "source_sha256": before,
            "source_time": original["time"],
            "source_revision": original["revision"],
            "genuine_player_meals": 1,
            "source_travel_pending": True,
            "original_reader_reopened": True,
            "migration": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predecessor", type=Path, required=True,
                        help="unchanged checkout of frozen WEB-03 repository root")
    args = parser.parse_args()
    print(json.dumps(verify(args.predecessor), sort_keys=True))


if __name__ == "__main__":
    main()
