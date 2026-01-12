#!/usr/bin/env python3
"""
Scalp Fuzzer
==============
This script performs feature engineering on 15‑minute BTC‑USD data and uses a simple
parameter‑fuzzing approach to discover scalping strategies with positive returns.
It builds on the existing `strategy_fuzzer.py` but focuses on high‑frequency
(5‑15 min) setups.

The workflow:
1. Load 15 min OHLCV data.
2. Generate technical features via `feature_generator.py`.
3. Define a generic `ScalpStrategy` that uses a few tunable indicator thresholds.
4. Run a grid‑search over those parameters using Backtrader's optimisation API.
5. Collect and print the best‑performing configurations.
"""

import os
import sys
import json
import logging
from datetime import datetime
import pandas as pd
import backtrader as bt
from tabulate import tabulate

# Ensure project root is on sys.path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

# Import the feature generator used elsewhere in the repo
try:
    from research.feature_generator import AdvancedFeatureGenerator
except Exception as e:
    logging.error(f"Failed to import AdvancedFeatureGenerator: {e}")
    raise

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ScalpStrategy(bt.Strategy):
    """A simple scalping strategy with tunable parameters.

    Parameters (all can be fuzzed):
        rsi_period   – period for the RSI indicator
        rsi_thresh   – upper threshold for a short‑signal (ignored for scalping)
        bb_period    – Bollinger Bands period
        bb_dev       – Standard‑deviation multiplier
        sl_pct       – Stop‑loss as % of entry price
        tp_pct       – Take‑profit as % of entry price
    """

    params = dict(
        bb_period=20,
        bb_dev=2.0,
        adx_period=14,
        adx_thresh=25,
        sl_pct=1.5,
        tp_pct=4.0,
    )

    def __init__(self):
        # Technical indicators
        self.bb = bt.indicators.BollingerBands(self.data.close, period=self.p.bb_period, devfactor=self.p.bb_dev)
        self.adx = bt.indicators.AverageDirectionalMovementIndex(self.data, period=self.p.adx_period)
        self.order = None
        self.entry_price = None

    def next(self):
        # Momentum Breakout: Buy if price breaks Upper BB AND ADX shows trend
        if not self.position:
            if self.data.close[0] > self.bb.top[0] and self.adx[0] > self.p.adx_thresh:
                self.order = self.buy()
                self.entry_price = self.data.close[0]
        else:
            # Manage exit via SL/TP
            pnl_pct = (self.data.close[0] - self.entry_price) / self.entry_price * 100
            if pnl_pct >= self.p.tp_pct or pnl_pct <= -self.p.sl_pct:
                self.close()

    def stop(self):
        # Quick progress indicator
        print(f".", end="", flush=True)


def run_fuzzer(data_path, cash=10000, max_workers=1):
    logger.info("🚀 Starting Scalp Fuzzer on 15m data")
    # Load raw data
    df = pd.read_csv(data_path)
    # Ensure datetime index
    # Determine the correct datetime column name
    if "datetime" in df.columns:
        time_col = "datetime"
    elif "timestamp" in df.columns:
        time_col = "timestamp"
    else:
        time_col = "time"
    df[time_col] = pd.to_datetime(df[time_col])
    df.set_index(time_col, inplace=True)
    # Feature engineering (adds many columns but we keep original OHLCV for Backtrader)
    gen = AdvancedFeatureGenerator(df)
    df_feat = gen.generate_all()
    # Backtrader expects specific column names
    df_feat.rename(columns=lambda c: c.lower(), inplace=True)
    # Create data feed
    data = bt.feeds.PandasData(dataname=df_feat)

    # Define parameter ranges for fuzzing
    opt_params = dict(
        bb_period=[20],
        bb_dev=[2.0],
        adx_thresh=[20, 25, 30, 40],
        sl_pct=[1.0, 2.0, 3.0],
        tp_pct=[2.0, 4.0, 6.0, 8.0],
    )

    cerebro = bt.Cerebro(optreturn=True)
    cerebro.optstrategy(ScalpStrategy, **opt_params)
    cerebro.adddata(data)
    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(commission=0.0006)  # Binance taker fee approx.
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

    results = cerebro.run(maxcpus=max_workers)
    # Gather best results (positive net profit)
    best = []
    for run in results:
        for strat in run:
            trades = strat.analyzers.trades.get_analysis()
            net = trades.get("pnl", {}).get("net", {}).get("total", 0)
            if net > 0:
                best.append({
                    "params": strat.params.__dict__,
                    "net_profit": net,
                    "profit_pct": net / cash * 100,
                    "sharpe": strat.analyzers.sharpe.get_analysis().get("sharperatio", 0),
                    "drawdown": strat.analyzers.drawdown.get_analysis().get("max", {}).get("drawdown", 0),
                    "total_trades": trades.get("total", {}).get("total", 0),
                })
    # Sort by profit
    best.sort(key=lambda x: x["net_profit"], reverse=True)
    if best:
        logger.info(f"✅ Found {len(best)} profitable configurations")
        table = []
        for b in best[:10]:
            table.append([
                json.dumps(b["params"]),
                f"{b['net_profit']:.2f}",
                f"{b['profit_pct']:.2f}%",
                f"{b['sharpe']:.2f}",
                f"{b['drawdown']:.2f}%",
                b["total_trades"],
            ])
        print(tabulate(table, headers=["Params", "Net $", "% Profit", "Sharpe", "DD%", "Trades"], tablefmt="grid"))
    else:
        logger.warning("⚠️ No profitable configuration found in the search space.")

    # Save full results for later ML usage
    out_path = os.path.join(os.path.dirname(data_path), "scalp_fuzzer_results.json")
    with open(out_path, "w") as f:
        json.dump(best, f, indent=4)
    logger.info(f"📁 Results saved to {out_path}")


if __name__ == "__main__":
    data_file = os.path.abspath(os.path.join(PROJECT_ROOT, "datasets", "BTCUSD-15m-max-data.csv"))
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        sys.exit(1)
    run_fuzzer(data_file)
