import pandas as pd
import numpy as np

def analyze_losses():
    print("🔬 FORENSIC LOSS ANALYSIS")
    print("=" * 60)
    
    # Load forensic log
    try:
        df = pd.read_csv('FORENSIC_TRADES.csv')
    except FileNotFoundError:
        print("❌ CSV File not found")
        return

    print(f"📊 Total Trades: {len(df)}")
    
    # Separate Winners and Losers
    # PnL > 0 is win. <= 0 might include breakeven/loss. Logic says PnL < 0 is loss.
    winners = df[df['PnL %'] > 0].copy()
    losers = df[df['PnL %'] <= 0].copy()
    
    print(f"   🏆 Winners: {len(winners)}")
    print(f"   ❌ Losers:  {len(losers)}")
    print("-" * 60)
    
    metrics = ['Confidence', 'Disagreement', 'Hurst', 'ATR', 'RSI']
    
    print(f"{'Metric':<15} {'Avg (Win)':<12} {'Avg (Loss)':<12} {'Delta':<10} {'Filter Idea'}")
    print("-" * 60)
    
    recommendations = []
    
    for m in metrics:
        if m not in df.columns:
            continue
            
        win_mean = winners[m].mean()
        loss_mean = losers[m].mean()
        
        # Calculate Delta %
        delta = ((win_mean - loss_mean) / abs(loss_mean)) * 100 if loss_mean != 0 else 0
        
        filter_str = ""
        # Heuristic for meaningful difference
        if m == 'Disagreement' and loss_mean > win_mean:
             filter_str = f"Cap {m} < {np.percentile(winners[m], 90):.3f}?"
             recommendations.append(('Disagreement', '<', np.percentile(winners[m], 90)))
        elif m == 'Hurst':
             # If losers have Higher Hurst (Trending) when we are mean reversion...
             if loss_mean > win_mean:
                 filter_str = f"Cap {m} < {np.percentile(winners[m], 90):.3f}?"
                 recommendations.append(('Hurst', '<', np.percentile(winners[m], 90)))
        elif m == 'ATR':
             # Maybe we lose on low volatility?
             if win_mean > loss_mean:
                 filter_str = f"Require {m} > {np.percentile(losers[m], 75):.3f}?"
                 recommendations.append(('ATR', '>', np.percentile(losers[m], 75)))
                 
        print(f"{m:<15} {win_mean:<12.4f} {loss_mean:<12.4f} {delta:<10.1f}% {filter_str}")
        
    print("=" * 60)
    
    # SIMULATE THE PERFECT FILTER
    # Let's try to apply a composite filter to see if we can kill the 55 losses without killing all wins
    
    print("\n🧪 SIMULATING FILTER COMBINATIONS")
    
    # Base: existing
    best_wr = (len(winners) / len(df)) * 100
    best_filter = "Baseline"
    remaining_trades = len(df)
    
            
    # Try Combined Disagreement + ATR Caps
    print("\n   ⚗️  Testing Composite Filters (Disagreement + ATR)...")
    for d_cap in [0.09, 0.10, 0.11]:
        for atr_cap in [100, 110, 120, 130]:
            filtered = df[(df['Disagreement'] < d_cap) & (df['ATR'] < atr_cap)]
            if len(filtered) < 20: continue
            
            w = len(filtered[filtered['PnL %'] > 0])
            wr = (w / len(filtered)) * 100
            
            if wr > best_wr:
                best_wr = wr
                best_filter = f"Disagreement < {d_cap} & ATR < {atr_cap}"
                remaining_trades = len(filtered)
                print(f"      Found: {best_filter} -> {wr:.2f}% ({len(filtered)} trades)")
            
    # Try Hurst Caps
    # ... (similar logic)
    
    print(f"   🏆 BEST FOUND: {best_filter}")
    print(f"      Win Rate: {best_wr:.2f}%")
    print(f"      Trades:   {remaining_trades} ({(remaining_trades/7):.1f}/day)")
    
    if best_wr > 98:
        print("\n   ✅ EUREKA! We found the 99% filter.")

if __name__ == "__main__":
    analyze_losses()
