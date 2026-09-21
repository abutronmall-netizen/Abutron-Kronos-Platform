import pytest

from app.services.kronos_quant import QuantMode, evaluate_quant


PRICES = [100.0, 100.4, 100.2, 100.8, 101.1, 100.9, 101.5]


def test_shadow_mode_never_blocks_existing_pipeline():
    result = evaluate_quant(PRICES)
    assert result.mode is QuantMode.SHADOW
    assert result.allow_trade is True
    assert result.reason == "QUANT_SHADOW_OBSERVE_ONLY"
    assert result.telemetry()["features"]["sample_size"] == len(PRICES) - 1


def test_gate_fails_closed_without_calibrated_economics():
    result = evaluate_quant(PRICES, mode=QuantMode.GATE)
    assert result.allow_trade is False
    assert result.reason == "QUANT_GATE_MISSING_ECONOMICS"


def test_gate_blocks_negative_net_expectancy():
    result = evaluate_quant(
        PRICES,
        mode=QuantMode.GATE,
        win_probability=0.55,
        expected_win=5.0,
        expected_loss=5.0,
        spread_cost=0.4,
        slippage_cost=0.3,
    )
    assert result.allow_trade is False
    assert result.reason == "QUANT_GATE_NON_POSITIVE_EDGE"


def test_gate_allows_positive_edge_but_does_not_execute():
    result = evaluate_quant(
        PRICES,
        mode=QuantMode.GATE,
        win_probability=0.70,
        expected_win=8.0,
        expected_loss=5.0,
        spread_cost=0.3,
        slippage_cost=0.2,
        commission_cost=0.1,
    )
    assert result.allow_trade is True
    assert result.reason == "QUANT_GATE_POSITIVE_EDGE"


def test_partial_economics_is_rejected():
    with pytest.raises(ValueError):
        evaluate_quant(PRICES, win_probability=0.7, expected_win=5.0)
