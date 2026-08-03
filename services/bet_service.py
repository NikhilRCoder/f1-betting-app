"""Bet-tracking service — placement, settlement and P&L analytics.

Wraps the bet-tracker repository with staking helpers and the profit metrics the
Dashboard reports. This is how the platform measures whether it is actually
generating profit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from calculators import roi as roi_calc
from config.logging_config import get_logger
from database.repositories.bet_tracker import BetTrackerRepository
from utilities.helpers import safe_div

logger = get_logger(__name__)


class BetService:
    """Record bets and compute bankroll performance."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._bets = BetTrackerRepository(db_path=db_path)

    def place_bet(
        self,
        race_id: int,
        driver_id: int,
        market: str,
        odds_taken: float,
        stake: float,
        bookmaker: str | None = None,
        recommendation_id: int | None = None,
        notes: str | None = None,
    ) -> int:
        """Record a placed (pending) bet and return its id.

        Raises:
            ValueError: If odds are not > 1.0 or stake is not positive.
        """
        if odds_taken <= 1.0:
            raise ValueError("Odds taken must be greater than 1.0.")
        if stake <= 0:
            raise ValueError("Stake must be positive.")
        return self._bets.insert(
            {
                "race_id": race_id,
                "driver_id": driver_id,
                "market": market,
                "bookmaker": bookmaker,
                "odds_taken": odds_taken,
                "stake": stake,
                "recommendation_id": recommendation_id,
                "result": "pending",
                "notes": notes,
            }
        )

    def settle_bet(self, bet_id: int, result: str, payout: float | None = None) -> bool:
        """Settle a bet as win/loss/void.

        For a win, ``payout`` defaults to ``stake × odds_taken`` when omitted.
        A loss has zero payout.
        """
        bet = self._bets.get_by_id(bet_id)
        if bet is None:
            return False
        if result == "win" and payout is None:
            payout = bet["stake"] * bet["odds_taken"]
        elif result == "loss":
            payout = 0.0
        return self._bets.settle(bet_id, result, payout or 0.0)

    def list_bets(self) -> list[dict[str, Any]]:
        """Return all bets with driver/race context, newest first."""
        return self._bets.get_all_with_context()

    def pnl_summary(self) -> dict[str, Any]:
        """Return headline P&L metrics across all settled bets."""
        settled = self._bets.get_settled()
        graded = [b for b in settled if b["result"] in ("win", "loss")]
        total_staked = sum(b["stake"] for b in graded)
        total_pl = sum(b["profit_loss"] or 0.0 for b in graded)
        wins = sum(1 for b in graded if b["result"] == "win")
        return {
            "total_bets": len(graded),
            "wins": wins,
            "win_rate": round(safe_div(wins, len(graded)), 4),
            "total_staked": round(total_staked, 2),
            "total_profit_loss": round(total_pl, 2),
            "roi_pct": round(roi_calc.calculate_roi(total_pl, total_staked), 2),
            "yield_pct": round(
                roi_calc.calculate_yield(total_pl, len(graded)), 4
            ),
        }

    def pnl_timeline(self) -> list[dict[str, Any]]:
        """Return cumulative profit over settled bets ordered by settlement."""
        settled = [
            b for b in self._bets.get_all_with_context()
            if b["result"] in ("win", "loss") and b["settled_at"]
        ]
        settled.sort(key=lambda b: b["settled_at"])
        cumulative = 0.0
        timeline = []
        for bet in settled:
            cumulative += bet["profit_loss"] or 0.0
            timeline.append(
                {"settled_at": bet["settled_at"], "cumulative_pl": round(cumulative, 2)}
            )
        return timeline

    def performance_by(self, field: str) -> list[dict[str, Any]]:
        """Return profit grouped by ``market`` or ``verdict`` proxy.

        Args:
            field: ``"market"`` (grouped from bet_tracker) — the supported
                grouping for now.

        Returns:
            A list of ``{group, bets, profit_loss}`` dicts.
        """
        if field != "market":
            raise ValueError("Only 'market' grouping is supported.")
        rows = self._bets.query(
            """
            SELECT market AS group_key,
                   COUNT(*) AS bets,
                   ROUND(SUM(COALESCE(profit_loss, 0)), 2) AS profit_loss
            FROM bet_tracker
            WHERE result IN ('win', 'loss')
            GROUP BY market
            ORDER BY profit_loss DESC
            """
        )
        return [
            {"group": r["group_key"], "bets": r["bets"], "profit_loss": r["profit_loss"]}
            for r in rows
        ]
