"""SQLite connection management.

Exposes a context-managed connection factory and a one-shot schema initialiser.
Connections are configured with:

* ``row_factory = sqlite3.Row`` so rows behave like dict-accessible records.
* ``PRAGMA foreign_keys = ON`` so declared foreign keys are enforced.

No other layer should open raw ``sqlite3`` connections; always go through
:func:`get_connection` or the repository classes built on top of it.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a configured SQLite connection to ``db_path``."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection, committing on success and closing always.

    On an unhandled exception the transaction is rolled back and the error is
    re-raised so the caller can surface it. The connection is closed in every
    case — connections are never left open.

    Args:
        db_path: Optional database file path. Defaults to
            :data:`config.settings.DATABASE_PATH`.

    Yields:
        An open :class:`sqlite3.Connection`.
    """
    path = db_path or settings.DATABASE_PATH
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Database transaction failed; rolled back.")
        raise
    finally:
        conn.close()


def initialize_database(db_path: Path | None = None) -> None:
    """Create all tables and indexes by executing ``schema.sql``.

    Idempotent — the schema uses ``CREATE TABLE IF NOT EXISTS`` throughout, so
    calling this repeatedly is safe.

    Args:
        db_path: Optional database file path. Defaults to
            :data:`config.settings.DATABASE_PATH`.
    """
    schema_sql = settings.SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection(db_path) as conn:
        conn.executescript(schema_sql)
    logger.info("Database initialised at %s", db_path or settings.DATABASE_PATH)


def database_exists(db_path: Path | None = None) -> bool:
    """Return ``True`` if the database file exists on disk."""
    return (db_path or settings.DATABASE_PATH).exists()
