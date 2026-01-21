import sys
import os
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quant_engine import TradingEngine, add_all_indicators

class MockCircuitBreaker:
    def __init__(self, engine, max_losses=2, window_minutes=60, cooldown_hours=4):
        self.engine = engine
        self.max_losses = max_losses
        self.window_minutes = window_minutes
        self.cooldown_hours = cooldown_hours
        self.losses = []
        self.cooldown_until = None
        
    def record_loss(self):
        now = self.engine.current_t
        self.losses = [t for t in self.losses if (now - t).total_seconds() < self.window_minutes * 60]
        self.losses.append(now)
        if len(self.losses) >= self.max_losses:
            self.trip()
            
    def trip(self):
        self.cooldown_until = self.engine.current_t + timedelta(hours=self.cooldown_hours)
        
    def reset(self):
        if not self.is_active():
            self.losses = []

    def is_active(self):
        if self.cooldown_until:
            if self.engine.current_t < self.cooldown_until:
                return True
            else:
                self.cooldown_until = None
                self.losses = []
        return False

class BacktestEngine(TradingEngine):
    def __init__(self, d5, d15, d1h, use_hurst=True, use_atr=True, use_ai_filter=True):
        super().__init__()
        self.d5 = d5
        self.d15 = d15
        self.d1h = d1h
        self.current_t = None
        
        # Filter toggles
        self.use_hurst_filter = use_hurst
        self.use_atr_penalty = use_atr
        self.use_ai_smart_filter = use_ai_filter
        
    def set_time(self, t):
        self.current_t = t
        
    def fetch_data(self, interval='5m', limit=500):
        if interval == '5m': df = self.d5
        elif interval == '15m': df = self.d15
        elif interval == '1h': df = self.d1h
        else: return None
        if df is None: return None
        mask = df.index <= self.current_t
        return df[mask].tail(limit).reset_index()

    def check_mtf_scalper(self):
        df_5m = self.fetch_data('5m', 500)
        if df_5m is None or len(df_5m) == 0:
            return None, 0.0
        
        try:
            from utils.advanced_features import get_rolling_hurst
            if 'hurst' not in df_5m.columns:
                df_5m['hurst'] = get_rolling_hurst(df_5m, window=100)
        except ImportError:
            df_5m['hurst'] = 0.5

        if 'timestamp' in df_5m.columns:
            df_5m.set_index('timestamp', inplace=True)
            
        df_15m = self.fetch_data('15m', 500)
        if df_15m is None or len(df_15m) == 0: return None, 0.0
        if 'timestamp' in df_15m.columns: df_15m.set_index('timestamp', inplace=True)
        
        exclude = ['open', 'high', 'low', 'close', 'volume']
        ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
        df_15m_renamed = df_15m[ctx_cols_15m].copy()
        df_15m_renamed.columns = [f"{c}_15m" for c in ctx_cols_15m]
        df_15m_resampled = df_15m_renamed.reindex(df_5m.index, method='ffill')
        df_5m = pd.concat([df_5m, df_15m_resampled], axis=1)
        
        df_1h = self.fetch_data('1h', 500)
        if df_1h is None or len(df_1h) == 0: return None, 0.0
        if 'timestamp' in df_1h.columns: df_1h.set_index('timestamp', inplace=True)
        
        ctx_cols_1h = [c for c in df_1h.columns if c not in exclude]
        df_1h_renamed = df_1h[ctx_cols_1h].copy()
        df_1h_renamed.columns = [f"{c}_1h" for c in ctx_cols_1h]
        df_1h_resampled = df_1h_renamed.reindex(df_5m.index, method='ffill')
        df_5m = pd.concat([df_5m, df_1h_resampled], axis=1)
        
        df_5m.dropna(inplace=True)
        if len(df_5m) == 0: return None, 0.0
        
        all_exclude = exclude + ['timestamp', 'hurst']
        features = [c for c in df_5m.columns if c not in all_exclude]
        latest = df_5m.iloc[-1]
        X = latest[features].values.reshape(1, -1)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        
        if X.shape[1] > 239: X = X[:, :239]
        
        probas = self.get_ensemble_proba('MTF', X)[0]
        prob_long = float(probas[1])
        prob_short = float(probas[2])
        
        direction = None
        confidence = 0.0
        
        self.mtf_elastic.update(prob_long, prob_short)
        
        if prob_long >= self.mtf_elastic.active_threshold_long:
            direction = 'LONG'
            confidence = prob_long
        elif prob_short >= self.mtf_elastic.active_threshold_short:
            direction = 'SHORT'
            confidence = prob_short
        
        if direction:
            price = float(latest['close'])
            if not price or price <= 0: return None, confidence
            
            # HURST FILTER (Falling Knife Detector)
            if self.use_hurst_filter:
                rsi = latest.get('rsi_14', 50)
                hurst = latest.get('hurst', 0.5)
                if direction == 'LONG' and rsi < 30 and hurst > 0.50:
                    return None, confidence
            
            # ATR PENALTY (Volatility Adaptation)
            if self.use_atr_penalty:
                atr_val = latest.get('atr_14', 50)
                required_conf = self.mtf_elastic.active_threshold_long if direction == 'LONG' else self.mtf_elastic.active_threshold_short
                
                if atr_val > 70:
                    penalty = (atr_val - 70) * 0.002
                    required_conf += penalty
                    
                if confidence < required_conf:
                    return None, confidence

            # AI SMART FILTER (Oversold Short Blocker)
            if self.use_ai_smart_filter:
                rsi7 = latest.get('rsi_7', 50)
                if direction == 'SHORT' and rsi7 < 25:
                    return None, confidence
            
            return {
                'model': 'MTF Scalper (5M)',
                'timestamp': self.current_t if self.current_t else datetime.now(),
                'price': price,
                'direction': direction,
                'confidence': confidence,
                'rsi': float(latest.get('rsi_14', 0)),
                'macd': float(latest.get('macd', 0)),
                'atr_pct': (float(latest.get('atr_14', 0)) / price * 100) if price > 0 else 0
            }, confidence
        
        return None, max(prob_long, prob_short)

