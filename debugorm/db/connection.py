from __future__ import annotations
import sqlite3
from typing import Any, List, Optional, Tuple


class Connection:
    """Thin wrapper around a single ``sqlite3.Connection``."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def raw(self) -> sqlite3.Connection:
        """Underlying ``sqlite3.Connection``, opened lazily on first access."""
        if self._conn is None:
            self.connect()
        return self._conn

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = self.raw.cursor()
        cursor.execute(sql, params)
        self.raw.commit()
        return cursor

    def fetchall(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        cursor = self.raw.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    def fetchone(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        cursor = self.raw.cursor()
        cursor.execute(sql, params)
        return cursor.fetchone()

    def create_table(self, table_name: str, columns_sql: str) -> None:
        self.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})")

    def __enter__(self) -> "Connection":
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        state = "open" if self._conn is not None else "closed"
        return f"Connection(db={self.db_path!r}, state={state})"


_default_connection: Optional[Connection] = None


def get_connection() -> Connection:
    """Return the process-wide default connection, creating it on first call."""
    global _default_connection
    if _default_connection is None:
        _default_connection = Connection(":memory:")
        _default_connection.connect()
    return _default_connection


def set_connection(connection: Connection) -> None:
    """Replace the global default connection."""
    global _default_connection
    _default_connection = connection


def configure(db_path: str = ":memory:") -> Connection:
    """Open a new connection to *db_path* and set it as the global default."""
    conn = Connection(db_path)
    conn.connect()
    set_connection(conn)
    return conn
