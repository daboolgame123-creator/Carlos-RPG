"""Real Rules63, Rules68 and Rules70 saves remain immutable and fail closed.

The source SHA is fetched via git archive into a disposable directory. No header
editing, event upcasting or migrations; the original writer verifies the file
again after the current reader rejects it. Frozen versions are explicit oracles.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from carlos_sim import SQLiteEventStore
from carlos_sim.store import UnsupportedVersion
from carlos_sim.domain import SCHEMA_VERSION, RULES_VERSION

FROZEN = [(63, 'b397f40d01a314197f2e22f26f1d27bf64eeed3f'),
          (68, '1e04e84e180b7ff6fa597aaed6e2605a3ca1dfd3'),
          (70, 'f6b124d74e422824df829a458be81e7519454ef9')]


@pytest.mark.parametrize('rules,sha', FROZEN)
def test_authentic_frozen_writer_refusal_and_original_reader(tmp_path, rules, sha):
    assert (SCHEMA_VERSION, RULES_VERSION) == (45, 71)
    repo = Path(__file__).resolve().parents[2]
    archive = subprocess.check_output(['git', 'archive', '--format=zip', sha, 'simulation'], cwd=repo)
    old = tmp_path / f'writer-{rules}'
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        z.extractall(old)
    path = tmp_path / 'old-world.sqlite'
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((
        str(old / 'simulation' / 'src'), str(old / 'simulation' / 'scenarios' / 'test_village'))))
    create = """
import json,sys
from carlos_sim import SQLiteEventStore
from play_physical_supply import seed_physical_supply,WORLD
with SQLiteEventStore(sys.argv[1]) as db:
    seed_physical_supply(db)
    s=db.verify(WORLD)
    assert len(s.npcs)==7 and s.revision>20
    db.snapshot(WORLD)
    print(json.dumps({'schema':s.schema_version,'rules':s.rules_version,'state':s.to_dict()}))
"""
    original = json.loads(subprocess.check_output([sys.executable, '-c', create, str(path)],
                                                 env=env, cwd=old, text=True, encoding='utf8'))
    assert (original['schema'], original['rules']) == (45, rules)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with SQLiteEventStore(path) as db:
        for read in (db.load, db.verify):
            with pytest.raises(UnsupportedVersion, match='schema/rules mismatch'):
                read(original['state']['world_id'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    verify = """
import json,sys
from carlos_sim import SQLiteEventStore
with SQLiteEventStore(sys.argv[1]) as db:
    print(json.dumps(db.verify(sys.argv[2]).to_dict()))
"""
    restored = json.loads(subprocess.check_output([sys.executable, '-c', verify, str(path),
                         original['state']['world_id']], env=env, cwd=old, text=True, encoding='utf8'))
    assert restored == original['state']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
