"""01-Z: restartable, trusted, *disposable-test* player session.

Does not authorize production games while P0 independent review is OPEN.
Use explicit request IDs, no silent world recreation or schema conversion.
"""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
from typing import Callable
import os
import sqlite3

from .backup import create_backup_bundle, _require_new_path
from .domain import SCHEMA_VERSION, RULES_VERSION
from .player_gateway import PlayerGateway
from .store import SQLiteEventStore
from .time_engine import TimeEngine


def _test_only(enabled: bool) -> None:
    if enabled is not True:
        raise PermissionError(
            'saved test worlds are experimental until P0 is independently reviewed')


def _preflight_existing(path: Path, world_id: str) -> None:
    """Read-only preflight: fail before SQLiteEventStore can create tables."""
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError('existing regular SQLite world file required')
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro',
                                      uri=True)) as connection:
            if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('SQLite integrity check failed')
            names = {r[0] for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'worlds', 'commands', 'events', 'snapshots'} <= names:
                raise ValueError('incomplete SQLite event store')
            row = connection.execute(
                'SELECT schema_version, rules_version FROM worlds WHERE id=?',
                (world_id,)).fetchone()
            if row != (SCHEMA_VERSION, RULES_VERSION):
                raise ValueError('missing world or unsupported version; no migration')
            columns = {r[1] for r in connection.execute('PRAGMA table_info(commands)')}
            if 'rpg_authorized' not in columns:
                raise ValueError('incompatible command ledger')
    except sqlite3.DatabaseError as exc:
        raise ValueError('cannot safely read saved world') from exc


class ResumableTestSession:
    """One process-local session on a verified test DB; no automatic game time."""

    def __init__(self, store: SQLiteEventStore, world_id: str, player_id: str):
        state = store.verify(world_id)
        who = state.entities.get(player_id)
        if who is None or who['controller'] != 'player':
            raise PermissionError('only an existing player can resume this world')
        self.store = store
        self.world_id = world_id
        self.player_id = player_id
        self.clock = TimeEngine(store)
        self.clock.open_session(world_id)
        self.gateway = PlayerGateway(
            store, self.clock, world_id=world_id, player_id=player_id)
        self._closed = False

    @classmethod
    def create(cls, path: str | Path, world_id: str, player_id: str,
               setup: Callable[[SQLiteEventStore], None], *,
               disposable_test: bool = False) -> 'ResumableTestSession':
        _test_only(disposable_test)
        dest = Path(path)
        _require_new_path(dest)
        if not callable(setup):
            raise ValueError('explicit trusted setup callback required')
        # Only the caller's fixture creates entities and player RPG facts.
        store = SQLiteEventStore(dest)
        try:
            setup(store)
            session = cls(store, world_id, player_id)
            return session
        except BaseException:
            store.close()
            # This path did not exist before this call. No existing save removed.
            dest.unlink(missing_ok=True)
            raise

    @classmethod
    def resume(cls, path: str | Path, world_id: str, player_id: str, *,
               disposable_test: bool = False) -> 'ResumableTestSession':
        _test_only(disposable_test)
        dest = Path(path)
        _preflight_existing(dest, world_id)
        store = SQLiteEventStore(dest)
        try:
            return cls(store, world_id, player_id)
        except BaseException:
            store.close()
            raise

    def _require_open(self) -> None:
        if self._closed:
            raise PermissionError('play session was closed')

    def bind_gateway(self, gateway: PlayerGateway) -> None:
        """Use a trusted local player gateway with this exact saved session.

        Enables an opt-in autonomous simulation policy for disposable test
        play, including after resume. No event, tick or checkpoint is created
        by binding. This is NOT an HTTP/client capability grant.
        """
        self._require_open()
        if (type(gateway) is not PlayerGateway
                or gateway.store is not self.store
                or gateway.clock is not self.clock
                or gateway.world_id != self.world_id
                or gateway.player_id != self.player_id):
            raise ValueError("gateway must belong to this exact player test session")
        self.gateway = gateway

    def view(self) -> dict:
        """Only safe-by-construction projections for the bound human player."""
        self._require_open()
        return {
            'scene': self.gateway.inspect(),
            'status': self.gateway.status(),
            'memory': self.gateway.recall(),
        }

    def handoff(self) -> dict[str, object]:
        """Copyable, player-only view for offline narration; never a raw save."""
        self._require_open()
        from .player_handoff import player_handoff
        return player_handoff(self.gateway)

    def checkpoint(self, new_bundle_dir: str | Path, *,
                   code_commit: str) -> dict:
        self._require_open()
        return create_backup_bundle(
            self.store, self.world_id, new_bundle_dir, code_commit=code_commit)

    def close(self) -> None:
        if not self._closed:
            self.clock.close_session(self.world_id)
            self.store.close()
            self._closed = True

    def __enter__(self) -> 'ResumableTestSession':
        self._require_open()
        return self

    def __exit__(self, *_exc) -> None:
        self.close()
