# Abutron Quantitative Mathematics Engine — Phase 1

Status: **shadow/telemetry only**. This phase does not place orders and is not wired into MT5 execution.

## Implemented

- Log returns
- Sample return variance / volatility
- Realized variance and realized volatility
- Upside/downside semivariance
- Return z-score
- Lag-1 autocorrelation
- EWMA volatility
- Transaction-cost-aware expected value gate

## Production rule

Quantitative outputs must be recorded and validated out-of-sample before they are permitted to alter BUY/SELL/HOLD, sizing, or execution.

## Next integration stages

1. Feed deterministic snapshots from broker OHLC data into Kronos/Fusion telemetry.
2. Persist feature snapshots and realized outcomes.
3. Add probability calibration (Brier/log-loss/reliability buckets).
4. Add regime and covariance exposure modules.
5. Add execution-cost estimates.
6. Promote individual features to decision gates only after walk-forward/OOS validation.