def run_backtest_with_config(df_5m, df_15m, df_1h, use_hurst, use_atr, use_ai, config_name):
    """Run backtest with specific filter configuration"""
    
    mock_engine = BacktestEngine(df_5m, df_15m, df_1h, use_hurst, use_atr, use_ai)
    mock_cb = MockCircuitBreaker(mock_engine)
    mock_engine.circuit_breaker = mock_cb

    start_date = "2026-01-02 00:00:00"
    end_date = "2026-01-11 23:59:59"
    
    mask = (df_5m.index >= start_date) & (df_5m.index <= end_date)
    sim_candles = df_5m[mask]
    
    trades = []
    current_position = None
    
    for i, (timestamp, row) in enumerate(sim_candles.iterrows()):
        mock_engine.set_time(timestamp)
        
        # Check if position open
        if current_position is not None:
            entry_price = current_position['price']
            tp_price = current_position['tp']
            sl_price = current_position['sl']
            direction = current_position['dir']
            
            h, l = row['high'], row['low']
            
            if direction == 'LONG':
                if h >= tp_price:
                    outcome = 'WIN'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
                elif l <= sl_price:
                    outcome = 'LOSS'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
            else:  # SHORT
                if l <= tp_price:
                    outcome = 'WIN'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
                elif h >= sl_price:
                    outcome = 'LOSS'
                    current_position['outcome'] = outcome
                    current_position['exit_time'] = timestamp
                    trades.append(current_position.copy())
                    mock_engine.report_outcome('MTF', outcome)
                    current_position = None
                    continue
            continue
        
        # Check circuit breaker
        if mock_engine.circuit_breaker.is_active():
            continue
        
        # Check for signals
        signal, conf = mock_engine.check_mtf_scalper()
        
        if signal:
            entry_price = signal['price']
            direction = signal['direction']
            tp_pct = 0.015
            sl_pct = 0.008
            
            if direction == 'LONG':
                tp_p = entry_price * (1+tp_pct)
                sl_p = entry_price * (1-sl_pct)
            else:
                tp_p = entry_price * (1-tp_pct)
                sl_p = entry_price * (1+sl_pct)
            
            current_position = {
                'time': timestamp,
                'dir': direction,
                'conf': conf,
                'price': entry_price,
                'tp': tp_p,
                'sl': sl_p,
                'outcome': 'OPEN'
            }
    
    # Calculate results
    total = len(trades)
    if total > 0:
        wins = len([t for t in trades if t['outcome']=='WIN'])
        losses = len([t for t in trades if t['outcome']=='LOSS'])
        win_rate = wins/total*100
    else:
        wins = 0
        losses = 0
        win_rate = 0
    
    return {
        'config': config_name,
        'total': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'trades': trades
    }

