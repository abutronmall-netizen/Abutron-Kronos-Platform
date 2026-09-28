"""Production-safe quantitative integration contract for Kronos.

This module is intentionally pure and side-effect free.  It enriches Kronos/Fusion
inputs with quantitative telemetry, but defaults to SHADOW mode and cannot submit
orders, change bot tier, or bypass Thesis/Risk/Capital gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Sequence

from app.services.quant_math import QuantSnapshot, TradeEconomics, build_snapshot, trade_economics


class QuantMode(StrEnum):
    OFF = "OFF"
    SHADOW = "SHADOW"
    GATE = "GATE"


@dataclass(frozen=True, slots=True)
class QuantDecision:
    mode: QuantMode
    snapshot: QuantSnapshot
    economics: TradeEconomics | None
    allow_trade: bool
    reason: str

    def telemetry(self) -> dict:
        return {
            "mode": self.mode.value,
            "allow_trade": self.allow_trade,
            "reason": self.reason,
            "features": asdict(self.snapshot),
            "economics": None if self.economics is None else {
                **asdict(self.economics),
                "total_cost": self.economics.total_cost,
                "gross_expectancy": self.economics.gross_expectancy,
                "net_expectancy": self.economics.net_expectancy,
                "positive_edge": self.economics.positive_edge,
            },
        }


def evaluate_quant(
    prices: Sequence[float],
    *,
    mode: QuantMode = QuantMode.SHADOW,
    win_probability: float | None = None,
    expected_win: float | None = None,
    expected_loss: float | None = None,
    spread_cost: float = 0.0,
    slippage_cost: float = 0.0,
    commission_cost: float = 0.0,
    impact_cost: float = 0.0,
) -> QuantDecision:
    snapshot = build_snapshot(prices)

    economics = None
    if win_probability is not None:
        if expected_win is None or expected_loss is None:
            raise ValueError("expected_win and expected_loss are required with win_probability")
        economics = trade_economics(
            win_probability=win_probability,
            expected_win=expected_win,
            expected_loss=expected_loss,
            spread_cost=spread_cost,
            slippage_cost=slippage_cost,
            commission_cost=commission_cost,
            impact_cost=impact_cost,
        )

    if mode is QuantMode.OFF:
        return QuantDecision(mode, snapshot, economics, True, "QUANT_OFF")

    if mode is QuantMode.SHADOW:
        # Critical invariant: shadow telemetry must never block or authorize execution.
        return QuantDecision(mode, snapshot, economics, True, "QUANT_SHADOW_OBSERVE_ONLY")

    if economics is None:
        # Fail closed if someone enables GATE without calibrated economics.
        return QuantDecision(mode, snapshot, economics, False, "QUANT_GATE_MISSING_ECONOMICS")

    if not economics.positive_edge:
        return QuantDecision(mode, snapshot, economics, False, "QUANT_GATE_NON_POSITIVE_EDGE")

    return QuantDecision(mode, snapshot, economics, True, "QUANT_GATE_POSITIVE_EDGE")
