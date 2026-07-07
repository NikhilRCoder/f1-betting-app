"""Generic repository base class.

:class:`BaseRepository` provides table-agnostic CRUD built on the shared
connection manager. Concrete repositories declare their ``table_name`` and
(optionally) an ``upsert_key`` for idempotent seeding, then inherit insert,
update, delete, and query helpers.

Repositories return plain ``dict`` records (or lists of them) so that upper
layers never depend on ``sqlite3.Row`` internals.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Sequence

from config.logging_config import get_logger
from database.connection import get_connection

logger = get_logger(__name__)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a :class:`sqlite3.Row` to a plain dict (or ``None``)."""
    return dict(row) if row is not None else None


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert an iterable of rows to a list of plain dicts."""
    return [dict(r) for r in rows]


class BaseRepository:
    """Generic CRUD repository for a single table.

    Subclasses must set :attr:`table_name`. Setting :attr:`upsert_key` to a
    tuple of column names enables :meth:`upsert` for idempotent imports.

    Attributes:
        table_name: Name of the backing SQL table.
        upsert_key: Column(s) forming the natural key used by :meth:`upsert`.
        db_path: Optional non-default database path (mainly for tests).
    """

    table_name: str = ""
    upsert_key: Sequence[str] = ()

    def __init__(self, db_path: Path | None = None) -> None:
        if not self.table_name:
            raise ValueError(
                f"{type(self).__name__} must define a non-empty 'table_name'."
            )
        self.db_path = db_path

    # ── Reads ────────────────────────────────────────────────────────
    def get_by_id(self, record_id: int) -> dict[str, Any] | None:
        """Return the record with the given primary-key id, or ``None``."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE id = ?", (record_id,)
            )
            return row_to_dict(cur.fetchone())

    def get_all(
        self, order_by: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Return all records, optionally ordered and limited."""
        sql = f"SELECT * FROM {self.table_name}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        with get_connection(self.db_path) as conn:
            return rows_to_dicts(conn.execute(sql).fetchall())

    def find_by(self, **filters: Any) -> list[dict[str, Any]]:
        """Return records matching equality filters on the given columns."""
        if not filters:
            return self.get_all()
        clause = " AND ".join(f"{col} = ?" for col in filters)
        sql = f"SELECT * FROM {self.table_name} WHERE {clause}"
        with get_connection(self.db_path) as conn:
            return rows_to_dicts(conn.execute(sql, tuple(filters.values())).fetchall())

    def find_one(self, **filters: Any) -> dict[str, Any] | None:
        """Return the first record matching the equality filters, or ``None``."""
        results = self.find_by(**filters)
        return results[0] if results else None

    def count(self) -> int:
        """Return the total number of rows in the table."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(f"SELECT COUNT(*) AS n FROM {self.table_name}")
            return int(cur.fetchone()["n"])

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        """Run an arbitrary read-only SQL query and return dict records.

        Intended for the joins/aggregations that concrete repositories need.
        """
        with get_connection(self.db_path) as conn:
            return rows_to_dicts(conn.execute(sql, tuple(params)).fetchall())

    # ── Writes ───────────────────────────────────────────────────────
    def insert(self, data: dict[str, Any]) -> int:
        """Insert one record and return its new primary-key id."""
        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        col_list = ", ".join(columns)
        sql = f"INSERT INTO {self.table_name} ({col_list}) VALUES ({placeholders})"
        with get_connection(self.db_path) as conn:
            cur = conn.execute(sql, tuple(data.values()))
            return int(cur.lastrowid)

    def insert_many(self, records: Iterable[dict[str, Any]]) -> int:
        """Insert many records sharing the same columns; return the row count."""
        records = list(records)
        if not records:
            return 0
        columns = list(records[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        col_list = ", ".join(columns)
        sql = f"INSERT INTO {self.table_name} ({col_list}) VALUES ({placeholders})"
        rows = [tuple(r[c] for c in columns) for r in records]
        with get_connection(self.db_path) as conn:
            conn.executemany(sql, rows)
        return len(rows)

    def update(self, record_id: int, data: dict[str, Any]) -> bool:
        """Update a record by id; return ``True`` if a row was changed."""
        if not data:
            return False
        assignments = ", ".join(f"{col} = ?" for col in data)
        sql = f"UPDATE {self.table_name} SET {assignments} WHERE id = ?"
        params = (*data.values(), record_id)
        with get_connection(self.db_path) as conn:
            cur = conn.execute(sql, params)
            return cur.rowcount > 0

    def delete(self, record_id: int) -> bool:
        """Delete a record by id; return ``True`` if a row was removed."""
        with get_connection(self.db_path) as conn:
            cur = conn.execute(
                f"DELETE FROM {self.table_name} WHERE id = ?", (record_id,)
            )
            return cur.rowcount > 0

    def upsert(self, data: dict[str, Any]) -> int:
        """Insert or update a record using :attr:`upsert_key` as the conflict key.

        Enables idempotent CSV re-imports. Returns the id of the affected row.

        Raises:
            ValueError: If :attr:`upsert_key` is not configured on the subclass.
        """
        if not self.upsert_key:
            raise ValueError(
                f"{type(self).__name__} must define 'upsert_key' to use upsert()."
            )
        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        col_list = ", ".join(columns)
        conflict = ", ".join(self.upsert_key)
        updates = ", ".join(
            f"{c} = excluded.{c}" for c in columns if c not in self.upsert_key
        )
        sql = (
            f"INSERT INTO {self.table_name} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict}) DO UPDATE SET {updates}"
        )
        with get_connection(self.db_path) as conn:
            cur = conn.execute(sql, tuple(data.values()))
            if cur.lastrowid:
                return int(cur.lastrowid)
            key_clause = " AND ".join(f"{c} = ?" for c in self.upsert_key)
            found = conn.execute(
                f"SELECT id FROM {self.table_name} WHERE {key_clause}",
                tuple(data[c] for c in self.upsert_key),
            ).fetchone()
            return int(found["id"]) if found else -1
