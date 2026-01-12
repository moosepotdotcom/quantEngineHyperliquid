
import random
import pandas as pd

class Genome:
    """
    Represents a Trading Strategy Candidate.
    DNA Structure:
    - Buy Conditions: List of strings e.g. ["rsi_14 < 30", "close > sma_200"]
    - Sell Conditions: List of strings e.g. ["rsi_14 > 70"]
    - Stop Loss %: Float
    - Take Profit %: Float
    """
    def __init__(self, features_list):
        self.features = [f for f in features_list if f not in ['date', 'timestamp', 'open', 'high', 'low', 'close', 'target']]
        # Core price features are allowed as operands
        self.features.extend(['close', 'volume'])
        
        self.buy_conditions = []
        self.sell_conditions = []
        
        # Risk Parameters
        self.stop_loss_pct = round(random.uniform(0.5, 5.0), 2)
        self.take_profit_pct = round(random.uniform(1.0, 10.0), 2)
        
        # Fitness Score
        self.fitness = 0.0
        self.net_profit = 0.0
        self.sharpe = 0.0
        self.total_trades = 0

    def random_condition(self):
        """Generates a single random logic clause."""
        # Left Operand: Feature
        left = random.choice(self.features)
        
        # Operator
        op = random.choice(['>', '<'])
        
        # Right Operand: Feature or Helper Value
        if random.random() < 0.5:
             # Compare to another feature (e.g. Close > SMA_50)
             right = random.choice(self.features)
        else:
             # Compare to a constant value appropriate for the features
             # This is tricky because ranges differ (RSI 0-100, Price 90000)
             # Heuristic: If name contains 'rsi' or 'mfi', use 0-100
             if 'rsi' in left or 'mfi' in left or 'stoch' in left:
                 right = str(random.randint(10, 90))
             elif 'adx' in left:
                 right = str(random.randint(15, 50))
             elif 'pct' in left or 'ratio' in left:
                 right = str(round(random.uniform(0.5, 2.0), 2))
             else:
                 # For raw price/volume, hard to guess value, so default to comparison with other feature
                 # or comparisons like "0" (e.g. macd > 0)
                 if 'macd' in left or 'diff' in left:
                     right = "0"
                 else:
                     right = random.choice(self.features) # Fallback to feature comparison
        
        return f"{left} {op} {right}"

    def genesis(self):
        """Creates a completely random strategy."""
        # 1 to 3 conditions for Buy
        num_buy = random.randint(1, 3)
        self.buy_conditions = [self.random_condition() for _ in range(num_buy)]
        
        # 1 to 2 conditions for Sell OR just Risk Management
        if random.random() < 0.7:
            num_sell = random.randint(1, 2)
            self.sell_conditions = [self.random_condition() for _ in range(num_sell)]
        else:
            self.sell_conditions = [] # Purely Trailing/Risk exit

    def mutate(self):
        """Randomly alters the genome."""
        r = random.random()
        
        if r < 0.3:
            # Modify Stop/TP
            self.stop_loss_pct = round(max(0.1, self.stop_loss_pct + random.uniform(-0.5, 0.5)), 2)
            self.take_profit_pct = round(max(0.2, self.take_profit_pct + random.uniform(-1.0, 1.0)), 2)
            
        elif r < 0.6:
            # Change a Buy Condition
            if self.buy_conditions:
                idx = random.randint(0, len(self.buy_conditions)-1)
                self.buy_conditions[idx] = self.random_condition()
                
        elif r < 0.8:
            # Add/Remove Buy Condition
            if len(self.buy_conditions) < 4 and random.random() > 0.5:
                self.buy_conditions.append(self.random_condition())
            elif len(self.buy_conditions) > 1:
                self.buy_conditions.pop(random.randint(0, len(self.buy_conditions)-1))
                
        else:
            # Mutate Sell Condition
            if not self.sell_conditions:
                 self.sell_conditions.append(self.random_condition())
            else:
                 idx = random.randint(0, len(self.sell_conditions)-1)
                 self.sell_conditions[idx] = self.random_condition()

    def crossover(self, other):
        """Breeds this genome with another to create a child."""
        child = Genome(self.features)
        
        # Mix Parameters
        child.stop_loss_pct = random.choice([self.stop_loss_pct, other.stop_loss_pct])
        child.take_profit_pct = random.choice([self.take_profit_pct, other.take_profit_pct])
        
        # Mix Conditions
        # Take half from mom, half from dad
        split = len(self.buy_conditions) // 2
        child.buy_conditions = self.buy_conditions[:split] + other.buy_conditions[split:]
        
        if not child.buy_conditions: # Ensure at least one
            child.buy_conditions = [random.choice(self.buy_conditions + other.buy_conditions)]
            
        return child

    def get_signal_series(self, df):
        """Evaluates the strategy on the full DataFrame."""
        # Start with all True
        buy_signal = pd.Series(True, index=df.index)
        sell_signal = pd.Series(True, index=df.index)
        
        try:
            for cond in self.buy_conditions:
                # Evaluation using pandas query syntax is safer/easier
                # But here we need Series boolean logic.
                # cond string: "feature > value"
                parts = cond.split()
                left = df[parts[0]]
                op = parts[1]
                right_str = parts[2]
                
                # Check if right is a column or value
                if right_str in df.columns:
                    right = df[right_str]
                else:
                    right = float(right_str)
                    
                if op == '>':
                    buy_signal &= (left > right)
                elif op == '<':
                    buy_signal &= (left < right)
                    
            if not self.sell_conditions:
                sell_signal = pd.Series(False, index=df.index)
            else:
                for cond in self.sell_conditions:
                    parts = cond.split()
                    left = df[parts[0]]
                    op = parts[1]
                    right_str = parts[2]
                    
                    if right_str in df.columns:
                        right = df[right_str]
                    else:
                        right = float(right_str)
                        
                    if op == '>':
                        sell_signal &= (left > right)
                    elif op == '<':
                        sell_signal &= (left < right)
                        
            return buy_signal, sell_signal
            
        except Exception as e:
            # print(f"Error evaluating genome: {e} | Cond: {self.buy_conditions}")
            return pd.Series(False, index=df.index), pd.Series(False, index=df.index)

    def __str__(self):
        return f"BUY: {' AND '.join(self.buy_conditions)} | SELL: {' AND '.join(self.sell_conditions)} | SL: {self.stop_loss_pct}% TP: {self.take_profit_pct}%"
