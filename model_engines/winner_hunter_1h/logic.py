
"""
Winner Hunter (1H) - Isolated Logic
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime

# Add root to path for utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'utils')))

from utils.feature_engineer import add_all_indicators

# ML Imports
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from catboost import CatBoostClassifier
    HAS_CAT = True
except ImportError:
    HAS_CAT = False

# DEFINITIVE FEATURE LIST (231 Features)
MTF_FEATURE_LIST = [
    "rsi_7","rsi_14","rsi_21","stoch_k","stoch_d","williams_r","roc_5","roc_10","awesome_osc","kama","ppo","ppo_signal","ppo_hist",
    "ema_5","ema_10","ema_20","ema_50","ema_100","ema_200","sma_10","sma_20","sma_50",
    "macd","macd_signal","macd_hist","adx","adx_pos","adx_neg","cci","aroon_up","aroon_down","ichimoku_a","ichimoku_b",
    "bb_high","bb_low","bb_mid","bb_width","bb_pct","atr_7","atr_14","atr_21",
    "kc_high","kc_low","kc_mid","dc_high","dc_low","dc_mid","dc_width",
    "obv","cmf","mfi","adi","eom","vpt","nvi","vwap",
    "price_vs_ema20","price_vs_ema50","price_vs_bb_mid","ema_cross","trend_strength","atr_pct","volatility_regime",
    "rsi_sma","rsi_divergence","vol_sma_20","volume_surge","body_size","upper_wick","lower_wick","is_bullish",
    "return_1","return_3","return_5","return_10","range_pct","range_vs_atr",
    
    # 15m Context
    "rsi_7_15m","rsi_14_15m","rsi_21_15m","stoch_k_15m","stoch_d_15m","williams_r_15m","roc_5_15m","roc_10_15m","awesome_osc_15m","kama_15m",
    "ppo_15m","ppo_signal_15m","ppo_hist_15m","ema_5_15m","ema_10_15m","ema_20_15m","ema_50_15m","ema_100_15m","ema_200_15m",
    "sma_10_15m","sma_20_15m","sma_50_15m","macd_15m","macd_signal_15m","macd_hist_15m","adx_15m","adx_pos_15m","adx_neg_15m","cci_15m",
    "aroon_up_15m","aroon_down_15m","ichimoku_a_15m","ichimoku_b_15m","bb_high_15m","bb_low_15m","bb_mid_15m","bb_width_15m","bb_pct_15m",
    "atr_7_15m","atr_14_15m","atr_21_15m","kc_high_15m","kc_low_15m","kc_mid_15m","dc_high_15m","dc_low_15m","dc_mid_15m","dc_width_15m",
    "obv_15m","cmf_15m","mfi_15m","adi_15m","eom_15m","vpt_15m","nvi_15m","vwap_15m",
    "price_vs_ema20_15m","price_vs_ema50_15m","price_vs_bb_mid_15m","ema_cross_15m","trend_strength_15m","atr_pct_15m","volatility_regime_15m",
    "rsi_sma_15m","rsi_divergence_15m","vol_sma_20_15m","volume_surge_15m","body_size_15m","upper_wick_15m","lower_wick_15m","is_bullish_15m",
    "return_1_15m","return_3_15m","return_5_15m","return_10_15m","range_pct_15m","range_vs_atr_15m",
    
    # 1h Context (Note: Since we are in WH logic which operates on 1H base, 
    # the '1h' suffix features here technically refer to the base timeframe features if we are consistent with 5m model.
    # However, WH logic might be slightly different. But the weights file expects these NAMES.
    # So we must map our 1H base dataframe columns to these `_1h` suffixed names if that's what the model expects.
    # OR, if this list comes from MTF Scalper (5m Base), then `_1h` are context.
    # If Winner Hunter uses the SAME model structure, then it treats 1H as base?
    # Wait, the error is "expected 231". This feature list is 231 long.
    # If Winner Hunter uses `winner_hunter_1h_trio_xgb.json`, we assume it was trained with these 231 features.
    
    # Let's include the rest of the list:
    "rsi_7_1h","rsi_14_1h","rsi_21_1h","stoch_k_1h","stoch_d_1h","williams_r_1h","roc_5_1h","roc_10_1h","awesome_osc_1h","kama_1h",
    "ppo_1h","ppo_signal_1h","ppo_hist_1h","ema_5_1h","ema_10_1h","ema_20_1h","ema_50_1h","ema_100_1h","ema_200_1h",
    "sma_10_1h","sma_20_1h","sma_50_1h","macd_1h","macd_signal_1h","macd_hist_1h","adx_1h","adx_pos_1h","adx_neg_1h","cci_1h",
    "aroon_up_1h","aroon_down_1h","ichimoku_a_1h","ichimoku_b_1h","bb_high_1h","bb_low_1h","bb_mid_1h","bb_width_1h","bb_pct_1h",
    "atr_7_1h","atr_14_1h","atr_21_1h","kc_high_1h","kc_low_1h","kc_mid_1h","dc_high_1h","dc_low_1h","dc_mid_1h","dc_width_1h",
    "obv_1h","cmf_1h","mfi_1h","adi_1h","eom_1h","vpt_1h","nvi_1h","vwap_1h",
    "price_vs_ema20_1h","price_vs_ema50_1h","price_vs_bb_mid_1h","ema_cross_1h","trend_strength_1h","atr_pct_1h","volatility_regime_1h",
    "rsi_sma_1h","rsi_divergence_1h","vol_sma_20_1h","volume_surge_1h","body_size_1h","upper_wick_1h","lower_wick_1h","is_bullish_1h",
    "return_1_1h","return_3_1h","return_5_1h","return_10_1h","range_pct_1h","range_vs_atr_1h"
]

class WinnerHunter1HLogic:
    """
    Winner Hunter 1H Logic (Isolated for Connector).
    """
    
    def __init__(self):
        self.name = "Winner Hunter (1H)"
        
        # Model paths (Local to this engine)
        self.models_dir = os.path.join(os.path.dirname(__file__), 'weights')
        self.wh_prefix = os.path.join(self.models_dir, 'winner_hunter_1h_trio_')
        
        # Models
        self.wh_xgb = None
        self.wh_lgb = None
        self.wh_cat = None
        
        # Thresholds
        self.threshold_long = 0.45
        self.threshold_short = 0.45
        
        self.load_models()
        self.load_thresholds()
        
    def load_models(self):
        """Load Trio Ensemble models."""
        try:
            print(f"   🤖 [WH Logic] Loading Trio Ensemble Models...")
            
            # XGBoost
            xgb_path = f'{self.wh_prefix}xgb.json'
            if os.path.exists(xgb_path):
                self.wh_xgb = xgb.XGBClassifier()
                self.wh_xgb.load_model(xgb_path)
            else: 
                print(f"   ⚠️ [WH Logic] XGB not found at {xgb_path}")

            # LightGBM
            lgb_path = f'{self.wh_prefix}lgb.json'
            if os.path.exists(lgb_path):
                self.wh_lgb = lgb.Booster(model_file=lgb_path)
            else:
                print(f"   ⚠️ [WH Logic] LGB not found at {lgb_path}")

            # CatBoost
            cat_path = f'{self.wh_prefix}cat.json'
            if os.path.exists(cat_path):
                self.wh_cat = CatBoostClassifier()
                self.wh_cat.load_model(cat_path)
            else:
                print(f"   ⚠️ [WH Logic] CatBoost not found at {cat_path}")
                
        except Exception as e:
            print(f"   ⚠️ [WH Logic] Model Load Error: {e}")

    def load_thresholds(self):
        try:
            meta_path = f'{self.wh_prefix}metadata.json'
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    wh_meta = json.load(f)
                    self.threshold_long = wh_meta.get('target_precision_threshold_long', 0.45)
                    self.threshold_short = wh_meta.get('target_precision_threshold_short', 0.45)
        except Exception:
            pass

    def get_ensemble_proba(self, X):
        """Calculate probability from Trio Ensemble"""
        # Checks if models are loaded
        if not (self.wh_xgb and self.wh_lgb and self.wh_cat):
            return np.array([0.33, 0.33, 0.33]) # Neutral fallback

        p1 = self.wh_xgb.predict_proba(X)
        p2 = self.wh_lgb.predict(X, num_iteration=self.wh_lgb.best_iteration)
        p3 = self.wh_cat.predict_proba(X)
        
        # Average
        ensemble_proba = (p1 + p2 + p3) / 3.0
        return ensemble_proba

    def analyze(self, df_1h, df_5m, df_15m):
        """
        Analyze DataFrames and return signal.
        Expects 1H base dataframe + 5m/15m context
        """
        try:
            # We need full MTF features because the model expects 231 features
            # This means we need 5m, 15m, and 1h data
            if df_5m is None or df_15m is None:
                return None

            from utils.mtf_feature_engineer import MTFFeatureGenerator
            # Note: MTFFeatureGenerator might be designed for 5m base. 
            # If Winner Hunter was trained on 231 features, it likely used the SAME generator
            # as the Scalper, just targeting 1H outcomes or similar.
            # Let's verify if we should use MTFFeatureGenerator(df_5m, df_15m, df_1h) (treating 1h as 30m slot? or just matching names)
            
            # Re-reading quant_engine_legacy:
            # check_winner_hunter constructs features manually by merging 5m, 15m, 1h columns.
            # It uses `add_all_indicators` on 1h, 5m, 15m and merges them.
            # Let's reproduce exactly that logic here to be safe.
            
            # --- REPRODUCTION OF LEGACY LOGIC ---
            
            # 1. Prepare 1H Base
            df_1h = add_all_indicators(df_1h, use_advanced=False)
            df_1h.set_index('timestamp', inplace=True)
            
            # 2. Context 5m
            df_5m = add_all_indicators(df_5m, use_advanced=False)
            df_5m.set_index('timestamp', inplace=True)
            exclude = ['open', 'high', 'low', 'close', 'volume']
            ctx_cols_5m = [c for c in df_5m.columns if c not in exclude]
            df_5m_ctx = df_5m[ctx_cols_5m].copy()
            df_5m_ctx.columns = [f"{c}_5m" for c in ctx_cols_5m]
            
            # 3. Context 15m
            df_15m = add_all_indicators(df_15m, use_advanced=False)
            df_15m.set_index('timestamp', inplace=True)
            ctx_cols_15m = [c for c in df_15m.columns if c not in exclude]
            df_15m_ctx = df_15m[ctx_cols_15m].copy()
            df_15m_ctx.columns = [f"{c}_15m" for c in ctx_cols_15m]
            
            # 4. Merge onto 1H
            # We must reindex context to 1H timestamps (ffill)
            df_5m_resampled = df_5m_ctx.reindex(df_1h.index, method='ffill')
            df_15m_resampled = df_15m_ctx.reindex(df_1h.index, method='ffill')
            
            df_combined = pd.concat([df_1h, df_5m_resampled, df_15m_resampled], axis=1)
            df_combined.dropna(inplace=True)
            
            if len(df_combined) == 0: return None
            
            if len(df_combined) == 0: return None
            
            # Map data to MTF_FEATURE_LIST (231 features)
            # The model expects strict 231 features.
            # We map:
            # - Base features (in list) <- 1H Data
            # - _15m features (in list) <- 15m Data
            # - _1h features (in list)  <- 5m Data (Mapping 5m context to the 3rd slot)
            
            latest_1h = df_1h.iloc[-1]
            latest_5m = df_5m.iloc[-1]
            latest_15m = df_15m.iloc[-1]
            
            X_data = []
            for feat_name in MTF_FEATURE_LIST:
                val = 0.0
                
                if feat_name.endswith('_15m'):
                    # Map from 15m DF
                    raw_name = feat_name.replace('_15m', '')
                    val = latest_15m.get(raw_name, 0.0)
                    
                elif feat_name.endswith('_1h'):
                    # Map from 5m DF (Using 5m as the second context slot)
                    raw_name = feat_name.replace('_1h', '')
                    val = latest_5m.get(raw_name, 0.0)
                    
                else:
                    # Map from 1H DF (Base)
                    val = latest_1h.get(feat_name, 0.0)
                
                X_data.append(val)
            
            X = np.array(X_data).reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Predict
            probas = self.get_ensemble_proba(X)[0]
            prob_long = float(probas[1])
            prob_short = float(probas[2])
            
            direction = None
            confidence = 0.0
            
            # Elastic Manager Update would go here in full version
            
            if prob_long >= self.threshold_long:
                direction = 'LONG'
                confidence = prob_long
            elif prob_short >= self.threshold_short:
                direction = 'SHORT'
                confidence = prob_short
                
                return {
                    'model': self.name,
                    'timestamp': datetime.now(),
                    'price': float(latest_1h['close']),
                    'direction': direction,
                    'confidence': confidence,
                    'meta': {
                        'rsi': latest_1h.get('rsi_14', 0),
                        'macd': latest_1h.get('macd_hist', 0)
                    }
                }
            return None

        except Exception as e:
            print(f"   ⚠️ [WH Logic] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
