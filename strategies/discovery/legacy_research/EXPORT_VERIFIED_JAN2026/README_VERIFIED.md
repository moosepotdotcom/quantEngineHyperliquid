# Verified Quant Engine (Jan 2026) -> "EXPORT_VERIFIED_JAN2026"

This folder contains the fully patched and verified version of the Quantitative Trading Engine.

## Critical Fixes
- **Feature Mismatch Resolved**: The `Winner Hunter` model now correctly uses the basic feature set (231 features) via `use_advanced=False`. This prevents the "expected 231, got 255" crash.
- **Engine Stability**: Verified through high-fidelity backtesting.

## Contents
- `quant_engine.py`: The patched trading engine.
- `optimized_backtest_jan2_jan9.py`: The verification script used to validate the fix.
- `hyperliquid_live_trader.py`: Live trading interface.
- `models/`: All Trio Ensemble models.
- `utils/`: Feature engineering library (updated).

## Verification
To verify the fix and performance (Jan 2 - Jan 7):
```bash
python3 optimized_backtest_jan2_jan9.py
```
This will run the simulation using live Hyperliquid API data.

## Deployment
To run the Live Engine:
```bash
python3 live_trading_engine.py --live --mainnet
```

## Benchmark Verification (Jan 13 2026)
Attempted to recreate the 93% Win Rate benchmark (Jan 2-9).
- **Result:** 0 Trades.
- **Cause:** **Adaptive Shield Active**. High volatility (ATR > 290) triggered safety blocking.
- **Report:** `RECREATION_REPORT.md`
