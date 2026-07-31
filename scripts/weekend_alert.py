"""Standalone weekend-alert runner.

Runs the race-weekend pipeline for the next upcoming race (or a given race id)
and reports STRONG_BET opportunities. Emails the summary when SMTP is configured
(see :mod:`utilities.notify`); always prints it.

Schedule it to run automatically:

* Windows (Task Scheduler): program ``python``, arguments
  ``scripts\\weekend_alert.py``, "Start in" = the project folder (inside the
  conda env, or use the env's python.exe).
* macOS/Linux (cron): ``0 9 * * 4 cd /path/to/project && python scripts/weekend_alert.py``

Usage:
    python scripts/weekend_alert.py [--race-id N]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Allow running as `python scripts/weekend_alert.py` from the project root by
# putting the root (this file's parent's parent) on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.repositories.races import RaceRepository  # noqa: E402
from services.pipeline_service import WeekendPipeline  # noqa: E402
from services.race_service import RaceService  # noqa: E402
from utilities import notify  # noqa: E402


def _target_race_id(explicit: int | None) -> int | None:
    """Return the race to run: explicit id, else next upcoming, else latest."""
    if explicit is not None:
        return explicit
    upcoming = RaceRepository().get_upcoming(date.today().isoformat())
    if upcoming:
        return upcoming[0]["id"]
    latest = RaceService().latest_race()
    return latest["id"] if latest else None


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns a process exit code."""
    parser = argparse.ArgumentParser(description="PitWall weekend alert runner")
    parser.add_argument("--race-id", type=int, default=None, help="Specific race id")
    args = parser.parse_args(argv)

    race_id = _target_race_id(args.race_id)
    if race_id is None:
        print("No race found — import data first (Settings page).")
        return 1

    summary = WeekendPipeline().run(race_id, send_alert=True)
    print(notify.format_alert(summary))
    if summary["strong_bets"] and not summary["alert_sent"]:
        print("\n(Set SMTP_* / ALERT_EMAIL_* env vars to receive these by email.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
