
import sys
import os
import backtrader as bt
import pandas as pd
import ccxt
from datetime import datetime, timedelta

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.strategies_complete import MTFScalperStrategy

from data.loader import DataLoader

import requests
import json

def fetch_data():
    """Fetch recent data using Hyperliquid API (High Fidelity)"""
    print("dl Fetching recent BTC data from Hyperliquid...")
    
    url = "https://api.hyperliquid.xyz/info"
    
    # Needs ~3200 candles for indicators. Hyperliquid gives max 5000 per request.
    # We want the latest 5000 candles.
    # EndTime is optional (defaults to now).
    # StartTime is optional? Actually usually we just ask for a window.
    # But 'candleSnapshot' might just give the last N candles if we don't specify strict bounds?
    # Let's try specifying a start time from ~60 days ago.
    
    # 60 days ago in ms
    start_time = int((pd.Timestamp.now() - pd.Timedelta(days=60)).timestamp() * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": "BTC",
            "interval": "15m",
            "startTime": start_time
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Hyperliquid returns list of: {'t': 163..., 'o': '...', 'h': '...', 'l': '...', 'c': '...', 'v': '...'}
        if not data:
            raise ValueError("No data returned from Hyperliquid")
            
        df = pd.DataFrame(data)
        
        # Rename columns to match Backtrader requirements
        # HL: t, o, h, l, c, v, n (count), s (quote volume?)
        # We need: datetime, open, high, low, close, volume
        
        df.rename(columns={
            't': 'timestamp', 
            'o': 'open', 
            'h': 'high', 
            'l': 'low', 
            'c': 'close', 
            'v': 'volume'
        }, inplace=True)
        
        # Clean types (they are strings)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        # Drop raw timestamp
        df.drop(columns=['timestamp', 'n', 's'], errors='ignore', inplace=True)
        
        # Sort just in case
        df.sort_index(inplace=True)
        
        # Save for inspection
        data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'BTC_15m_HL.csv')
        df.to_csv(data_path)
        print(f"✅ Data saved to {data_path}")
        print(f"   Range: {df.index[0]} to {df.index[-1]}")
        print(f"   Count: {len(df)} candles")
        return df
        
    except Exception as e:
        print(f"❌ Hyperliquid Fetch Error: {e}")
        raise e


class DiagnosticScalper(MTFScalperStrategy):
    def next(self):
        # Debug: Verify we are running
        if len(self) % 1000 == 0: print(f"Processing bar {len(self)}...")
        
        # 1. Base Logic
        check_dir = 0
        if self.rsi[0] < 50: check_dir = 1
        else: check_dir = -1
        
        if check_dir != 0:
            allowed, prob = self.check_ml(check_dir, self.data.close[0])
            
            # Log any potential setup > 50%
            if prob > 0.5:
                ts = self.data.datetime.datetime(0)
                print(f"🧐 [{ts}] Dir: {check_dir} | Conf: {prob:.2%}")
                
            # Original Logic: > 0.85
            if allowed and prob > 0.85:
                signal = check_dir
                print(f"🦅 MTF Scalper Signal: {signal} | Conf: {prob:.2%}")
                
                if signal == 1:
                    self.buy()
                    self.tp_price = self.data.close[0] * (1 + self.params.tp_pct/100)
                    self.sl_price = self.data.close[0] * (1 - self.params.sl_pct/100)
                elif signal == -1:
                    self.sell()
                    self.tp_price = self.data.close[0] * (1 - self.params.tp_pct/100)
                    self.sl_price = self.data.close[0] * (1 + self.params.sl_pct/100)
                    
        # Exit Management
        if self.position:
            if self.position.size > 0:
                if self.data.close >= self.tp_price: self.close()
                elif self.data.close <= self.sl_price: self.close()
            elif self.position.size < 0:
                if self.data.close <= self.tp_price: self.close()
                elif self.data.close >= self.sl_price: self.close()

def check_trades():
    print("🦅 Checking for missed trades since Jan 8th, 2026...")
    
    # Fetch Data
    try:
        df = fetch_data()
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return

    cerebro = bt.Cerebro()
    
    # Add Data
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Use Diagnostic Strategy
    cerebro.addstrategy(DiagnosticScalper)
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0006)
    
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    
    print("\n🚀 Running Simulation...")
    results = cerebro.run()
    strat = results[0]
    
    print("\n🔍 Trade Analysis (Since Jan 8th 2026):")
    print("="*60)
    
    # Check for open positions
    if strat.position:
        print(f"🚨 OPEN POSITION: Size: {strat.position.size} | Price: {strat.position.price}")
        trades_found = True
    
    analyzer = strat.analyzers.trades.get_analysis()
    
    # We need to extract individual trades if the analyzer doesn't give list easily
    # But strat._trades is available.
    
    trades_found = False
    
    start_check = pd.Timestamp("2026-01-08 00:00:00")
    
    # Iterate through all closed trades
    for date_key in strat._trades:
        trades = strat._trades[date_key]
        for trade in trades:
            trade_open_date = bt.num2date(trade.dtopen)
            if trade_open_date >= start_check:
                trades_found = True
                status = "WON" if trade.pnl > 0 else "LOST"
                print(f"[{trade_open_date}] {status} | PnL: ${trade.pnl:.2f} | Price: {trade.price:.2f}")

    # Find the very last trade
    last_trade = None
    last_trade_date = None
    
    for date_key in strat._trades:
        trades = strat._trades[date_key]
        for trade in trades:
            trade_open_date = bt.num2date(trade.dtopen)
            if last_trade_date is None or trade_open_date > last_trade_date:
                last_trade = trade
                last_trade_date = trade_open_date

    if last_trade:
        status = "WON" if last_trade.pnl > 0 else "LOST"
        print(f"\n🗓️ LAST TRADE FOUND:")
        print(f"   Date: {last_trade_date}")
        print(f"   Type: {status}")
        print(f"   Price: {last_trade.price:.2f}")
        print(f"   PnL: {last_trade.pnl:.2f}")
    else:
        print("\n🚫 No trades found in the entire period.")

    if not trades_found:
        print("\n🤷 No closed trades found since Jan 8th.")
        
    print("\n✅ Check Complete")

if __name__ == '__main__':
    check_trades()