def main():
    print("\n" + "="*70)
    print("🧪 FILTER COMBINATION TESTING")
    print("="*70)
    
    # Fetch data once
    print("\n📥 Fetching Data...")
    engine = TradingEngine()
    df_raw = engine.fetch_data('5m', 4000)
    
    if df_raw is None:
        print("❌ Failed to fetch data")
        return
    
    df_raw.sort_values('timestamp', inplace=True)
    df_5m = add_all_indicators(df_raw)
    df_15m = add_all_indicators(engine.fetch_data('15m', 4000))
    df_1h = add_all_indicators(engine.fetch_data('1h', 4000))
    
    for df in [df_5m, df_15m, df_1h]:
        if df is not None and 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True)
    
    del engine
    
    print("✅ Data loaded\n")
    
    # Test configurations
    configs = [
        # (use_hurst, use_atr, use_ai, name)
        (True, True, True, "ALL FILTERS ON (Default)"),
        (False, True, True, "NO HURST"),
        (True, False, True, "NO ATR PENALTY"),
        (True, True, False, "NO AI FILTER"),
        (False, False, True, "ONLY AI FILTER"),
        (False, True, False, "ONLY ATR PENALTY"),
        (True, False, False, "ONLY HURST"),
        (False, False, False, "NO FILTERS"),
    ]
    
    results = []
    
    for use_hurst, use_atr, use_ai, name in configs:
        print(f"🔄 Testing: {name}...")
        result = run_backtest_with_config(df_5m, df_15m, df_1h, use_hurst, use_atr, use_ai, name)
        results.append(result)
        print(f"   ✅ {result['total']} trades | {result['wins']}W/{result['losses']}L | {result['win_rate']:.1f}% WR\n")
    
    # Print comparison table
    print("\n" + "="*70)
    print("📊 RESULTS COMPARISON")
    print("="*70)
    print(f"{'Configuration':<30} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'Win Rate':<10}")
    print("-"*70)
    
    for r in results:
        print(f"{r['config']:<30} {r['total']:<8} {r['wins']:<6} {r['losses']:<8} {r['win_rate']:.1f}%")
    
    print("="*70)
    
    # Find best configuration
    best_wr = max(results, key=lambda x: x['win_rate'] if x['total'] > 0 else 0)
    most_trades = max(results, key=lambda x: x['total'])
    
    print(f"\n🏆 BEST WIN RATE: {best_wr['config']} ({best_wr['win_rate']:.1f}%)")
    print(f"📈 MOST TRADES: {most_trades['config']} ({most_trades['total']} trades)")
    
    # Calculate P&L for best configs
    print("\n" + "="*70)
    print("💰 P&L ANALYSIS (with $53 capital, 27x leverage)")
    print("="*70)
    
    capital = 53
    leverage = 27
    buying_power = capital * leverage
    
    for r in results:
        if r['total'] > 0:
            pnl_per_win = buying_power * 0.015
            pnl_per_loss = buying_power * -0.008
            total_pnl = (r['wins'] * pnl_per_win) + (r['losses'] * pnl_per_loss)
            final_balance = capital + total_pnl
            roi = (total_pnl / capital) * 100
            
            print(f"\n{r['config']}:")
            print(f"  Total P&L: ${total_pnl:+.2f}")
            print(f"  Final Balance: ${final_balance:.2f}")
            print(f"  ROI: {roi:+.1f}%")

if __name__ == "__main__":
    main()
