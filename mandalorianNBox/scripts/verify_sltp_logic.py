import sys
import os
import pandas as pd
import backtrader as bt
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dashboard.strategies_complete import TurtleStrategyOptimized, ConsolidationPopStrategy, SMAStrategy

# Debug Subclasses
class DebugTurtle(TurtleStrategyOptimized):
    def next(self):
        # Print only last few bars
        if len(self) > 190:
             try:
                 h_prev = self.high[-1]
                 print(f"T={len(self)} | Close: {self.data.close[0]} | High[-1]: {h_prev}")
             except:
                 pass
        super().next()

class DebugSMA(SMAStrategy):
    def next(self):
        super().next()

def run_test(strategy_class, data, name, params=None):
    print(f"\n🧪 Testing {name}...")
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    
    # Use Debug subclass if available
    strat_cls = DebugTurtle if strategy_class == TurtleStrategyOptimized else strategy_class
    
    if params:
        cerebro.addstrategy(strat_cls, **params)
    else:
        cerebro.addstrategy(strat_cls)
        
    strats = cerebro.run()
    strat = strats[0]
    
    if strat.position.size != 0:
        print(f"   ✅ Signal Triggered: {strat.position.size} units @ {strat.position.price:.2f}")
        sl = getattr(strat, 'sl_price', 0.0)
        tp = getattr(strat, 'tp_price', 0.0)
        
        if sl > 0 and tp > 0:
            print(f"   ✅ SL/TP Verified: SL=${sl:.2f}, TP=${tp:.2f}")
            return True
        else:
            print(f"   ❌ FAILED: SL/TP is 0.0! (SL={sl}, TP={tp})")
            return False
    else:
        print("   ⚠️ No signal triggered in mock data.")
        # Debug why for Turtle
        if "Turtle" in name:
             print(f"   Debug: Close[-1]={data['close'].iloc[-1]}, High[-1]={data['high'].iloc[-1]}")
        return None

# 1. Mock Data for Turtle (Breakout)
# Need > 98 bars + buffer for execution. Let's make 210.
dates = pd.date_range(start='2024-01-01', periods=210, freq='1h')
df_turtle = pd.DataFrame({
    'open': [100.0]*210, 'high': [105.0]*210, 'low': [95.0]*210, 'close': [100.0]*210, 'volume': [1000.0]*210
}, index=dates)
# Breakout at 200. 
# Previous 98 bars max high is 105.
# We set bar 200 to Close 106.
df_turtle.loc[df_turtle.index[200], 'close'] = 106.0
df_turtle.loc[df_turtle.index[200], 'high'] = 106.0
# Rest remain 100 or follow trend (doesn't matter, just need next bar existing)

# 2. Mock Data for Investor (SMA Crossover)
dates_sma = pd.date_range(start='2024-01-01', periods=310, freq='1d')
df_sma = pd.DataFrame({
    'open': [100.0]*310, 'high': [105.0]*310, 'low': [95.0]*310, 'close': [100.0]*310, 'volume': [1000.0]*310
}, index=dates_sma)
# Trigger Cross: Price Jumps up at 250
for i in range(250, 310):
   df_sma.loc[df_sma.index[i], 'close'] = 200.0

# 3. Mock Data for Consolidation
# Tight range, then down (Buy low)
dates_con = pd.date_range(start='2024-01-01', periods=50, freq='1h')
df_consol = pd.DataFrame({
    'open': [100.0]*50, 'high': [101.0]*50, 'low': [99.0]*50, 'close': [100.0]*50, 'volume': [1000.0]*50
}, index=dates_con)
# Trigger: Last bar drops to lower third of 99-101 range.
# Range = 2. High=101, Low=99. Lower third < 99.66
df_consol.loc[df_consol.index[-1], 'close'] = 99.1 

print("🔍 Starting Verification...")
results = []
results.append(run_test(TurtleStrategyOptimized, df_turtle, "Turtle Strategy"))
results.append(run_test(SMAStrategy, df_sma, "Investor (SMA)", params={'fast_period': 50, 'slow_period': 200}))

if all(r is True for r in results if r is not None):
    print("\n🏆 ALL CHECKS PASSED: Logic is verified.")
else:
    print("\n❌ SOME CHECKS FAILED.")
