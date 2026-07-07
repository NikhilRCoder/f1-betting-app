"""Central application configuration.

Single source of truth for filesystem paths, database location, and
application-wide constants. Nothing in this module imports Streamlit or any
UI framework — it is safe to import from every layer of the stack.
"""
from __future__ import annotations

from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════════════════════
# Project root is two levels up from this file: <root>/config/settings.py
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

DATA_DIR: Path = PROJECT_ROOT / "data"
CSV_DIR: Path = DATA_DIR / "csv"
PROCESSED_DIR: Path = DATA_DIR / "processed"
EXPORTS_DIR: Path = PROJECT_ROOT / "exports"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
LOGS_DIR: Path = PROJECT_ROOT / "logs"

DATABASE_DIR: Path = PROJECT_ROOT / "database"
SCHEMA_PATH: Path = DATABASE_DIR / "schema.sql"
MIGRATIONS_DIR: Path = DATABASE_DIR / "migrations"

# Database file lives under data/ so it is easy to back up and is gitignored.
DATABASE_PATH: Path = DATA_DIR / "pitwall.db"


def ensure_directories() -> None:
    """Create all runtime directories if they do not already exist.

    Called once at application start-up so that seeding, exports, reports and
    logging never fail on a missing folder.
    """
    for directory in (
        DATA_DIR,
        CSV_DIR,
        PROCESSED_DIR,
        EXPORTS_DIR,
        REPORTS_DIR,
        LOGS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# Application metadata
# ═══════════════════════════════════════════════════════════════════
APP_NAME: str = "PitWall"
APP_TAGLINE: str = "F1 Betting Analytics Platform"
APP_ICON: str = "🏎️"
APP_VERSION: str = "0.1.0"

# ═══════════════════════════════════════════════════════════════════
# Betting / model constants
# ═══════════════════════════════════════════════════════════════════
# Default fractional-Kelly multiplier used across calculators and services.
DEFAULT_KELLY_FRACTION: float = 0.25

# Default starting bankroll (currency-agnostic units) for simulations.
DEFAULT_BANKROLL: float = 1_000.0

# Points at which a driver is considered "in the points" (top 10).
POINTS_POSITIONS: int = 10

# Recognised betting markets (kept in sync with the odds_history schema).
MARKETS: tuple[str, ...] = (
    "race_winner",
    "podium",
    "top5",
    "top10",
    "pole",
    "fastest_lap",
    "h2h",
)

# Recognised recommendation verdicts (kept in sync with recommendations schema).
VERDICTS: tuple[str, ...] = (
    "STRONG_BET",
    "SMALL_EDGE",
    "NO_BET",
    "AVOID",
)

# ═══════════════════════════════════════════════════════════════════
# Recommendation-engine thresholds
# ═══════════════════════════════════════════════════════════════════
# Expected-value thresholds expressed as fractions (0.10 == 10%).
STRONG_BET_EV: float = 0.10
SMALL_EDGE_EV: float = 0.03
AVOID_EV: float = -0.03

# Confidence thresholds (0-100 scale).
STRONG_BET_CONFIDENCE: float = 70.0
SMALL_EDGE_CONFIDENCE: float = 50.0

# ═══════════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════════
LOG_LEVEL: str = "INFO"
LOG_FILE: Path = LOGS_DIR / "pitwall.log"
