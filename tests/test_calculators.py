"""Tests for the pure calculators package."""
from __future__ import annotations

import math

import pytest

from calculators import (
    arbitrage,
    bankroll,
    dutch,
    expected_value,
    kelly,
    overround,
    probability,
    roi,
    stake,
)


# ── probability ──────────────────────────────────────────────────────
def test_decimal_to_implied():
    assert probability.decimal_to_implied(2.0) == pytest.approx(0.5)
    assert probability.decimal_to_implied(4.0) == pytest.approx(0.25)


def test_implied_to_decimal_roundtrip():
    assert probability.implied_to_decimal(0.5) == pytest.approx(2.0)
    assert probability.implied_to_decimal(
        probability.decimal_to_implied(3.3)
    ) == pytest.approx(3.3)


def test_american_conversions():
    assert probability.american_to_decimal(100) == pytest.approx(2.0)
    assert probability.american_to_decimal(-200) == pytest.approx(1.5)
    assert probability.decimal_to_american(2.0) == "+100"
    assert probability.decimal_to_american(1.5) == "-200"


def test_fractional_conversions():
    assert probability.fractional_to_decimal(5, 2) == pytest.approx(3.5)
    assert probability.decimal_to_fractional(3.5) == "5/2"


def test_convert_all():
    out = probability.convert_all(2.0, "decimal")
    assert out["implied_probability"] == pytest.approx(0.5)
    assert out["american"] == "+100"


def test_probability_validation():
    with pytest.raises(ValueError):
        probability.decimal_to_implied(1.0)
    with pytest.raises(ValueError):
        probability.implied_to_decimal(1.5)
    with pytest.raises(ValueError):
        probability.american_to_decimal(0)


# ── expected value ───────────────────────────────────────────────────
def test_expected_value():
    # Fair coin at even money -> zero EV.
    assert expected_value.calculate_ev(0.5, 2.0) == pytest.approx(0.0)
    # 50% at 2.5 -> +25% EV.
    assert expected_value.calculate_ev(0.5, 2.5) == pytest.approx(0.25)
    assert expected_value.calculate_ev_percentage(0.5, 2.5) == pytest.approx(25.0)


# ── kelly ────────────────────────────────────────────────────────────
def test_full_kelly():
    # p=0.6, odds=2.0 -> f = (1*0.6 - 0.4)/1 = 0.2
    assert kelly.full_kelly(0.6, 2.0) == pytest.approx(0.2)


def test_kelly_no_edge_clamped():
    assert kelly.full_kelly(0.4, 2.0) == 0.0


def test_fractional_and_stake():
    assert kelly.fractional_kelly(0.6, 2.0, 0.5) == pytest.approx(0.1)
    assert kelly.kelly_stake(1000, 0.6, 2.0, 0.25) == pytest.approx(50.0)


# ── arbitrage ────────────────────────────────────────────────────────
def test_detect_arb_true():
    is_arb, margin = arbitrage.detect_arb([2.1, 2.1])
    assert is_arb is True
    assert margin > 0


def test_detect_arb_false():
    is_arb, margin = arbitrage.detect_arb([1.9, 1.9])
    assert is_arb is False
    assert margin < 0


def test_arb_stakes_equal_return():
    odds = [2.1, 2.05]
    stakes = arbitrage.arb_stakes(odds, 100.0)
    returns = [s * o for s, o in zip(stakes, odds)]
    assert returns[0] == pytest.approx(returns[1])
    assert sum(stakes) == pytest.approx(100.0)


# ── dutch ────────────────────────────────────────────────────────────
def test_dutch_stakes_equal_return():
    odds = [3.0, 4.0, 5.0]
    stakes = dutch.dutch_stakes(odds, 100.0)
    returns = [s * o for s, o in zip(stakes, odds)]
    assert returns[0] == pytest.approx(returns[1]) == pytest.approx(returns[2])
    assert sum(stakes) == pytest.approx(100.0)


def test_dutch_profit_sign():
    # Overround book -> negative profit.
    assert dutch.dutch_profit([1.9, 1.9], 100.0) < 0
    # Arbitrage book -> positive profit.
    assert dutch.dutch_profit([2.1, 2.1], 100.0) > 0


# ── overround ────────────────────────────────────────────────────────
def test_overround():
    assert overround.calculate_overround([2.0, 2.0]) == pytest.approx(0.0)
    assert overround.calculate_overround([1.9, 1.9]) == pytest.approx(
        2 / 1.9 - 1
    )


def test_true_probabilities_sum_to_one():
    probs = overround.true_probabilities([1.9, 3.5, 6.0])
    assert sum(probs) == pytest.approx(1.0)


# ── bankroll ─────────────────────────────────────────────────────────
def test_growth_projection_length_and_growth():
    traj = bankroll.growth_projection(1000, 0.05, 2, 10)
    assert len(traj) == 11
    assert traj[0] == 1000
    assert traj[-1] > traj[0]


def test_risk_of_ruin_bounds():
    # Negative edge -> certain ruin.
    assert bankroll.risk_of_ruin(1000, 20, 0.2, 2.0) == 1.0
    # Positive edge -> risk in [0, 1].
    ror = bankroll.risk_of_ruin(1000, 20, 0.6, 2.0)
    assert 0.0 <= ror <= 1.0


# ── roi ──────────────────────────────────────────────────────────────
def test_roi_and_yield():
    assert roi.calculate_roi(50, 500) == pytest.approx(10.0)
    assert roi.calculate_roi(0, 0) == 0.0
    assert roi.calculate_yield(100, 20) == pytest.approx(5.0)
    assert roi.calculate_yield(100, 0) == 0.0


def test_closing_line_value():
    assert roi.closing_line_value(2.2, 2.0) == pytest.approx(10.0)
    assert math.isclose(roi.closing_line_value(2.0, 2.0), 0.0)


# ── stake dispatcher ─────────────────────────────────────────────────
def test_stake_dispatch():
    assert stake.size_stake("flat", 1000, unit=25) == 25
    assert stake.size_stake("percentage", 1000, pct=2) == pytest.approx(20.0)
    assert stake.size_stake(
        "kelly", 1000, prob=0.6, decimal_odds=2.0, kelly_fraction=0.25
    ) == pytest.approx(50.0)
    with pytest.raises(ValueError):
        stake.size_stake("bogus", 1000)
