"""Bet-tracker repository."""
from __future__ import annotations

from typing import Any

from database.repositories.base import BaseRepository


class BetTrackerRepository(BaseRepository):
    """Data access for the ``bet_tracker`` table."""

    table_name = "bet_tracker"

    def get_all_with_context(self) -> list[dict[str, Any]]:
        """Return all bets joined with driver and race names, newest first."""
        return self.query(
            """
            SELECT bt.*, d.full_name AS driver, d.code, r.name AS race_name,
                   r.season, r.round
            FROM bet_tracker bt
            JOIN drivers d ON d.id = bt.driver_id
            JOIN races r ON r.id = bt.race_id
            ORDER BY bt.placed_at DESC
            """
        )

    def get_settled(self) -> list[dict[str, Any]]:
        """Return settled bets (result is win/loss/void, not pending)."""
        return self.query(
            "SELECT * FROM bet_tracker WHERE result IN ('win', 'loss', 'void')"
        )

    def settle(self, bet_id: int, result: str, payout: float) -> bool:
        """Settle a bet, computing profit/loss from payout minus stake.

        Args:
            bet_id: Bet primary-key id.
            result: One of ``'win'``, ``'loss'`` or ``'void'``.
            payout: Total returned amount (stake + profit for a win).

        Returns:
            ``True`` if the bet was updated.
        """
        bet = self.get_by_id(bet_id)
        if bet is None:
            return False
        stake = bet["stake"]
        if result == "void":
            payout, profit = stake, 0.0
        else:
            profit = payout - stake
        return self.update(
            bet_id,
            {
                "result": result,
                "payout": payout,
                "profit_loss": profit,
                "settled_at": _now(),
            },
        )


def _now() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
