# Kronos Quant Integration v4.2

## Safety contract

The quantitative engine is an enrichment layer. It does **not** replace or bypass:

Kronos -> Fusion -> Confidence -> Thesis -> BUY/SELL/HOLD -> Risk -> Capital -> Equity Router -> Bot -> MT5.

Default mode is `SHADOW`. Shadow output is telemetry only and must not alter live execution.

Modes:

- `OFF`: feature computation available; no gating.
- `SHADOW`: compute and record features/outcomes; existing pipeline remains authoritative.
- `GATE`: may only veto a trade on non-positive calibrated net expectancy. It never creates a BUY/SELL signal and never bypasses downstream safety gates.

## Promotion requirements

Do not promote GATE to production until Abutron-specific data passes:
1. deterministic unit/contract tests;
2. out-of-sample and walk-forward validation;
3. transaction-cost/slippage stress;
4. probability calibration;
5. live shadow comparison;
6. signed production acceptance gates.

Execution flags remain OFF during integration certification.
