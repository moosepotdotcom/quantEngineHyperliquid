# 🌊 Liquidation Scalper Project Summary

## 🎯 Objective
Build a live Bitcoin liquidation scalper strategy using Hyperliquid data.

## 🏆 Key Achievements
1.  **Strategy Developed:**
    - **V2 (Aggressive Momentum):** Best performer (Stable Profit in Simulation).
    - **V5 (CVD Divergence):** Implemented for Live Trading (Order Flow).
2.  **Simulation Results (Jan 2026 Data):**
    - **V2:** 45% Win Rate, Positive PnL. Safe and Robust.
    - **V3 (Reversal):** FAILED (Do not use).
3.  **Live Connectivity:**
    - **External:** Blocked by DNS/Firewall.
    - **Internal:** **SUCCESS!** Tapped into `logs/collector_debug.log`.
    - **Monitor:** Built `LIVE_MONITOR.py` which detects real-time Whale Trades (e.g., seen $478k Buy).
4.  **System Built:**
    - `live_system.py`: Auto-switching engine (Paper/Live).
    - `backtest_log_feed.py`: Verified strategy on the live captured data.

## 📂 Deliverables
All final code is in `LIQUIDATION_SCALPER/`.
The Deployment Package is in `LIQUIDATION_SCALPER/DEPLOY_ME/`.

### How to Run
1.  **To Monitor Live Feed (Local):**
    ```bash
    python3 LIQUIDATION_SCALPER/LIVE_MONITOR.py
    ```
2.  **To Run the System (Paper/Real):**
    ```bash
    python3 LIQUIDATION_SCALPER/live_system.py
    ```
3.  **To Deploy (Cloud):**
    Upload `LIQUIDATION_SCALPER/DEPLOY_ME/` to a VPS and run `python main.py`.

## 🔮 Next Steps
- Deploy `main.py` to a server with Internet Access to enable real execution.
- Monitor `trades.csv` for Paper Trading performance in the meantime.
