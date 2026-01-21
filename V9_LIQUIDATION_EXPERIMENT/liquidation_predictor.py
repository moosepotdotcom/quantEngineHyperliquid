#!/usr/bin/env python3
"""
Liquidation Predictor
Predicts when next liquidation cascade will occur
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

class LiquidationPredictor:
    """Predict upcoming liquidation events"""
    
    def __init__(self):
        self.api_url = "https://api.hyperliquid.xyz/info"
    
    def get_current_price(self):
        """Get current BTC price from Hyperliquid"""
        payload = {"type": "allMids"}
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return float(data.get('BTC', 0))
        except:
            pass
        
        return None
    
    def get_funding_rate(self):
        """Get current funding rate"""
        payload = {
            "type": "metaAndAssetCtxs"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Extract funding rate for BTC
                for asset in data[1]:
                    if asset.get('coin') == 'BTC':
                        funding = asset.get('funding', 0)
                        return float(funding)
        except:
            pass
        
        return None
    
    def predict_liquidation_levels(self, current_price, leverage_levels=[10, 25, 50, 100]):
        """
        Predict where liquidations will occur based on common leverage levels
        
        Returns:
            DataFrame with predicted liquidation prices
        """
        predictions = []
        
        for leverage in leverage_levels:
            # Long liquidation price (price drops)
            long_liq_pct = (1 / leverage) * 100  # e.g., 10x = 10% drop
            long_liq_price = current_price * (1 - long_liq_pct/100)
            
            # Short liquidation price (price rises)
            short_liq_pct = (1 / leverage) * 100
            short_liq_price = current_price * (1 + short_liq_pct/100)
            
            predictions.append({
                'leverage': f"{leverage}x",
                'long_liq_price': long_liq_price,
                'long_liq_distance_pct': -long_liq_pct,
                'short_liq_price': short_liq_price,
                'short_liq_distance_pct': short_liq_pct
            })
        
        return pd.DataFrame(predictions)
    
    def assess_liquidation_risk(self, funding_rate):
        """
        Assess liquidation risk based on funding rate
        
        High positive funding = many longs = risk of long liquidations
        High negative funding = many shorts = risk of short liquidations
        """
        if funding_rate is None:
            return "UNKNOWN", "No funding data"
        
        funding_pct = funding_rate * 100
        
        if funding_pct > 0.05:
            return "HIGH", f"Longs paying {funding_pct:.3f}% - Long liquidation risk"
        elif funding_pct < -0.05:
            return "HIGH", f"Shorts paying {abs(funding_pct):.3f}% - Short liquidation risk"
        elif abs(funding_pct) > 0.02:
            return "MEDIUM", f"Moderate funding: {funding_pct:+.3f}%"
        else:
            return "LOW", f"Balanced funding: {funding_pct:+.3f}%"
    
    def print_prediction_report(self):
        """Print comprehensive liquidation prediction report"""
        print("\n🔮 LIQUIDATION PREDICTION REPORT")
        print("="*70)
        print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get current data
        current_price = self.get_current_price()
        funding_rate = self.get_funding_rate()
        
        if current_price is None:
            print("   ❌ Could not fetch current price")
            return
        
        print(f"   💰 Current BTC Price: ${current_price:,.2f}")
        
        # Funding rate analysis
        if funding_rate is not None:
            risk_level, risk_msg = self.assess_liquidation_risk(funding_rate)
            print(f"   📊 Funding Rate: {funding_rate*100:+.4f}%")
            print(f"   ⚠️  Liquidation Risk: {risk_level}")
            print(f"      {risk_msg}")
        
        print()
        
        # Predicted liquidation levels
        print("   🎯 PREDICTED LIQUIDATION LEVELS:")
        print()
        
        df_pred = self.predict_liquidation_levels(current_price)
        
        print("   Leverage | Long Liq Price | Distance | Short Liq Price | Distance")
        print("   " + "-"*65)
        
        for _, row in df_pred.iterrows():
            print(f"   {row['leverage']:>8} | "
                  f"${row['long_liq_price']:>13,.2f} | "
                  f"{row['long_liq_distance_pct']:>+7.2f}% | "
                  f"${row['short_liq_price']:>14,.2f} | "
                  f"{row['short_liq_distance_pct']:>+7.2f}%")
        
        print()
        print("   💡 INTERPRETATION:")
        print("      - Clusters near these levels = high liquidation risk")
        print("      - Price approaching level = potential cascade")
        print("      - Use with heatmap to identify actual clusters")
        print()

if __name__ == "__main__":
    predictor = LiquidationPredictor()
    predictor.print_prediction_report()
