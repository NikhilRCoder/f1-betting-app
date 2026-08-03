"""CSV → SQLite loader.

Imports Ergast-style CSV dumps into the PitWall schema. Ergast's own integer
identifiers are reused as our primary keys so foreign-key relationships survive
the import unchanged.

The loader:

1. Accepts a directory containing the expected CSV files.
2. Maps CSV columns to the schema (see :data:`_TABLE_LOADERS`).
3. Upserts records via ``INSERT OR REPLACE`` so re-imports are idempotent.
4. Logs row counts per table.

Only files that are present are imported; missing files are skipped with a
warning, so a partial dump still loads what it can.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from config import settings
from config.logging_config import get_logger
from database.connection import get_connection

logger = get_logger(__name__)

# Ergast encodes missing values as the literal string "\N".
_NULL_TOKEN = "\\N"


def _clean(value: Any) -> Any:
    """Normalise Ergast null tokens and NaN to ``None``."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in ("", _NULL_TOKEN):
            return None
        return stripped
    return value


def _to_int(value: Any) -> int | None:
    """Coerce a value to ``int`` or ``None``."""
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _time_to_ms(value: Any) -> int | None:
    """Parse a lap-time string (``'m:ss.mmm'`` or ``'ss.mmm'``) to milliseconds."""
    value = _clean(value)
    if value is None:
        return None
    try:
        text = str(value)
        if ":" in text:
            minutes, seconds = text.split(":")
            total = int(minutes) * 60 + float(seconds)
        else:
            total = float(text)
        return int(round(total * 1000))
    except (ValueError, TypeError):
        return None


def _read_csv(csv_dir: Path, filename: str) -> pd.DataFrame | None:
    """Read a CSV if present, returning ``None`` when the file is missing."""
    path = csv_dir / filename
    if not path.exists():
        logger.warning("CSV not found, skipping: %s", path.name)
        return None
    return pd.read_csv(path, dtype=str, keep_default_na=False)


# ── Per-table row mappers ────────────────────────────────────────────
def _map_circuits(row: pd.Series) -> dict[str, Any]:
    return {
        "id": _to_int(row.get("circuitId")),
        "name": _clean(row.get("name")),
        "country": _clean(row.get("country")) or "Unknown",
        "city": _clean(row.get("location")),
        "altitude_m": _clean(row.get("alt")),
        "latitude": _clean(row.get("lat")),
        "longitude": _clean(row.get("lng")),
    }


def _map_drivers(row: pd.Series) -> dict[str, Any]:
    forename = _clean(row.get("forename")) or ""
    surname = _clean(row.get("surname")) or ""
    return {
        "id": _to_int(row.get("driverId")),
        "code": _clean(row.get("code")),  # may be None — resolved downstream
        "first_name": forename,
        "last_name": surname,
        "full_name": f"{forename} {surname}".strip(),
        "nationality": _clean(row.get("nationality")),
        "date_of_birth": _clean(row.get("dob")),
    }


def _assign_unique_codes(rows: list[dict[str, Any]]) -> None:
    """Fill missing/duplicate driver codes with unique fallbacks in place.

    The schema requires ``drivers.code`` to be NOT NULL and UNIQUE, but many
    historic Ergast drivers have no code. Missing codes fall back to the first
    three letters of the surname (uppercased); any collision is disambiguated
    with a numeric suffix so the UNIQUE constraint is never violated.
    """
    seen: set[str] = set()
    for row in rows:
        code = row.get("code")
        if not code:
            surname = (row.get("last_name") or "DRV").upper()
            code = "".join(ch for ch in surname if ch.isalpha())[:3] or "DRV"
        base = code
        suffix = 1
        while code in seen:
            suffix += 1
            code = f"{base}{suffix}"
        seen.add(code)
        row["code"] = code


def _map_constructors(row: pd.Series) -> dict[str, Any]:
    return {
        "id": _to_int(row.get("constructorId")),
        "name": _clean(row.get("name")),
        "nationality": _clean(row.get("nationality")),
    }


def _map_races(row: pd.Series) -> dict[str, Any]:
    return {
        "id": _to_int(row.get("raceId")),
        "season": _to_int(row.get("year")),
        "round": _to_int(row.get("round")),
        "circuit_id": _to_int(row.get("circuitId")),
        "name": _clean(row.get("name")),
        "date": _clean(row.get("date")),
        "time": _clean(row.get("time")),
    }


