#!/usr/bin/env python3
"""
Phase 4 Precision Model Training
Trains a high-accuracy classifier for trade signal generation
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import sys
import os

class PrecisionModelTrainer:
    """
    Trains precision model for Phase 4
    
    Goal: 70%+ win rate with fewer trades
    """
    
    def __init__(self):
        self.model = None
        self.feature_cols = []
        
    def label_trades(self, df, tp_pct=0.012, sl_pct=0.006, max_duration_hours=8):
        """
        Label each candle: 1 = good long, -1 = good short, 0 = skip
        
        A "good" trade hits TP before SL within duration
        """
        
        print(f"🏷️  Labeling trades (TP: {tp_pct*100}%, SL: {sl_pct*100}%, Duration: {max_duration_hours}h)...")
        
        labels = []
        max_candles = max_duration_hours * 12  # 5min candles
        
        for i in range(len(df)):
            row = df.iloc[i]
            entry_price = row['close']
            
            # Look ahead to see if TP/SL hit
            future_window = df.iloc[i+1:min(i+1+max_candles, len(df))]
            
            if len(future_window) == 0:
                labels.append(0)
                continue
            
            # Long setup
            long_tp = entry_price * (1 + tp_pct)
            long_sl = entry_price * (1 - sl_pct)
            
            # Check if TP hit before SL
            tp_hit_long = (future_window['high'] >= long_tp).any()
            sl_hit_long = (future_window['low'] <= long_sl).any()
            
            if tp_hit_long and not sl_hit_long:
                # TP hit first = good long
                tp_idx = future_window[future_window['high'] >= long_tp].index[0]
                sl_idx = future_window[future_window['low'] <= long_sl].index[0] if sl_hit_long else len(df)
                if tp_idx < sl_idx:
                    labels.append(1)
                    continue
            
            # Short setup
            short_tp = entry_price * (1 - tp_pct)
            short_sl = entry_price * (1 + sl_pct)
            
            tp_hit_short = (future_window['low'] <= short_tp).any()
            sl_hit_short = (future_window['high'] >= short_sl).any()
            
            if tp_hit_short and not sl_hit_short:
                # TP hit first = good short
                tp_idx = future_window[future_window['low'] <= short_tp].index[0]
                sl_idx = future_window[future_window['high'] >= short_sl].index[0] if sl_hit_short else len(df)
                if tp_idx < sl_idx:
                    labels.append(-1)
                    continue
            
            # Neither is good = skip
            labels.append(0)
        
        df['label'] = labels
        
        # Stats
        good_longs = (df['label'] == 1).sum()
        good_shorts = (df['label'] == -1).sum()
        skips = (df['label'] == 0).sum()
        
        print(f"✅ Labeling complete:")
        print(f"   Good longs: {good_longs} ({good_longs/len(df)*100:.1f}%)")
        print(f"   Good shorts: {good_shorts} ({good_shorts/len(df)*100:.1f}%)")
        print(f"   Skips: {skips} ({skips/len(df)*100:.1f}%)")
        
        return df
    
    def prepare_features(self, df):
        """
        Select and prepare features for training
        """
        
        # Phase 4 features
        phase4_features = [
            'ob_imbalance', 'ob_bid_depth', 'ob_ask_depth',
            'ob_large_bids', 'ob_large_asks', 'ob_spread_pct',
            'funding_rate', 'funding_pct', 'funding_is_extreme',
            'liq_cluster_nearby', 'liq_pressure'
        ]
        
        # Add some price-based features
        price_features = [
            'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_lower',
            'atr', 'atr_ratio', 'volume'
        ]
        
        # Combine
        self.feature_cols = [f for f in phase4_features + price_features if f in df.columns]
        
        print(f"📊 Using {len(self.feature_cols)} features:")
        for f in self.feature_cols:
            print(f"   - {f}")
        
        return df[self.feature_cols].fillna(0)
    
    def train(self, df):
        """
        Train precision model
        """
        
        print("\n🤖 Training Precision Model...")
        
        # Prepare data
        X = self.prepare_features(df)
        y = df['label']
        
        # Only train on good setups (ignore skips for now)
        mask = y != 0
        X_train_full = X[mask]
        y_train_full = y[mask]
        
        # Convert to binary: 1 = long, 0 = short
        y_binary = (y_train_full == 1).astype(int)
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X_train_full, y_binary, test_size=0.2, random_state=42
        )
        
        print(f"\n📦 Training set: {len(X_train)} samples")
        print(f"📦 Test set: {len(X_test)} samples")
        
        # Train model
        print("\n🔧 Training Random Forest...")
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"\n✅ Training complete!")
        print(f"   Train accuracy: {train_score*100:.2f}%")
        print(f"   Test accuracy: {test_score*100:.2f}%")
        
        # Detailed metrics
        y_pred = self.model.predict(X_test)
        print(f"\n📊 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['Short', 'Long']))
        
        # Feature importance
        print(f"\n🔝 Top 10 Features:")
        importances = pd.DataFrame({
            'feature': self.feature_cols,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for idx, row in importances.head(10).iterrows():
            print(f"   {row['feature']:20s}: {row['importance']:.4f}")
        
        return self.model
    
    def save_model(self, filename="precision_model.pkl"):
        """Save trained model"""
        joblib.dump({
            'model': self.model,
            'feature_cols': self.feature_cols
        }, filename)
        print(f"\n💾 Model saved to {filename}")

# Main
if __name__ == "__main__":
    print("="*60)
    print("🎯 Phase 4 Precision Model Training")
    print("="*60)
    
    # Load data
    data_file = "dec2025_with_phase4_features.csv"
    print(f"\n📂 Loading {data_file}...")
    df = pd.read_csv(data_file)
    print(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Train
    trainer = PrecisionModelTrainer()
    
    # Label trades
    df = trainer.label_trades(df, tp_pct=0.012, sl_pct=0.006, max_duration_hours=8)
    
    # Train model
    model = trainer.train(df)
    
    # Save
    trainer.save_model("precision_model.pkl")
    
    print("\n" + "="*60)
    print("✅ Training Complete!")
    print("="*60)
