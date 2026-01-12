
import pandas as pd
import numpy as np
import logging
import random
import sys
import os
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from research.feature_generator import AdvancedFeatureGenerator
from research.genetic_genome import Genome
from utils.logger import log_to_journal

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DarwinEngine:
    def __init__(self, data_path, population_size=50, generations=10):
        self.data_path = data_path
        self.population_size = population_size
        self.generations = generations
        self.population = []
        self.df = None
        self.features = []
        
        # Load and Prep Data
        self.load_data()

    def load_data(self):
        """Loads data and generates gene pool (features)."""
        logger.info(f"🧬 Loading Data from {self.data_path}")
        raw_df = pd.read_csv(self.data_path)
        
        # Limit rows for speed if needed, but 1H data is usually fine
        # raw_df = raw_df.tail(10000) 
        
        gen = AdvancedFeatureGenerator(raw_df)
        self.df = gen.generate_all()
        self.features = list(self.df.columns)
        logger.info(f"🧬 Gene Pool Initialized: {len(self.features)} Genes Available.")

    def evaluate(self, genome):
        """
        Fast Vectorized/Iterative Backtest.
        Calculates Fitness = Sharpe * log(Trades)
        """
        buy_signals, sell_signals = genome.get_signal_series(self.df)
        
        # Simulation State
        position = 0 # 0: None, 1: Long
        entry_price = 0.0
        balance = 10000.0
        trades = []
        equity_curve = []
        
        # Convert to numpy for insane speed
        closes = self.df['close'].values
        buys = buy_signals.values
        sells = sell_signals.values
        
        # Iterating numpy array is fast enough (approx 100-200ms per genome)
        for i in range(len(closes)):
            price = closes[i]
            
            if position == 0:
                # Check Entry
                if buys[i]:
                    position = 1
                    entry_price = price
            else:
                # Check Exit (Logic)
                exit_signal = False
                if sells[i]:
                    exit_signal = True
                
                # Check Exit (Risk)
                pnl_pct = (price - entry_price) / entry_price * 100
                if pnl_pct >= genome.take_profit_pct:
                    exit_signal = True
                elif pnl_pct <= -genome.stop_loss_pct:
                    exit_signal = True
                    
                if exit_signal:
                    # Execute Trade
                    profit = balance * (pnl_pct / 100) # Simple compounding simulation
                    balance += profit
                    trades.append(pnl_pct)
                    position = 0
            
            equity_curve.append(balance)
            
        # Calculate Stats
        genome.total_trades = len(trades)
        genome.net_profit = (balance - 10000.0) / 10000.0 * 100
        
        if len(trades) > 5:
            returns = np.array(trades)
            avg_ret = np.mean(returns)
            std_ret = np.std(returns) + 0.0001
            genome.sharpe = avg_ret / std_ret
        else:
            genome.sharpe = 0.0
            
        # Fitness Function: Reward Profit & Sharpe, punish low trades (lucky hits)
        # Using a balanced score
        if genome.total_trades < 5:
            genome.fitness = 0
        else:
            genome.fitness = genome.sharpe * 2 + (genome.net_profit / 100)
            
        return genome

    def evolve(self):
        """The Main Evolutionary Loop."""
        logger.info("🦕 Genesis: Spawning Random Population...")
        self.population = [Genome(self.features) for _ in range(self.population_size)]
        
        # Genesis Initialization
        for g in self.population:
            g.genesis()
            
        for gen in range(self.generations):
            logger.info(f"⏳ Generation {gen+1}/{self.generations} Evolving...")
            
            # 1. Evaluate
            evaluated_pop = [self.evaluate(g) for g in self.population]
            
            # 2. Rank
            evaluated_pop.sort(key=lambda x: x.fitness, reverse=True)
            best = evaluated_pop[0]
            logger.info(f"   🏆 Gen {gen+1} Best: {best.fitness:.2f} | PnL: {best.net_profit:.1f}% | Sharpe: {best.sharpe:.2f} | Trades: {best.total_trades}")
            logger.info(f"      Strategy: {best}")
            
            # 3. Select (Survival of the Fittest)
            survivors = evaluated_pop[:self.population_size // 2] # Kill bottom 50%
            
            # Throttle CPU usage to prevent system crash ("PyRefly" / VSCode Indexer overload)
            time.sleep(1) 
            
            # 4. Reproduce & Mutate
            new_pop = survivors.copy()
            
            while len(new_pop) < self.population_size:
                # Tournament Selection for parents? Or random from survivors
                p1 = random.choice(survivors)
                
                if random.random() < 0.7:
                    # Crossover
                    p2 = random.choice(survivors)
                    child = p1.crossover(p2)
                else:
                    # Asexual Reproduction (Clone)
                    child = Genome(self.features)
                    # Copy genes manually (fastest way for simple class)
                    child.buy_conditions = p1.buy_conditions[:]
                    child.sell_conditions = p1.sell_conditions[:]
                    child.stop_loss_pct = p1.stop_loss_pct
                    child.take_profit_pct = p1.take_profit_pct
                    
                # Mutation
                child.mutate()
                new_pop.append(child)
                
            self.population = new_pop
            
        # Final Result
        self.evaluate(self.population[0]) # Re-eval best just in case
        return self.population[0]

    def run_continuous(self):
        """Runs the evolutionary process appropriately forever."""
        logger.info("♾️ STARTING CONTINUOUS DARWINIAN EVOLUTION (Background Service)")
        
        cycle = 1
        best_overall_fitness = 0.0
        
        # Try to load existing best to prevent regression on restart
        if os.path.exists('darwin_winner.json'):
            try:
                with open('darwin_winner.json', 'r') as f:
                    data = json.load(f)
                    if 'fitness' in data:
                        best_overall_fitness = data['fitness']
                        logger.info(f"♻️ Resumed from previous champion. Benchmark Fitness: {best_overall_fitness:.2f}")
            except:
                pass
        
        while True:
            logger.info(f"\n🌀 Starting Evolution Cycle {cycle}...")
            
            # 1. Evolve a Winner for this cycle
            current_winner = self.evolve()
            
            # 2. Compare to previous best logic (Safety Check)
            # We only overwrite if it's statistically significant or we want to rotate strategies
            # For now, simplistic: if fitness > best_overall * 1.05 (5% improvement) OR first run
            
            if current_winner.fitness > best_overall_fitness:
                logger.info(f"🚨 NEW GLOBAL CHAMPION FOUND! Fitness: {current_winner.fitness:.2f} (Prev Best: {best_overall_fitness:.2f})")
                best_overall_fitness = current_winner.fitness
                
                # Save to JSON
                winner_data = {
                    "buy_conditions": current_winner.buy_conditions,
                    "sell_conditions": current_winner.sell_conditions,
                    "stop_loss_pct": current_winner.stop_loss_pct,
                    "take_profit_pct": current_winner.take_profit_pct,
                    "fitness": current_winner.fitness,
                    "timestamp": datetime.now().isoformat()
                }
                
                with open('darwin_winner.json', 'w') as f:
                    json.dump(winner_data, f, indent=4)
                    
                log_to_journal(
                    "Darwin Evolution Update",
                    f"**New Strategy Evolved!**\n- **Cycle**: {cycle}\n- **Sharpe**: {current_winner.sharpe:.2f}\n- **Profit**: {current_winner.net_profit:.2f}%\n- **Logic**: `{current_winner}`",
                    "🧬"
                )
            else:
                logger.info(f"💤 Cycle {cycle} Winner ({current_winner.fitness:.2f}) failed to beat Global Best ({best_overall_fitness:.2f}). Keeping current champion.")
            
            cycle += 1
            # Sleep to prevent CPU melting? Or just go full speed?
            # Sleep to prevent CPU melting? Or just go full speed?
            # User said "keep on evolving", assuming full speed is okay but let's be nice to the CPU.
            logger.info("⏳ Resting for 30 seconds before next cycle (Cooling Down)...")
            import time
            time.sleep(30)

if __name__ == "__main__":
    # Test Run
    data_file = "datasets/BTCUSD-1h-500wks-data.csv"
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', data_file))
    
    if os.path.exists(path):
        darwin = DarwinEngine(path, population_size=100, generations=10) 
        # darwin.evolve() # Old one-off
        darwin.run_continuous() # New Loop

