import math

import pytest

from app.services.quant_math import (
    build_snapshot,
    lag1_autocorrelation,
    log_returns,
    trade_economics,
)


def test_log_returns_are_log_price_ratios():
    values = log_returns([100.0, 101.0, 99.0])
    assert values[0] == pytest.approx(math.log(1.01))
    assert values[1] == pytest.approx(math.log(99.0 / 101.0))


def test_snapshot_is_finite_and_side_effect_free():
    snap = build_snapshot([100, 101, 100.5, 102, 101.5, 103])
    assert snap.sample_size == 5
    assert snap.realized_variance >= 0
    assert snap.realized_volatility >= 0
    assert -1 <= snap.lag1_autocorrelation <= 1
    assert math.isfinite(snap.return_zscore)


def test_invalid_prices_are_rejected():
    with pytest.raises(ValueError):
        build_snapshot([100, 0, 101])


def test_autocorrelation_bounds():
    assert lag1_autocorrelation([1, 2, 3, 4]) == pytest.approx(1.0)
    assert -1 <= lag1_autocorrelation([1, -1, 1, -1]) <= 1


def test_trade_economics_rejects_negative_net_edge():
    econ = trade_economics(
        win_probability=0.60,
        expected_win=5.0,
        expected_loss=4.0,
        spread_cost=0.8,
        slippage_cost=0.5,
        commission_cost=0.2,
    )
    assert econ.gross_expectancy == pytest.approx(1.4)
    assert econ.net_expectancy == pytest.approx(-0.1)
    assert econ.positive_edge is False


def test_trade_economics_accepts_positive_net_edge():
    econ = trade_economics(
        win_probability=0.70,
        expected_win=8.0,
        expected_loss=5.0,
        spread_cost=0.3,
        slippage_cost=0.2,
        commission_cost=0.1,
    )
    assert econ.net_expectancy > 0
    assert econ.positive_edge is True


def test_probability_validation():
    with pytest.raises(ValueError):
        trade_economics(win_probability=1.1, expected_win=1, expected_loss=1)
