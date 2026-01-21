#!/usr/bin/env python3
"""
HYBRID STRATEGY: V8 + Liquidation Boost
Use V8's proven 83.82% WR model
Add liquidation proximity as confidence booster
"""

import pandas as pd
import numpy as np
import joblib
from datetime import timedelta

class V8LiquidationHybrid:
    """Enhance V8 with liquidation awareness"""
    
    def __init__(self, model_path='../PRODUCTION_93WR_OPTIMIZED/v8_simple_model.pkl'):
        # Load V8 model
        self.model = joblib.load(model_path)
        
        # V8 params (from production)
        self.confidence_threshold = 0.65
        self.tp_pct = 0.004  # 0.4%
        self.sl_pct = 0.002  # 0.2%
        
        # Liquidation boost params
        self.liq_proximity_pct = 0.03  # Within 3% of liquidation
        self.liq_boost_multiplier = 1.5  # 1.5x confidence if near liquidation
    
    def check_liquidation_proximity(self, current_price, df_liquidations, current_time):
        """Check if price is near recent liquidation"""
        cutoff = current_time - timedelta(hours=2)
        recent = df_liquidations[df_liquidations['timestamp'] > cutoff]
        
        if len(recent) == 0:
            return False, None
        
        for _, liq in recent.iterrows():
            distance_pct = abs(liq['price'] - current_price) / current_price
            
            if distance_pct <= self.liq_proximity_pct:
                # Near liquidation level
                direction = 'long_liq' if liq['side'] == 'A' else 'short_liq'
                return True, direction
        
        return False, None
    
    def generate_signal(self, row, df_liquidations, current_time):
        """Generate V8 signal with liquidation boost"""
        
        # Get V8 prediction
        features = row[['rsi', 'bb_position', 'volume_surge', 'price_velocity', 
                       'volatility', 'trend_strength']].values.reshape(1, -1)
        
        proba = self.model.predict_proba(features)[0]
        
        # Get base signal
        if proba[2] > self.confidence_threshold:  # LONG
            base_signal = 'LONG'
            confidence = proba[2]
        elif proba[0] > self.confidence_threshold:  # SHORT
            base_signal = 'SHORT'
            confidence = proba[0]
        else:
            return None
        
        # Check liquidation proximity
        near_liq, liq_dir = self.check_liquidation_proximity(
            row['close'], df_liquidations, current_time
        )
        
        # Boost confidence if aligned
        if near_liq:
            if base_signal == 'LONG' and liq_dir == 'long_liq':
                # V8 says LONG + near long liquidation = STRONG BUY
                confidence *= self.liq_boost_multiplier
                boosted = True
            elif base_signal == 'SHORT' and liq_dir == 'short_liq':
                # V8 says SHORT + near short liquidation = STRONG SELL
                confidence *= self.liq_boost_multiplier
                boosted = True
            else:
                boosted = False
        else:
            boosted = False
        
        # Generate trade
        entry = row['close']
        if base_signal == 'LONG':
            tp = entry * (1 + self.tp_pct)
            sl = entry * (1 - self.sl_pct)
        else:
            tp = entry * (1 - self.tp_pct)
            sl = entry * (1 + self.sl_pct)
        
        return base_signal, entry, tp, sl, confidence, boosted

