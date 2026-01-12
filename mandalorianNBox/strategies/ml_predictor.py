import backtrader as bt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

class MLPredictorStrategy(bt.Strategy):
    """
    AI/ML Random Forest Predictor (Advanced)
    Trains a Random Forest on RSI, Volume, Momentum, and Price Action.
    Includes Hard Stop Loss for risk management.
    """
    params = (
        ('train_len', 500),
        ('retrain_freq', 500),
        ('rsi_period', 14),
        ('roc_period', 5),
        ('stop_loss_pct', 2.0), # 2% Hard Stop Loss
    )
    
    def __init__(self):
        # Indicators for Features
        self.rsi = bt.ind.RSI(period=self.params.rsi_period)
        self.sma_fast = bt.ind.SMA(period=10)
        self.sma_slow = bt.ind.SMA(period=20)
        self.atr = bt.ind.ATR(period=14)
        self.roc = bt.ind.ROC(period=self.params.roc_period)
        
        # Machine Learning Model (Optimized)
        self.model = RandomForestClassifier(
            n_estimators=20,       # Reduced from 100 to 20 for speed
            max_depth=5,           # Limit depth to prevent overfitting/memory usage
            min_samples_split=20, 
            random_state=42,
            n_jobs=1               # Single core to avoid multiprocessing overhead in container
        )
        self.is_trained = False
        self.last_train_bar = 0
        
        # Data storage for training
        self.feature_history = []
        self.label_history = []
        self.last_features = None
        self.last_price = None

    def next(self):
        if len(self) < 50: # Warmup
            return

        current_price = self.data.close[0]
        prev_price = self.data.close[-1]
        
        # --- RISK MANAGEMENT (STOP LOSS) ---
        if self.position:
            entry_price = self.position.price
            if self.position.size > 0: # Long
                if current_price < entry_price * (1 - self.params.stop_loss_pct / 100):
                    self.close()
                    return # Exit logic immediately
        # -----------------------------------
        
        # 1. Feature Engineering
        # Price Action
        log_return = np.log(current_price / prev_price) if prev_price > 0 else 0
        
        # SMA Trends
        sma_fast_dist = (current_price - self.sma_fast[0]) / current_price
        sma_slow_dist = (current_price - self.sma_slow[0]) / current_price
        
        # Volume Trend (Avoid division by zero)
        vol = self.data.volume[0]
        prev_vol = self.data.volume[-1]
        vol_change = (vol - prev_vol) / (prev_vol + 1)
        
        # Volatility
        volatility = self.atr[0] / current_price
        
        current_features = [
            self.rsi[0],            # Momentum
            self.roc[0],            # Rate of Change
            sma_fast_dist,          # Trend Fast
            sma_slow_dist,          # Trend Slow
            volatility,             # Volatility
            vol_change,             # Volume Flow
            log_return              # Recent Performance
        ]

        # 2. Label Generation (Did previous features predict this correctly?)
        if self.last_features is not None and self.last_price is not None:
            # If price went UP, label was 1. Else 0.
            label = 1 if current_price > self.last_price else 0
            
            self.feature_history.append(self.last_features)
            self.label_history.append(label)
            
        # 3. Model Training (Online Learning)
        # Train if we have enough data AND (never trained OR time to retrain)
        data_len = len(self.feature_history)
        if data_len > self.params.train_len:
            curr_bar = len(self)
            if not self.is_trained or (curr_bar - self.last_train_bar > self.params.retrain_freq):
                # Optimization: Slice data to keep window fixed size (max 500 samples)
                max_window = 500
                train_X = self.feature_history[-max_window:]
                train_y = self.label_history[-max_window:]
                
                # Training takes a moment
                try:
                    print(f"🔄 Training ML Model... (Bar {curr_bar})")
                    self.model.fit(train_X, train_y)
                    self.is_trained = True
                    self.last_train_bar = curr_bar
                    print(f"✅ Training Complete. Score: {self.model.score(train_X, train_y):.2f}")
                except Exception as e:
                    print(f"⚠️ ML Training Error: {e}")
                    pass # Skip this training round if it fails

        # 4. Prediction & Trading
        if self.is_trained:
            prediction = self.model.predict([current_features])[0]
            
            # Handle case where model only saw one class (e.g. only UP during bull run)
            if len(self.model.classes_) > 1:
                probability = self.model.predict_proba([current_features])[0][1] # Prob of class 1 (UP)
            else:
                # If only one class, probability is 1.0 if prediction matches that class, else 0.0
                probability = 1.0 if prediction == 1 else 0.0

            
            # Trading Logic: Buy if confident UP, Sell if confident DOWN
            if prediction == 1 and probability > 0.55: # Strong Buy signal
                if not self.position:
                    self.buy()
            
            elif prediction == 0 and probability < 0.45: # Strong Sell signal (Prob of UP is low)
                if not self.position:
                    self.sell() # Short
                elif self.position.size > 0:
                     self.close() # Close Long
            
            # Simple Exit if wrong
            if self.position.size > 0 and prediction == 0:
                 self.close()

        # Update state for next step
        self.last_features = current_features
        self.last_price = current_price
