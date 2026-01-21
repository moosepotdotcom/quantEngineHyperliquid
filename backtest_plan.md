# Backtest Suite Plan

## Objective
Compare performance of isolated model engines on recent historical data (Jan 2026) to identify the best configuration for live trading.

## Constraints
- **Single Trade**: Only one position active at a time.
- **Fixed Size**: All trades use fixed size (e.g., $1000 or 1.0 BTC equivalent for simplicity in pnl calc, or % based).
- **Fees**: Include 0.04% taker fee/slippage estimate per trade.

## Data Source
- Use existing CSVs in `data/` (e.g., `BTC_5m_Jan2_11.csv`, `BTC_1h_Jan2_11.csv`).
- If missing, fetch using `utils/fetch_data.py`.

## Implementation: `backtest_suite.py`

### logic
1. Load `Connector` and discover models.
2. Load historical DataFrames for 5m, 15m, 1h, 30m.
3. Align timestamps (Index alignment).
4. Iterate through time (Tick by Tick simulation).
5. **Portfolio Manager Class**:
   - Tracks `current_position` (None, 'LONG', 'SHORT').
   - Tracks `balance`.
   - Rejects new signals if `current_position` is not None.
   - Exits position on Stop Loss / Take Profit hits (Simulated using High/Low of subsequent candles).
6. **Reporting**:
   - Output summary table: Model Name | Trades | Win Rate | PnL | Max Drawdown.

## Execution
Run `python3 backtest_suite.py` and analyze results.