def _map_results(row: pd.Series, status_map: dict[int, str]) -> dict[str, Any]:
    status_id = _to_int(row.get("statusId"))
    return {
        "race_id": _to_int(row.get("raceId")),
        "driver_id": _to_int(row.get("driverId")),
        "constructor_id": _to_int(row.get("constructorId")),
        "grid": _to_int(row.get("grid")),
        "position": _to_int(row.get("position")),  # NULL for DNF/DNS/DSQ
        "position_text": _clean(row.get("positionText")),
        "points": float(_clean(row.get("points")) or 0),
        "laps_completed": _to_int(row.get("laps")),
        "status": status_map.get(status_id) if status_id is not None else None,
        "time_ms": _to_int(row.get("milliseconds")),
        "fastest_lap_rank": _to_int(row.get("rank")),
        "fastest_lap_time_ms": _time_to_ms(row.get("fastestLapTime")),
        "fastest_lap_speed": _clean(row.get("fastestLapSpeed")),
    }


def _map_qualifying(row: pd.Series) -> dict[str, Any]:
    return {
        "race_id": _to_int(row.get("raceId")),
        "driver_id": _to_int(row.get("driverId")),
        "constructor_id": _to_int(row.get("constructorId")),
        "position": _to_int(row.get("position")),
        "q1_time_ms": _time_to_ms(row.get("q1")),
        "q2_time_ms": _time_to_ms(row.get("q2")),
        "q3_time_ms": _time_to_ms(row.get("q3")),
    }


def _map_pit_stops(row: pd.Series) -> dict[str, Any]:
    return {
        "race_id": _to_int(row.get("raceId")),
        "driver_id": _to_int(row.get("driverId")),
        "stop_number": _to_int(row.get("stop")),
        "lap": _to_int(row.get("lap")),
        "duration_ms": _to_int(row.get("milliseconds")),
        "total_time_ms": _to_int(row.get("milliseconds")),
    }


def _bulk_replace(
    table: str, columns: list[str], rows: list[dict[str, Any]], db_path: Path | None
) -> int:
    """``INSERT OR REPLACE`` a batch of rows into ``table``; return the count."""
    if not rows:
        return 0
    placeholders = ", ".join("?" for _ in columns)
    col_list = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})"
    values = [tuple(r[c] for c in columns) for r in rows]
    with get_connection(db_path) as conn:
        conn.executemany(sql, values)
    return len(values)


def _load_status_map(csv_dir: Path) -> dict[int, str]:
    """Load the ``statusId`` → status-text mapping from ``status.csv``."""
    df = _read_csv(csv_dir, "status.csv")
    if df is None:
        return {}
    return {
        _to_int(r["statusId"]): _clean(r["status"])
        for _, r in df.iterrows()
        if _to_int(r["statusId"]) is not None
    }


def seed_database(csv_dir: Path, db_path: Path | None = None) -> dict[str, int]:
    """Import all supported CSV files from ``csv_dir`` into the database.

    Args:
        csv_dir: Directory containing Ergast-style CSV files.
        db_path: Optional non-default database path (used by tests).

    Returns:
        A mapping of table name to the number of rows imported.
    """
    csv_dir = Path(csv_dir)
    counts: dict[str, int] = {}
    status_map = _load_status_map(csv_dir)

    # Seasons must exist before races (races.season -> seasons.year FK).
    counts["seasons"] = _seed_seasons_from_csv(csv_dir, db_path)

    # (table, filename, mapper) — simple 1:1 mapped tables.
    simple: list[tuple[str, str, Callable[[pd.Series], dict[str, Any]]]] = [
        ("circuits", "circuits.csv", _map_circuits),
        ("drivers", "drivers.csv", _map_drivers),
        ("constructors", "constructors.csv", _map_constructors),
        ("races", "races.csv", _map_races),
        ("qualifying", "qualifying.csv", _map_qualifying),
        ("pit_stops", "pit_stops.csv", _map_pit_stops),
    ]

    for table, filename, mapper in simple:
        df = _read_csv(csv_dir, filename)
        if df is None:
            continue
        rows = [mapper(r) for _, r in df.iterrows()]
        if table == "drivers":
            _assign_unique_codes(rows)
        columns = list(rows[0].keys()) if rows else []
        counts[table] = _bulk_replace(table, columns, rows, db_path)

    # Results need the status map injected.
    df = _read_csv(csv_dir, "results.csv")
    if df is not None:
        rows = [_map_results(r, status_map) for _, r in df.iterrows()]
        columns = list(rows[0].keys()) if rows else []
        counts["results"] = _bulk_replace("results", columns, rows, db_path)

    for table, n in counts.items():
        logger.info("Seeded %s: %d rows", table, n)
    return counts


