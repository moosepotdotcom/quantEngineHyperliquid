
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import collections

# Add root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

from main_connector import MainConnector
from utils.fetch_data import fetch_live_data

# ===========================
# CONFIGURATION
# ===========================
# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
SYMBOL = 'BTC'
START_DATE = '2026-01-02'
END_DATE = '2026-01-14'
INITIAL_CAPITAL = 10000
POSITION_SIZE = 10000 # All in
LEVERAGE = 1
TAKER_FEE = 0.0004 # 0.04%
SLIPPAGE = 0.0001 # 0.01%

# Which models to test?
MODELS_TO_TEST = [
    # 'MTF Scalper V2',       # Legacy
    # 'Winner Hunter (1H)',   # Benchmark
    'MTF Scalper V3'        # NEW Isolated Strategy
]

class PortfolioManager:
    def __init__(self):
        self.balance = INITIAL_CAPITAL
        self.position = None # {type: LONG/SHORT, price: float, size: float, tp: float, sl: float, model: str}
        self.trades = []
        self.equity_curve = []

    def check_exit(self, candle):
        """Check if TP or SL hit in the current candle"""
        if not self.position: return

        low = candle['low']
        high = candle['high']
        close = candle['close'] # Use close for EOM exit if needed, or stick to intra-candle
        ts = candle['timestamp']
        
        p = self.position
        exit_price = None
        exit_reason = None
        pnl = 0

        # Logic for LONG
        if p['type'] == 'LONG':
            if low <= p['sl']:
                exit_price = p['sl']
                exit_reason = 'STOP_LOSS'
            elif high >= p['tp']:
                exit_price = p['tp']
                exit_reason = 'TAKE_PROFIT'
        
        # Logic for SHORT
        elif p['type'] == 'SHORT':
            if high >= p['sl']:
                exit_price = p['sl']
                exit_reason = 'STOP_LOSS'
            elif low <= p['tp']:
                exit_price = p['tp']
                exit_reason = 'TAKE_PROFIT'

        if exit_price:
            # Calculate PnL
            if p['type'] == 'LONG':
                raw_pnl = (exit_price - p['price']) / p['price']
            else:
                raw_pnl = (p['price'] - exit_price) / p['price']
            
            # Apply Fees & Slippage
            # Fee on entry + Fee on exit
            total_fee = TAKER_FEE + TAKER_FEE
            
            # Slippage on exit (entry assumed limit/market filled at signal price for simple sim, or add slippage there too)
            # Let's apply simple net PnL adjustment
            net_pnl_pct = raw_pnl - total_fee - SLIPPAGE
            
            realized_pnl = p['size'] * net_pnl_pct
            self.balance += realized_pnl
            
            self.trades.append({
                'entry_time': p['time'],
                'exit_time': ts,
                'model': p['model'],
                'type': p['type'],
                'entry_price': p['price'],
                'exit_price': exit_price,
                'reason': exit_reason,
                'raw_pnl_pct': raw_pnl,
                'net_pnl': realized_pnl,
                'balance': self.balance
            })
            
            self.position = None

    def execute_signal(self, signal):
        """Try to open a position"""
        if self.position: return # One trade at a time rule
        
        price = signal['price']
        model = signal['model']
        direction = signal['direction']
        
        # Risk Management (Fixed for standard comparison)
        tp_pct = 0.015 # 1.5%
        sl_pct = 0.008 # 0.8%
        
        if direction == 'LONG':
            tp = price * (1 + tp_pct)
            sl = price * (1 - sl_pct)
        else:
            tp = price * (1 - tp_pct)
            sl = price * (1 + sl_pct)
            
        self.position = {
            'type': direction,
            'price': price,
            'size': POSITION_SIZE,
            'tp': tp,
            'sl': sl,
            'time': signal['timestamp'],
            'model': model
        }

