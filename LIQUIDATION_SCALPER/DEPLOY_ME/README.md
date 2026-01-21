# 🌊 Liquidation Scalper (Live Deployment)

## Overview
This bot scalps Bitcoin (BTC) on Hyperliquid DEX by detecting large liquidation cascades and riding the momentum.

## Strategy (V2 Aggressive)
- **Signal:** Liquidation Proxy Score >= 4 (Volume Spike + Wick).
- **Direction:** Trend Following (Green Candle -> Buy, Red Candle -> Sell).
- **Settings:** Take Profit 0.2%, Stop Loss 0.1%.

## How to Deploy
1.  **Environment:** Ensure you have Python 3.9+ and unrestricted internet access.
2.  **Install:** `pip install -r requirements.txt`
3.  **Run:** `python main.py`

## Note
This script automatically detects if it can connect to Hyperliquid. If network is blocked (like in some restricted containers), it falls back to Simulation Mode.
On a real server (AWS, GCP, Local), it will connect to the WebSocket and trade live.