def seed_from_uploaded(
    files: Iterable[Any], db_path: Path | None = None, dest_dir: Path | None = None
) -> dict[str, int]:
    """Save uploaded CSV files to disk and run the Ergast seeder.

    Bridges Streamlit's file uploader to :func:`seed_database`. Each item in
    ``files`` must expose a ``name`` attribute and either ``getbuffer()`` or
    ``getvalue()`` returning the file bytes (Streamlit ``UploadedFile`` does).

    Args:
        files: Uploaded file-like objects (e.g. Streamlit ``UploadedFile``).
        db_path: Optional non-default database path (used by tests).
        dest_dir: Directory to write the CSVs into. Defaults to
            :data:`config.settings.CSV_DIR`.

    Returns:
        A mapping of table name to the number of rows imported.
    """
    target = Path(dest_dir) if dest_dir is not None else settings.CSV_DIR
    target.mkdir(parents=True, exist_ok=True)

    written = 0
    for upload in files:
        name = Path(getattr(upload, "name", "")).name
        if not name.lower().endswith(".csv"):
            logger.warning("Ignoring non-CSV upload: %s", name or "<unnamed>")
            continue
        data = upload.getbuffer() if hasattr(upload, "getbuffer") else upload.getvalue()
        (target / name).write_bytes(bytes(data))
        written += 1

    logger.info("Saved %d uploaded CSV(s) to %s", written, target)
    return seed_database(target, db_path)


def import_dataframe(
    table: str, df: pd.DataFrame, db_path: Path | None = None
) -> int:
    """Import a DataFrame into a schema table, keeping only matching columns.

    A generic, schema-aware single-table importer for CSVs whose column names
    already match a PitWall table. Columns not present in the table are dropped;
    rows are written with ``INSERT OR REPLACE`` for idempotency.

    Args:
        table: Target table name. Must be a real table in the schema.
        df: Rows to import; column names should match the table's columns.
        db_path: Optional non-default database path (used by tests).

    Returns:
        The number of rows written.

    Raises:
        ValueError: If ``table`` is not a known schema table or no columns match.
    """
    with get_connection(db_path) as conn:
        table_info = conn.execute(f"PRAGMA table_info({table})").fetchall()
    valid_columns = {row["name"] for row in table_info}
    if not valid_columns:
        raise ValueError(f"Unknown table '{table}'.")

    use_columns = [c for c in df.columns if c in valid_columns]
    if not use_columns:
        raise ValueError(
            f"None of the CSV columns match table '{table}'. "
            f"Expected some of: {sorted(valid_columns)}."
        )

    subset = df[use_columns].where(pd.notna(df[use_columns]), None)
    rows = [
        {col: _clean(row[col]) for col in use_columns}
        for _, row in subset.iterrows()
    ]
    written = _bulk_replace(table, use_columns, rows, db_path)
    logger.info("Imported %d rows into %s (columns: %s)", written, table, use_columns)
    return written


def _seed_seasons_from_csv(csv_dir: Path, db_path: Path | None) -> int:
    """Populate ``seasons`` from distinct years/round counts in ``races.csv``.

    Runs before races are imported so the ``races.season`` foreign key resolves.
    Returns 0 when ``races.csv`` is absent.
    """
    df = _read_csv(csv_dir, "races.csv")
    if df is None:
        return 0
    seasons: dict[int, int] = {}
    for _, row in df.iterrows():
        year = _to_int(row.get("year"))
        rnd = _to_int(row.get("round")) or 0
        if year is None:
            continue
        seasons[year] = max(seasons.get(year, 0), rnd)
    with get_connection(db_path) as conn:
        for year, rounds in seasons.items():
            conn.execute(
                "INSERT OR REPLACE INTO seasons (year, rounds) VALUES (?, ?)",
                (year, rounds),
            )
    return len(seasons)