def backtest_v8_liquidation_hybrid(df_price, df_liquidations, fee_pct=0.001):
    """Backtest V8 + Liquidation hybrid"""
    
    print("🎯 BACKTESTING: V8 + Liquidation Hybrid")
    print("="*70)
    print("   Base: V8 model (83.82% WR)")
    print("   Boost: 1.5x confidence when near liquidation")
    print()
    
    strategy = V8LiquidationHybrid()
    
    trades = []
    active_trade = None
    
    for i in range(len(df_price)):
        row = df_price.iloc[i]
        current_time = row['timestamp']
        
        # Manage active trade
        if active_trade:
            if active_trade['direction'] == 'LONG':
                if row['high'] >= active_trade['tp']:
                    pnl_pct = strategy.tp_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct,
                        'boosted': active_trade['boosted']
                    })
                    active_trade = None
                    continue
                elif row['low'] <= active_trade['sl']:
                    pnl_pct = -strategy.sl_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct,
                        'boosted': active_trade['boosted']
                    })
                    active_trade = None
                    continue
            else:  # SHORT
                if row['low'] <= active_trade['tp']:
                    pnl_pct = strategy.tp_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'outcome': 'WIN',
                        'pnl_pct': pnl_pct,
                        'boosted': active_trade['boosted']
                    })
                    active_trade = None
                    continue
                elif row['high'] >= active_trade['sl']:
                    pnl_pct = -strategy.sl_pct - fee_pct
                    trades.append({
                        'entry_time': active_trade['entry_time'],
                        'exit_time': current_time,
                        'direction': 'SHORT',
                        'outcome': 'LOSS',
                        'pnl_pct': pnl_pct,
                        'boosted': active_trade['boosted']
                    })
                    active_trade = None
                    continue
        
        # Check for new signal
        if active_trade is None:
            signal = strategy.generate_signal(row, df_liquidations, current_time)
            
            if signal:
                dir, entry, tp, sl, confidence, boosted = signal
                active_trade = {
                    'direction': dir,
                    'entry': entry,
                    'tp': tp,
                    'sl': sl,
                    'entry_time': current_time,
                    'confidence': confidence,
                    'boosted': boosted
                }
    
    # Results
    df_trades = pd.DataFrame(trades)
    
    if len(df_trades) > 0:
        wins = len(df_trades[df_trades['outcome'] == 'WIN'])
        losses = len(df_trades[df_trades['outcome'] == 'LOSS'])
        wr = wins / len(df_trades)
        net_pnl = df_trades['pnl_pct'].sum() * 100
        
        # Boosted trades analysis
        boosted = df_trades[df_trades['boosted'] == True]
        if len(boosted) > 0:
            boosted_wr = len(boosted[boosted['outcome'] == 'WIN']) / len(boosted)
            print(f"🚀 LIQUIDATION-BOOSTED TRADES:")
            print(f"   Count: {len(boosted)}")
            print(f"   Win Rate: {boosted_wr:.1%}")
            print()
        
        print(f"📊 OVERALL RESULTS:")
        print(f"   Total Trades: {len(df_trades)}")
        print(f"   Wins: {wins}, Losses: {losses}")
        print(f"   Win Rate: {wr:.1%}")
        print(f"   Net PnL: {net_pnl:+.2f}%")
        print(f"   Trades/Day: {len(df_trades)/14:.1f}")
        print()
        
        # Compare to V8
        print(f"📈 VS V8 BASELINE:")
        print(f"   V8 Baseline: 83.82% WR, +70.80% PnL")
        print(f"   V8+Liquidation: {wr:.1%} WR, {net_pnl:+.2f}% PnL")
        
        if wr > 0.8382:
            print(f"\n   ✅ BETTER WR! +{(wr - 0.8382)*100:.2f}%")
        if net_pnl > 70.80:
            print(f"   ✅ BETTER PNL! +{net_pnl - 70.80:.2f}%")
        
        if wr > 0.8382 or net_pnl > 70.80:
            print(f"\n   🎯 WINNER! Liquidation boost improves V8!")
        else:
            print(f"\n   ⚠️  No improvement - V8 alone is better")
        
        return df_trades, wr, net_pnl
    else:
        print("\n   ⚠️  No trades generated")
        return None, 0, 0

if __name__ == "__main__":
    # Test
    import sys
    sys.path.insert(0, '..')
    
    df_price = pd.read_csv('../training/data/BTC_5m_2025_enriched.csv')
    df_price['timestamp'] = pd.to_datetime(df_price['timestamp'])
    df_price = df_price[df_price['timestamp'] >= '2026-01-01'].reset_index(drop=True)
    
    df_liqs = pd.read_csv('liquidation_data/historical_liquidations_inferred.csv')
    df_liqs['timestamp'] = pd.to_datetime(df_liqs['timestamp'])
    
    backtest_v8_liquidation_hybrid(df_price, df_liqs)
