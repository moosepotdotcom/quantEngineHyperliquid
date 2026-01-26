# 🚀 Renaissance HFT: Production V1

This is the high-performance, deployment-ready version of the **Renaissance HFT Engine**. It is optimized for live execution on Hyperliquid with minimal latency and maximal reliability.

## 🚀 Quick Start
1.  **Dependencies**: `pip install hyperliquid xgboost pandas numpy requests joblib`
2.  **Credentials**: Fill out your `.env` (see `DEPLOYMENT_GUIDE.md`).
3.  **Deploy**: `python3 live_trading_engine.py --live --mainnet`

## 🛡️ Safe Operating Limits
The engine is pre-configured with the following verified guardrails:
- **Win Rate Target**: ~87%
- **Leverage Ceiling**: 5.0x
- **Slot Model**: Single-Position Only (Locks equity until exit)
- **Exit Logic**: Trailing Take Profit (TTP) enabled.

## 📚 Technical Docs
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)**: Setup and operation instructions.
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Neural logic and feature engineering details.

**Status**: Ready for Live Production 🛰️🏛️🏆⚖️
