"""Abutron quantitative mathematics engine.

Phase 1 is deliberately side-effect free: feature computation and expectancy gates only.
It must not place orders or alter MT5 execution state.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log, sqrt
from statistics import fmean
from typing import Sequence


_EPS = 1e-12


@dataclass(frozen=True)
class QuantSnapshot:
    log_return: float
    mean_return: float
    volatility: float
    realized_variance: float
    realized_volatility: float
    downside_semivariance: float
    upside_semivariance: float
    return_zscore: float
    lag1_autocorrelation: float
    ewma_volatility: float
    sample_size: int


@dataclass(frozen=True)
class TradeEconomics:
    win_probability: float
    expected_win: float
    expected_loss: float
    spread_cost: float = 0.0
    slippage_cost: float = 0.0
    commission_cost: float = 0.0
    impact_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        return self.spread_cost + self.slippage_cost + self.commission_cost + self.impact_cost

    @property
    def gross_expectancy(self) -> float:
        return self.win_probability * self.expected_win - (1.0 - self.win_probability) * self.expected_loss

    @property
    def net_expectancy(self) -> float:
        return self.gross_expectancy - self.total_cost

    @property
    def positive_edge(self) -> bool:
        return self.net_expectancy > 0.0


def _finite(values: Sequence[float], name: str) -> list[float]:
    out = [float(v) for v in values]
    if not out or any(not isfinite(v) for v in out):
        raise ValueError(f"{name} must contain finite values")
    return out


def log_returns(prices: Sequence[float]) -> list[float]:
    p = _finite(prices, "prices")
    if len(p) < 2:
        raise ValueError("at least two prices are required")
    if any(v <= 0.0 for v in p):
        raise ValueError("prices must be strictly positive")
    return [log(p[i] / p[i - 1]) for i in range(1, len(p))]


def realized_variance(returns: Sequence[float]) -> float:
    r = _finite(returns, "returns")
    return sum(x * x for x in r)


def sample_variance(values: Sequence[float]) -> float:
    x = _finite(values, "values")
    if len(x) < 2:
        return 0.0
    mu = fmean(x)
    return sum((v - mu) ** 2 for v in x) / (len(x) - 1)


def zscore(value: float, history: Sequence[float]) -> float:
    x = _finite(history, "history")
    mu = fmean(x)
    sigma = sqrt(sample_variance(x))
    return 0.0 if sigma <= _EPS else (float(value) - mu) / sigma


def semivariance(returns: Sequence[float], *, downside: bool) -> float:
    r = _finite(returns, "returns")
    selected = [x * x for x in r if (x < 0.0 if downside else x > 0.0)]
    return 0.0 if not selected else sum(selected) / len(r)


def lag1_autocorrelation(values: Sequence[float]) -> float:
    x = _finite(values, "values")
    if len(x) < 3:
        return 0.0
    left, right = x[:-1], x[1:]
    ml, mr = fmean(left), fmean(right)
    num = sum((a - ml) * (b - mr) for a, b in zip(left, right))
    den_l = sum((a - ml) ** 2 for a in left)
    den_r = sum((b - mr) ** 2 for b in right)
    den = sqrt(den_l * den_r)
    return 0.0 if den <= _EPS else max(-1.0, min(1.0, num / den))


def ewma_variance(returns: Sequence[float], decay: float = 0.94) -> float:
    r = _finite(returns, "returns")
    if not 0.0 < decay < 1.0:
        raise ValueError("decay must be between 0 and 1")
    variance = r[0] * r[0]
    for value in r[1:]:
        variance = decay * variance + (1.0 - decay) * value * value
    return variance


def build_snapshot(prices: Sequence[float], *, ewma_decay: float = 0.94) -> QuantSnapshot:
    r = log_returns(prices)
    rv = realized_variance(r)
    var = sample_variance(r)
    vol = sqrt(max(var, 0.0))
    return QuantSnapshot(
        log_return=r[-1],
        mean_return=fmean(r),
        volatility=vol,
        realized_variance=rv,
        realized_volatility=sqrt(rv),
        downside_semivariance=semivariance(r, downside=True),
        upside_semivariance=semivariance(r, downside=False),
        return_zscore=zscore(r[-1], r),
        lag1_autocorrelation=lag1_autocorrelation(r),
        ewma_volatility=sqrt(ewma_variance(r, ewma_decay)),
        sample_size=len(r),
    )


def trade_economics(
    *,
    win_probability: float,
    expected_win: float,
    expected_loss: float,
    spread_cost: float = 0.0,
    slippage_cost: float = 0.0,
    commission_cost: float = 0.0,
    impact_cost: float = 0.0,
) -> TradeEconomics:
    if not 0.0 <= win_probability <= 1.0:
        raise ValueError("win_probability must be between 0 and 1")
    amounts = [expected_win, expected_loss, spread_cost, slippage_cost, commission_cost, impact_cost]
    if any((not isfinite(v)) or v < 0.0 for v in amounts):
        raise ValueError("payoffs and costs must be finite and non-negative")
    return TradeEconomics(
        win_probability=win_probability,
        expected_win=expected_win,
        expected_loss=expected_loss,
        spread_cost=spread_cost,
        slippage_cost=slippage_cost,
        commission_cost=commission_cost,
        impact_cost=impact_cost,
    )
