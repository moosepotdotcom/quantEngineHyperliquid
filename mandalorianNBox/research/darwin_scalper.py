
import sys
import os
import numpy as np
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from research.darwin_engine import DarwinEngine
from research.genetic_genome import Genome

class DarwinScalper(DarwinEngine):
    """
    Specialized Darwin Engine for High-Frequency Scalping.
    Prioritizes WIN RATE and PROFIT FACTOR over raw net profit.
    """
    
    def evaluate(self, genome):
        """
        Scalper-specific Fitness Function.
        Fitness = (WinRate^2 * 100) + (Sharpe * 50)
        """
        # Run standard simulation logic (copy-paste from base or reuse if possible)
        # Since base.evaluate modifies genome in place, we can call it?
        # No, the base evaluate calculates fitness at end. We need to intercept.
        # For speed/simplicity, I will reimplement the loop efficiently here.
        
        buy_signals, sell_signals = genome.get_signal_series(self.df)
        
        closes = self.df['close'].values
        buys = buy_signals.values
        sells = sell_signals.values
        
        position = 0
        entry_price = 0.0
        trades_pnl = []
        
        # Tighter Stops for Scalping (Fixed or Dynamic?)
        # Let's trust the Genome's SL/TP but maybe force them tighter if needed?
        # Genome defaults are usually 1-5%. For 15m scalping, we want 0.5% - 1.5%.
        # Let's assume the mutation/evolution finds the right SL/TP.
        
        for i in range(len(closes)):
            price = closes[i]
            
            if position == 0:
                if buys[i]:
                    position = 1
                    entry_price = price
            else:
                exit_signal = False
                if sells[i]: exit_signal = True
                
                # Check SL/TP
                pnl_pct = (price - entry_price) / entry_price * 100
                
                if pnl_pct >= genome.take_profit_pct: exit_signal = True
                elif pnl_pct <= -genome.stop_loss_pct: exit_signal = True
                elif sells[i]: exit_signal = True
                    
                if exit_signal:
                    # Deduct Fees (0.06% Taker x 2 = 0.12%)
                    pnl_pct -= 0.12
                    trades_pnl.append(pnl_pct)
                    position = 0
        
        # Stats
        total_trades = len(trades_pnl)
        if total_trades < 10: # Minimum sample size for scalper
            genome.fitness = 0
            genome.net_profit = 0
            return genome
            
        wins = [t for t in trades_pnl if t > 0]
        win_rate = len(wins) / total_trades
        
        returns = np.array(trades_pnl)
        net_profit = np.sum(returns)
        
        if np.std(returns) == 0:
            sharpe = 0
        else:
            sharpe = np.mean(returns) / np.std(returns)
            
        # --- SCALPER FITNESS FUNCTION ---
        # User wants "High Win Rate".
        # We also need profit matching (Profit Factor).
        
        # Win Rate Score (0.0 to 1.0) -> Weighted heavily
        # If Win Rate < 0.5, severe penalty
        
        score = 0
        if win_rate > 0.5:
            score += (win_rate * 1000) # Base score from winrate (500 to 1000)
        else:
            score -= 500
            
        score += (sharpe * 100)
        score += (total_trades * 2) # Reward activity
        
        genome.fitness = score
        genome.net_profit = net_profit
        genome.sharpe = sharpe
        genome.win_rate = win_rate # Store for logging
        genome.total_trades = total_trades
        
        return genome

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    data_path = "datasets/BTCUSD-15m-max-data.csv"
    if not os.path.exists(data_path):
        print("Data missing!")
        sys.exit(1)
        
    print("⚡ STARTING SCALPER EVOLUTION (Target: High Win Rate)...")
    
    # Run for 5 generations only closely to find a quick candidate
    engine = DarwinScalper(data_path, population_size=100, generations=5)
    winner = engine.evolve()
    
    print("\n🏆 BEST SCALPER FOUND:")
    print(f"   Win Rate: {winner.win_rate*100:.1f}%")
    print(f"   Trades:   {winner.total_trades}")
    print(f"   Logic:    {winner}")
    print(f"   SL: {winner.stop_loss_pct}% | TP: {winner.take_profit_pct}%")
    
    # Save to special file
    import json
    with open('darwin_scalper.json', 'w') as f:
        json.dump({
            "buy_conditions": winner.buy_conditions,
            "sell_conditions": winner.sell_conditions,
            "stop_loss_pct": winner.stop_loss_pct,
            "take_profit_pct": winner.take_profit_pct,
            "win_rate": winner.win_rate
        }, f, indent=4)
    print("💾 Saved to darwin_scalper.json")
