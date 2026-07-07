"""Structured logging configuration.

Provides a single ``configure_logging`` entry point that installs a consistent
console + rotating-file handler set. Every module should obtain its logger via
``logging.getLogger(__name__)`` after configuration has run once at start-up.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import settings

_CONFIGURED: bool = False

_LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str | None = None) -> None:
    """Configure root logging handlers exactly once.

    Args:
        level: Optional override for the log level (e.g. ``"DEBUG"``). Falls
            back to :data:`config.settings.LOG_LEVEL` when omitted.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings.ensure_directories()
    log_level = getattr(logging, (level or settings.LOG_LEVEL).upper(), logging.INFO)

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    # Clear any pre-existing handlers (e.g. from Streamlit's re-runs).
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger, ensuring logging is set up first.

    Args:
        name: Logger name, conventionally ``__name__`` of the calling module.

    Returns:
        A :class:`logging.Logger` ready for use.
    """
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
