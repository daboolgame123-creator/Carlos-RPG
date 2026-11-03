"""SQLite transactional event store with verified snapshots and idempotent commands."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Sequence
from .domain import WorldState, DomainEvent, apply_event, canonical, canonical_hash, SCHEMA_VERSION, RULES_VERSION

class RevisionConflict(Exception): pass
class InvalidEvent(Exception): pass
class IntegrityError(Exception): pass
class UnsupportedVersion(Exception): pass
class DuplicateCommand(Exception): pass

class SQLiteEventStore:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS worlds (
                id TEXT PRIMARY KEY, revision INTEGER NOT NULL, sim_time INTEGER NOT NULL,
                schema_version INTEGER NOT NULL, rules_version INTEGER NOT NULL,
                initial_state TEXT NOT NULL, initial_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS commands (
                world_id TEXT NOT NULL REFERENCES worlds(id), command_id TEXT NOT NULL,
                request_hash TEXT NOT NULL, first_revision INTEGER NOT NULL,
                last_revision INTEGER NOT NULL, bootstrap INTEGER NOT NULL DEFAULT 0,
                clock_authorized INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(world_id, command_id));
            CREATE TABLE IF NOT EXISTS events (
                world_id TEXT NOT NULL REFERENCES worlds(id), seq INTEGER NOT NULL,
                command_id TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
                PRIMARY KEY(world_id,seq), FOREIGN KEY(world_id,command_id)
                    REFERENCES commands(world_id,command_id));
            CREATE TABLE IF NOT EXISTS snapshots (
                world_id TEXT NOT NULL REFERENCES worlds(id), revision INTEGER NOT NULL,
                state TEXT NOT NULL, hash TEXT NOT NULL,
                PRIMARY KEY(world_id,revision));
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def create_world(self, world_id: str) -> WorldState:
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world ID required")
        state = WorldState(world_id)
        d = state.to_dict()
        payload = canonical(d)
        with self.db:
            self.db.execute("INSERT INTO worlds VALUES(?,?,?,?,?,?,?)", (world_id, 0, 0, SCHEMA_VERSION, RULES_VERSION, payload, canonical_hash(d)))
        return state

    def _world_row(self, world_id: str):
        row = self.db.execute("SELECT revision,sim_time,schema_version,rules_version,initial_state,initial_hash FROM worlds WHERE id=?", (world_id,)).fetchone()
        if row is None: raise KeyError(world_id)
        if row[2] != SCHEMA_VERSION or row[3] != RULES_VERSION: raise UnsupportedVersion("world schema/rules mismatch")
        return row

    def _decode_state(self, payload: str, expected_hash: str) -> WorldState:
        try:
            d = json.loads(payload)
            if canonical_hash(d) != expected_hash:
                raise IntegrityError("state hash mismatch")
            return WorldState.from_dict(d)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise IntegrityError("invalid stored state") from exc

    def load(self, world_id: str, *, use_snapshot: bool = True) -> WorldState:
        row = self._world_row(world_id)
        state = self._decode_state(row[4], row[5])
        if state.world_id != world_id or state.revision != 0:
            raise IntegrityError("invalid initial state")
        if use_snapshot:
            snap = self.db.execute("SELECT revision,state,hash FROM snapshots WHERE world_id=? ORDER BY revision DESC LIMIT 1",(world_id,)).fetchone()
            if snap:
                state = self._decode_state(snap[1], snap[2])
                if state.world_id != world_id or state.revision != snap[0] or state.revision > row[0]:
                    raise IntegrityError("snapshot identity/revision mismatch")
        for seq, raw, stored_hash in self.db.execute("SELECT seq,payload,hash FROM events WHERE world_id=? AND seq>? ORDER BY seq", (world_id,state.revision)):
            if seq != state.revision + 1:
                raise IntegrityError("event sequence gap")
            try:
                raw_data = json.loads(raw)
                if canonical_hash(raw_data) != stored_hash:
                    raise IntegrityError("event hash mismatch")
                command = self.db.execute("SELECT c.request_hash, c.bootstrap FROM events e JOIN commands c ON e.world_id=c.world_id AND e.command_id=c.command_id WHERE e.world_id=? AND e.seq=?", (world_id, seq)).fetchone()
                if command is None:
                    raise IntegrityError("event command is missing")
                state = apply_event(state,DomainEvent.from_dict(raw_data),bootstrap=bool(command[1]))
            except (ValueError, TypeError) as exc:
                raise IntegrityError(f"corrupt event {seq}") from exc
        if state.revision != row[0] or state.time != row[1]:
            raise IntegrityError("world head mismatch")
        return state

    def append(self, world_id: str, command_id: str, expected_revision: int, events: Sequence[DomainEvent], *, bootstrap: bool = False, clock_authorized: bool = False) -> WorldState:
        """Commit events atomically. bootstrap is a trusted setup-only capability.

        Never expose this method or its bootstrap switch to untrusted callers.
        A future application authorization layer must guard the capability.
        """
        if not isinstance(command_id,str) or not command_id or type(expected_revision) is not int or expected_revision < 0 or not events:
            raise ValueError("command ID, expected revision and nonempty event batch required")
        if type(bootstrap) is not bool or type(clock_authorized) is not bool:
            raise ValueError("capability flags must be boolean")
        if not clock_authorized and any(e.event_type in ("TimeAdvanced", "ScheduledEventFired") for e in events):
            raise InvalidEvent("clock advancement/firing requires a trusted clock capability")
        serialized = [e.to_dict() for e in events]
        request_hash = canonical_hash({"events":serialized,"expected_revision":expected_revision,"bootstrap":bootstrap,"clock_authorized":clock_authorized})
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT request_hash FROM commands WHERE world_id=? AND command_id=?",(world_id,command_id)).fetchone()
            if existing:
                if existing[0] == request_hash:
                    self.db.execute("COMMIT")
                    return self.load(world_id)
                raise DuplicateCommand("command ID was already used with different data")
            state = self.load(world_id)
            if state.revision != expected_revision:
                raise RevisionConflict(f"expected {expected_revision}, current {state.revision}")
            first = state.revision + 1
            for e in events:
                try:
                    state = apply_event(state,e,bootstrap=bootstrap)
                except (ValueError,TypeError) as exc:
                    raise InvalidEvent(str(exc)) from exc
            self.db.execute("INSERT INTO commands VALUES(?,?,?,?,?,?,?)",(world_id,command_id,request_hash,first,state.revision,int(bootstrap),int(clock_authorized)))
            for idx, data in enumerate(serialized,start=first):
                self.db.execute("INSERT INTO events VALUES(?,?,?,?,?)",(world_id,idx,command_id,canonical(data),canonical_hash(data)))
            self.db.execute("UPDATE worlds SET revision=?,sim_time=? WHERE id=? AND revision=?",(state.revision,state.time,world_id,expected_revision))
            if self.db.execute("SELECT changes()").fetchone()[0] != 1:
                raise RevisionConflict("concurrent update")
            self.db.execute("COMMIT")
            return state
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def snapshot(self, world_id: str) -> WorldState:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            state = self.load(world_id)
            d = state.to_dict()
            self.db.execute("INSERT OR REPLACE INTO snapshots VALUES(?,?,?,?)", (world_id,state.revision,canonical(d),canonical_hash(d)))
            self.db.execute("COMMIT")
            return state
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def verify(self, world_id: str) -> WorldState:
        """Rebuild from genesis and compare to the latest snapshot-based projection."""
        full = self.load(world_id,use_snapshot=False)
        quick = self.load(world_id)
        if canonical_hash(full.to_dict()) != canonical_hash(quick.to_dict()):
            raise IntegrityError("snapshot and full replay disagree")
        return full

    def player_view(self, world_id: str) -> dict:
        """Safe-by-default: do not publish entities, resources or hidden state.

        Dedicated perception/visibility logic is deferred to a later phase.
        """
        state = self.load(world_id)
        return {"world_id": state.world_id, "time": state.time, "revision":state.revision}
