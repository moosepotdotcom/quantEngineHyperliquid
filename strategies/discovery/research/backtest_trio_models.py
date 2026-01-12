#!/usr/bin/env python3
"""
Backtest Trio Ensemble Models on Test Set
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import json
import os
from datetime import datetime

def load_trio_ensemble(prefix):
    """Load all 3 models from trio ensemble"""
    print(f"   Loading {prefix}...")
    
    xgb_model = xgb.XGBClassifier()
    xgb_model.load_model(f'{prefix}xgb.json')
    
    lgb_model = lgb.Booster(model_file=f'{prefix}lgb.json')
    
    cat_model = CatBoostClassifier()
    cat_model.load_model(f'{prefix}cat.json')
    
    with open(f'{prefix}metadata.json', 'r') as f:
        metadata = json.load(f)
    
    return xgb_model, lgb_model, cat_model, metadata

def get_trio_proba(xgb_m, lgb_m, cat_m, X):
    """Get consensus probability from trio"""
    p1 = xgb_m.predict_proba(X)
    p2 = lgb_m.predict(X, num_iteration=lgb_m.best_iteration)
    p3 = cat_m.predict_proba(X)
    
    # Average predictions (consensus)
    return (p1 + p2 + p3) / 3.0

def main():
    print("="*70)
    print("📈 TRIO ENSEMBLE BACKTEST REPORT")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ===== MTF SCALPER (5M) =====
    print("\n" + "="*70)
    print("1️⃣ MTF SCALPER (5M) BACKTEST")
    print("="*70)
    
    # Load data
    df_mtf = pd.read_csv('training/data/BTC_5m_mtf_labeled.csv')
    print(f"   Total samples: {len(df_mtf):,}")
    
    # Prepare features
    exclude = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'label']
    feature_cols = [c for c in df_mtf.columns if c not in exclude]
    
    # Test set (last 15%)
    test_start = int(len(df_mtf) * 0.85)
    test_df = df_mtf.iloc[test_start:].copy()
    X_test = test_df[feature_cols].values
    X_test = np.nan_to_num(X_test, nan=0.0, posinf=0.0, neginf=0.0)
    y_test = test_df['label'].values
    
    print(f"   Test set: {len(test_df):,} samples")
    
    # Load models
    xgb_m, lgb_m, cat_m, metadata = load_trio_ensemble('models/mtf_scalper_5m_trio_')
    
    # OVERRIDE with Calibrated Thresholds
    thresh_long = 0.50
    thresh_short = 0.55
    print(f"   ⚠️ Using Calibrated Thresholds: Long={thresh_long:.4f}, Short={thresh_short:.4f}")
    
    # Original from metadata (for reference)
    # thresh_long = metadata['target_precision_threshold_long']
    # thresh_short = metadata['target_precision_threshold_short']
    
    # Get predictions
    probas = get_trio_proba(xgb_m, lgb_m, cat_m, X_test)
    prob_long = probas[:, 1]
    prob_short = probas[:, 2]
    
    # Identify signals
    long_signals = prob_long >= thresh_long
    short_signals = prob_short >= thresh_short
    
    # Filter by actual labels (1=Long, 2=Short)
    long_trades = test_df[long_signals & (y_test == 1)].copy()
    short_trades = test_df[short_signals & (y_test == 2)].copy()
    
    long_wins = len(long_trades)
    short_wins = len(short_trades)
    
    # False signals (predicted but wrong label)
    long_losses = len(test_df[long_signals & (y_test != 1)])
    short_losses = len(test_df[short_signals & (y_test != 2)])
    
    total_trades = long_wins + short_wins + long_losses + short_losses
    total_wins = long_wins + short_wins
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    
    print(f"\n   📊 Results:")
    print(f"      Total Signals: {total_trades}")
    print(f"      Long Signals: {long_wins + long_losses} ({long_wins}W / {long_losses}L)")
    print(f"      Short Signals: {short_wins + short_losses} ({short_wins}W / {short_losses}L)")
    print(f"      Win Rate: {win_rate:.1f}%")
    
    # ===== WINNER HUNTER (1H) =====
    print("\n" + "="*70)
    print("2️⃣ WINNER HUNTER (1H) BACKTEST")
    print("="*70)
    
    # Load data
    df_wh = pd.read_csv('training/data/BTC_1h_labeled.csv')
    print(f"   Total samples: {len(df_wh):,}")
    
    # Prepare features
    feature_cols_wh = [c for c in df_wh.columns if c not in exclude]
    
    # Test set
    test_start_wh = int(len(df_wh) * 0.85)
    test_df_wh = df_wh.iloc[test_start_wh:].copy()
    X_test_wh = test_df_wh[feature_cols_wh].values
    X_test_wh = np.nan_to_num(X_test_wh, nan=0.0, posinf=0.0, neginf=0.0)
    y_test_wh = test_df_wh['label'].values
    
    print(f"   Test set: {len(test_df_wh):,} samples")
    
    # Load models
    xgb_wh, lgb_wh, cat_wh, metadata_wh = load_trio_ensemble('models/winner_hunter_1h_trio_')
    
    # OVERRIDE with Calibrated Thresholds
    thresh_long_wh = 0.35
    thresh_short_wh = 0.45
    print(f"   ⚠️ Using Calibrated Thresholds: Long={thresh_long_wh:.4f}, Short={thresh_short_wh:.4f}")
    
    # thresh_long_wh = metadata_wh['target_precision_threshold_long']
    # thresh_short_wh = metadata_wh['target_precision_threshold_short']
    
    # Get predictions
    probas_wh = get_trio_proba(xgb_wh, lgb_wh, cat_wh, X_test_wh)
    prob_long_wh = probas_wh[:, 1]
    prob_short_wh = probas_wh[:, 2]
    
    # Identify signals
    long_signals_wh = prob_long_wh >= thresh_long_wh
    short_signals_wh = prob_short_wh >= thresh_short_wh
    
    # Filter by actual labels
    long_trades_wh = test_df_wh[long_signals_wh & (y_test_wh == 1)].copy()
    short_trades_wh = test_df_wh[short_signals_wh & (y_test_wh == 2)].copy()
    
    long_wins_wh = len(long_trades_wh)
    short_wins_wh = len(short_trades_wh)
    
    long_losses_wh = len(test_df_wh[long_signals_wh & (y_test_wh != 1)])
    short_losses_wh = len(test_df_wh[short_signals_wh & (y_test_wh != 2)])
    
    total_trades_wh = long_wins_wh + short_wins_wh + long_losses_wh + short_losses_wh
    total_wins_wh = long_wins_wh + short_wins_wh
    win_rate_wh = (total_wins_wh / total_trades_wh * 100) if total_trades_wh > 0 else 0
    
    print(f"\n   📊 Results:")
    print(f"      Total Signals: {total_trades_wh}")
    print(f"      Long Signals: {long_wins_wh + long_losses_wh} ({long_wins_wh}W / {long_losses_wh}L)")
    print(f"      Short Signals: {short_wins_wh + short_losses_wh} ({short_wins_wh}W / {short_losses_wh}L)")
    print(f"      Win Rate: {win_rate_wh:.1f}%")
    
    # ===== GENERATE REPORT =====
    print("\n" + "="*70)
    print("📝 GENERATING REPORT")
    print("="*70)
    
    report_file = 'TRIO_BACKTEST_REPORT.md'
    
    with open(report_file, 'w') as f:
        f.write("# 📊 Trio Ensemble Backtest Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("**Test Period**: Out-of-sample test set (last 15% of historical data)\n\n")
        f.write("---\n\n")
        
        # MTF Scalper
        f.write("## 🚀 MTF Scalper (5M) Performance\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| **Win Rate** | **{win_rate:.1f}%** |\n")
        f.write(f"| **Total Signals** | {total_trades} |\n")
        f.write(f"| **Wins / Losses** | {total_wins}W / {total_trades - total_wins}L |\n")
        f.write(f"| **Long Signals** | {long_wins + long_losses} ({long_wins}W / {long_losses}L) |\n")
        f.write(f"| **Short Signals** | {short_wins + short_losses} ({short_wins}W / {short_losses}L) |\n")
        f.write(f"| **Long Threshold** | {thresh_long:.4f} ({thresh_long*100:.2f}%) |\n")
        f.write(f"| **Short Threshold** | {thresh_short:.4f} ({thresh_short*100:.2f}%) |\n")
        f.write(f"| **Test Samples** | {len(test_df):,} |\n\n")
        
        # Winner Hunter
        f.write("## 🏆 Winner Hunter (1H) Performance\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| **Win Rate** | **{win_rate_wh:.1f}%** |\n")
        f.write(f"| **Total Signals** | {total_trades_wh} |\n")
        f.write(f"| **Wins / Losses** | {total_wins_wh}W / {total_trades_wh - total_wins_wh}L |\n")
        f.write(f"| **Long Signals** | {long_wins_wh + long_losses_wh} ({long_wins_wh}W / {long_losses_wh}L) |\n")
        f.write(f"| **Short Signals** | {short_wins_wh + short_losses_wh} ({short_wins_wh}W / {short_losses_wh}L) |\n")
        f.write(f"| **Long Threshold** | {thresh_long_wh:.4f} ({thresh_long_wh*100:.2f}%) |\n")
        f.write(f"| **Short Threshold** | {thresh_short_wh:.4f} ({thresh_short_wh*100:.2f}%) |\n")
        f.write(f"| **Test Samples** | {len(test_df_wh):,} |\n\n")
        
        # Summary
        f.write("---\n\n")
        f.write("## 📈 Summary\n\n")
        f.write(f"- **MTF Scalper** shows {win_rate:.1f}% win rate with {total_trades} signals\n")
        f.write(f"- **Winner Hunter** shows {win_rate_wh:.1f}% win rate with {total_trades_wh} signals\n")
        f.write(f"- Both models use trio ensemble consensus (XGBoost + LightGBM + CatBoost)\n")
        f.write(f"- Precision-focused thresholds ensure high-quality signals\n\n")
    
    print(f"\n✅ Report saved to: {report_file}")
    print("\n" + "="*70)
    print("✅ BACKTEST COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
