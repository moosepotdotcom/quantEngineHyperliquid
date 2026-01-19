import pandas as pd
import numpy as np
import itertools

def optimize():
    print("="*60)
    print("🧪 HYPERPARAMETER GRID SEARCH (Golden Settings)")
    print("="*60)
    
    try:
        df = pd.read_csv("SIGNALS_DB.csv")
        print(f"   📊 Loaded {len(df)} potential signals")
    except Exception as e:
        print(f"❌ Could not load SIGNALS_DB.csv: {e}")
        return

    # Filter out invalid rows
    df.dropna(inplace=True)
    
    # Grid Search Space
    # We focus on the parameters that affect the Outcome
    grid = {
        'tp': [0.010, 0.012, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050],
        'sl': [0.005, 0.008, 0.010, 0.012, 0.015, 0.020],
        'conf': [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80],
        'use_atr': [True, False] # Adaptive threshold
    }
    
    keys, values = zip(*grid.items())
    combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    print(f"   🔍 Testing {len(combinations)} combinations...")
    
    results = []
    
    best_pnl = -np.inf
    
    # Pre-calculate columns for speed
    # We assume 'Conservative' outcome: If SL hits, it's a loss, even if TP also hits.
    
    for i, params in enumerate(combinations):
        if i % 500 == 0: print(f"      Processing {i}/{len(combinations)}...", end='\r')
        
        tp = params['tp']
        sl = params['sl']
        conf_base = params['conf']
        use_atr = params['use_atr']
        
        # 1. Filter by Confidence & ATR
        # Vectorized filtering
        mask = df['confidence'] >= conf_base
        
        if use_atr:
            # If ATR % is high (> 0.0015 i.e. 0.15%), require higher confidence
            # Let's say: if atr_pct > 0.5%, add 10% to threshold
            # Approximating 'atr' column is absolute value, need percentage
            # Assuming 'atr' in CSV is absolute value
            # atr_pct = df['atr'] / df['price']
            # We don't have price in all rows? We do.
            
            atr_pct = df['atr'] / df['price']
            # Penalty logic: if vol > 1.0% (0.01), +0.05 conf
            penalty_mask = atr_pct > 0.01
            # Combined mask:
            # (Normal & Conf > Base) OR (Volatile & Conf > Base + 0.05)
            # Simplified: Just effective threshold
            effective_conf = pd.Series(conf_base, index=df.index)
            effective_conf[penalty_mask] += 0.05
            
            mask = df['confidence'] >= effective_conf
            
        subset = df[mask]
        
        if len(subset) == 0:
            continue
            
        # 2. Calculate Outcomes
        # Win: MaxProfit >= TP AND MaxLoss < SL
        # Loss: MaxLoss >= SL
        
        wins = (subset['max_profit'] >= tp) & (subset['max_loss'] < sl)
        losses = (subset['max_loss'] >= sl)
        # Note: If neither hit (expired), result is 0 (or close at end)
        # For this optimization, let's assume 'Expired' trades break even or small loss.
        # Let's count them as strict 0.
        
        n_wins = wins.sum()
        n_losses = losses.sum()
        n_trades = len(subset)
        
        # PnL (Simple multiplier, ignoring fees/slippage for optimization)
        # Fees approx 0.001 per trade (0.1%)
        fees = 0.001
        
        # Net Outcome
        total_pnl = (n_wins * (tp - fees)) - (n_losses * (sl + fees))
        
        # Win Rate
        wr = (n_wins / n_trades) * 100 if n_trades > 0 else 0
        
        results.append({
            'tp': tp,
            'sl': sl,
            'conf': conf_base,
            'use_atr': use_atr,
            'pnl': total_pnl,
            'wr': wr,
            'trades': n_trades
        })
        
        if total_pnl > best_pnl:
            best_pnl = total_pnl
    
    print("\n✅ Optimization Complete")
    
    # Convert to DF
    res_df = pd.DataFrame(results)
    res_df.sort_values('pnl', ascending=False, inplace=True)
    
    print("\n🏆 TOP 10 SETTINGS (Maximize PnL):")
    print(res_df.head(10).to_string())
    
    top = res_df.iloc[0]
    print(f"\n🌟 GOLDEN CONFIGURATION:")
    print(f"   Confidence: {top['conf']:.2f}")
    print(f"   TP: {top['tp']*100:.1f}%")
    print(f"   SL: {top['sl']*100:.1f}%")
    print(f"   ATR Filter: {top['use_atr']}")
    print(f"   Stats: {int(top['trades'])} trades, {top['wr']:.1f}% WR, Score: {top['pnl']:.4f}")

    # Save
    res_df.to_csv("OPTIMIZATION_RESULTS.csv", index=False)

if __name__ == "__main__":
    optimize()