def run_backtest():
    print("🚀 Starting Comprehensive Backtest...")
    print(f"📅 Period: {START_DATE} to {END_DATE}")
    print(f"💰 Capital: ${INITIAL_CAPITAL}")
    
    # 1. Setup Connector & Models
    connector = MainConnector()
    connector.discover_and_load_models()
    
    # 2. Fetch Data (5m is base for simulation tick)
    print("\n📥 Fetching Data...")
    start_dt = pd.Timestamp(START_DATE).tz_localize('UTC')
    end_dt = pd.Timestamp(END_DATE).tz_localize('UTC') + pd.Timedelta(days=1)
    
    limit = int((end_dt - start_dt).total_seconds() / 300) + 1000 # Buffer
    print(f"   Requested candles: {limit}")
    
    # Fetch all timeframes needed
    data_store = {}
    timeframes = ['5m', '15m', '30m', '1h']
    
    for tf in timeframes:
        params_limit = min(limit, 10000) # Safety cap
        if tf == '1h': params_limit = min(limit // 12, 5000)
        
        df = fetch_live_data("BTC", tf, limit=params_limit) 
        if df is not None:
             # Ensure timestamp is datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            # Filter by date
            df = df[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)]
            
            # OPTIMIZATION: Pre-calculate indicators on full history once
            from utils.feature_engineer import add_all_indicators
            print(f"   ⚡ Pre-calculating indicators for {tf}...")
            df = add_all_indicators(df)
            
            data_store[tf] = df.sort_values('timestamp').reset_index(drop=True)
            print(f"   ✅ {tf}: {len(df)} rows (Optimized)")
        else:
            print(f"   ❌ {tf}: Failed to fetch")
            return
            
    # ==========================================
    # 4. THRESHOLD OPTIMIZATION LOOP
    # ==========================================
    print("\n⚡ Running Threshold Optimization...")
    
    # Store predictions for re-use
    # Structure: { 'ModelName': { 'timestamps': [], 'prices': [], 'probs': [[p_regime, p_long, p_short], ...] } }
    predictions_cache = {}
    
    # --- Capture MTF Scalper V2 Predictions ---
    if 'MTF Scalper V2' in MODELS_TO_TEST:
        try:
            eng = [m for m in connector.models if m.name == 'MTF Scalper V2'][0]
            logic = eng.logic
            
            # Use MTFFeatureGenerator to ensure exact 231 features
            from utils.mtf_feature_engineer import MTFFeatureGenerator
            
            # Reset indices just in case
            t_5m = data_store['5m'].reset_index(drop=True)
            t_15m = data_store['15m'].reset_index(drop=True)
            t_30m = data_store['30m'].reset_index(drop=True)
            
            # Generator expects standard column names
            # Data Store already has indicators, but generator handles that.
            # Generator generates mapping using timestamps. But here we passed non-indexed dfs?
            # Let's check generator code: it assumes columns are ['timestamp', ...].
            # FeatureEngineer `add_all_indicators` returns DF with timestamp column if it was there.
            
            gen = MTFFeatureGenerator(t_5m, t_15m, t_30m)
            X_feat, price_df = gen.generate()
            
            # Sanitize (Match training)
            X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # Predict
            # X_feat has the 231 columns.
            probs = logic.model_v2.predict_proba(X_feat.values)
            
            predictions_cache['MTF Scalper V2'] = {
                'timestamps': price_df.index, # Generate returns DF with DateTimeIndex
                'prices': price_df['close'].values,
                'probs': probs
            }
        except Exception as e:
            print(f"❌ V2 Pred Failed: {e}")
            import traceback
            traceback.print_exc()

    # --- Capture Winner Hunter Predictions ---
    if 'Winner Hunter (1H)' in MODELS_TO_TEST:
        try:
            eng = [m for m in connector.models if m.name == 'Winner Hunter (1H)'][0]
            logic = eng.logic
            df_1h = data_store['1h'].set_index('timestamp')
            # ... (Existing feature construction code) ...
            from model_engines.winner_hunter_1h.logic import MTF_FEATURE_LIST
            df_5m = data_store['5m'].set_index('timestamp')
            df_15m = data_store['15m'].set_index('timestamp')
            
            exclude = ['open', 'high', 'low', 'close', 'volume']
            cols_5m = [c for c in df_5m.columns if c not in exclude]
            cols_15m = [c for c in df_15m.columns if c not in exclude]
            
            df_5m_renamed = df_5m[cols_5m].add_suffix('_1h')
            df_15m_renamed = df_15m[cols_15m].add_suffix('_15m')
            
            aligned_5m = df_5m_renamed.reindex(df_1h.index, method='ffill')
            aligned_15m = df_15m_renamed.reindex(df_1h.index, method='ffill')
            
            X_df = pd.DataFrame(index=df_1h.index)
            for feat in MTF_FEATURE_LIST:
                if feat.endswith('_15m'):
                    X_df[feat] = aligned_15m.get(feat, 0.0)
                elif feat.endswith('_1h'):
                    X_df[feat] = aligned_5m.get(feat, 0.0)
                else:
                    X_df[feat] = df_1h.get(feat, 0.0)
            
            X_vals = np.nan_to_num(X_df.values, nan=0.0)
            probs = logic.get_ensemble_proba(X_vals)
            
            predictions_cache['Winner Hunter (1H)'] = {
                'timestamps': df_1h.index,
                'prices': df_1h['close'].values,
                'probs': probs
            }
        except Exception as e:
            print(f"❌ WH Pred Failed: {e}")

    # --- Capture MTF Scalper V3 Predictions ---
    if 'MTF Scalper V3' in MODELS_TO_TEST:
        try:
            eng = [m for m in connector.models if m.name == 'MTF Scalper V3'][0]
            logic = eng.logic
            
            # Use MTFFeatureGenerator
            from utils.mtf_feature_engineer import MTFFeatureGenerator
            
            t_5m = data_store['5m'].reset_index(drop=True)
            t_15m = data_store['15m'].reset_index(drop=True)
            t_30m = data_store['30m'].reset_index(drop=True)
            
            gen = MTFFeatureGenerator(t_5m, t_15m, t_30m)
            X_feat, price_df = gen.generate()
            
            # Sanitize (Match training)
            X_feat = X_feat.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # Predict (V3 Logic uses self.model)
            # Model is XGBClassifier: [neutral, long, short]
            probs = logic.model.predict_proba(X_feat.values)
            
            predictions_cache['MTF Scalper V3'] = {
                'timestamps': price_df.index,
                'prices': price_df['close'].values,
                'probs': probs
            }
        except Exception as e:
            print(f"❌ V3 Pred Failed: {e}")
            import traceback
            traceback.print_exc()

    # --- Run Simulations for Multiple Thresholds ---
    thresholds = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    
    results_table = []
    base_df = data_store['5m'].sort_values('timestamp') # Clock
    
    print(f"\n{'Model':<20} | {'Thresh':<6} | {'Trades':<6} | {'Win%':<6} | {'PnL ($)':<10}")
    print("-" * 65)
    
    for model_name in predictions_cache:
        data = predictions_cache[model_name]
        timestamps = data['timestamps']
        prices = data['prices']
        probs = data['probs']
        
        for thresh in thresholds:
            # 1. Generate Signals
            current_signals = []
            
            # Vectorized threshold check
            # Handle 2-class vs 3-class output
            if probs.shape[1] == 2:
                # Binary: Class 0 = Short, Class 1 = Long (Based on logic.py return probs[1], probs[0])
                prob_long_arr = probs[:, 1]
                prob_short_arr = probs[:, 0]
            else:
                # 3-Class: 0=Neutral, 1=Long, 2=Short
                prob_long_arr = probs[:, 1]
                prob_short_arr = probs[:, 2]

            long_mask = prob_long_arr >= thresh
            short_mask = prob_short_arr >= thresh
            
            # Combine indices
            for i in np.where(long_mask)[0]:
                current_signals.append({
                    'timestamp': timestamps[i],
                    'model': model_name,
                    'direction': 'LONG',
                    'price': prices[i],
                    'confidence': prob_long_arr[i]
                })
            for i in np.where(short_mask)[0]:
                current_signals.append({
                    'timestamp': timestamps[i],
                    'model': model_name,
                    'direction': 'SHORT',
                    'price': prices[i],
                    'confidence': prob_short_arr[i]
                })
                
            current_signals.sort(key=lambda x: x['timestamp'])
            
            # 2. Simulate
            pm = PortfolioManager()
            
            # Quick Map
            sig_map = collections.defaultdict(list)
            for s in current_signals:
                sig_map[s['timestamp']].append(s)
            
            # Event Loop
            for i, row in base_df.iterrows():
                pm.check_exit(row)
                if not pm.position:
                    ts = row['timestamp']
                    # Look up signals
                    # Note: Signal timestamps match the data frequency (5m or 1h)
                    # For 1H signals, they align with specific 5m candles (on the hour)
                    if ts in sig_map:
                        for s in sig_map[ts]:
                            pm.execute_signal(s)
                            if pm.position: break
            
            # 3. Metrics
            wins = [t for t in pm.trades if t['net_pnl'] > 0]
            n_trades = len(pm.trades)
            win_rate = (len(wins) / n_trades * 100) if n_trades > 0 else 0
            pnl = pm.balance - INITIAL_CAPITAL
            
            print(f"{model_name:<20} | {thresh:<6.2f} | {n_trades:<6} | {win_rate:<6.1f} | ${pnl:<10.2f}")
            results_table.append({
                'model': model_name, 'thresh': thresh, 
                'trades': n_trades, 'wr': win_rate, 'pnl': pnl
            })

if __name__ == "__main__":
    run_backtest()
