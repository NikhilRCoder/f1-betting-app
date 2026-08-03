"""Optional alert notifications.

Sends alerts by email when SMTP settings are provided via environment variables;
otherwise every call is a safe no-op. This keeps alerting available without
hard-coding credentials — the user configures it (or not) in their environment.

Environment variables:
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
    ALERT_EMAIL_FROM (defaults to SMTP_USER), ALERT_EMAIL_TO
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

from config.logging_config import get_logger

logger = get_logger(__name__)


def is_configured() -> bool:
    """Return ``True`` if the minimum SMTP settings are present."""
    return bool(
        os.environ.get("SMTP_HOST")
        and os.environ.get("ALERT_EMAIL_TO")
        and os.environ.get("SMTP_USER")
    )


def send_email(subject: str, body: str) -> bool:
    """Send an alert email if SMTP is configured.

    Args:
        subject: Email subject line.
        body: Plain-text body.

    Returns:
        ``True`` if an email was sent, ``False`` if unconfigured or on failure
        (failures are logged, never raised, so alerting never breaks a run).
    """
    if not is_configured():
        logger.info("Alert email skipped — SMTP not configured.")
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.environ.get("ALERT_EMAIL_FROM", os.environ["SMTP_USER"])
        msg["To"] = os.environ["ALERT_EMAIL_TO"]
        msg.set_content(body)
        host = os.environ["SMTP_HOST"]
        port = int(os.environ.get("SMTP_PORT", "587"))
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            server.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            server.send_message(msg)
        logger.info("Alert email sent to %s", os.environ["ALERT_EMAIL_TO"])
        return True
    except Exception as exc:  # noqa: BLE001 - alerting must never crash a run
        logger.warning("Alert email failed: %s", exc)
        return False


def format_alert(summary: dict[str, Any]) -> str:
    """Render a weekend-pipeline summary into a plain-text alert body."""
    lines = [
        f"PitWall — value alert for race {summary.get('race_name', summary['race_id'])}",
        "",
    ]
    strong = summary.get("strong_bets", [])
    if not strong:
        lines.append("No STRONG_BET opportunities detected.")
    else:
        lines.append(f"{len(strong)} STRONG_BET opportunity(ies):")
        for r in strong:
            lines.append(
                f"  • {r.get('driver', r['driver_id'])} [{r['market']}] — "
                f"model {r['model_probability']:.1%} vs implied "
                f"{r['implied_probability']:.1%}, EV {r['expected_value']:+.1%}, "
                f"conf {r['confidence']:.0f}/100"
            )
    return "\n".join(lines)
