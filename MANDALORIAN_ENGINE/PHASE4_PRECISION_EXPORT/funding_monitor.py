#!/usr/bin/env python3
"""
Hyperliquid Funding Rate & Open Interest Monitor
Tracks funding rates and open interest for sentiment analysis
"""

import requests
import pandas as pd
from datetime import datetime, timedelta

class FundingRateMonitor:
    """
    Monitors funding rates and open interest for BTC perpetuals
    
    Features:
    - Current funding rate
    - Funding rate history and trends
    - Open interest tracking
    - Extreme funding detection
    """
    
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz/info"
        self.session = requests.Session()
        
    def get_current_funding(self, symbol="BTC"):
        """
        Get current funding rate
        
        Returns:
            Current funding rate (as decimal, e.g., 0.0001 = 0.01%)
        """
        
        payload = {
            "type": "metaAndAssetCtxs"
        }
        
        try:
            response = self.session.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # data[0] = meta, data[1] = assetCtxs
            for asset in data[1]:
                if asset['name'] == symbol:
                    funding = float(asset.get('funding', 0))
                    return funding
            
            return 0.0
            
        except Exception as e:
            print(f"Error fetching funding rate: {e}")
            return 0.0
    
    def get_funding_history(self, symbol="BTC", hours=24):
        """
        Get historical funding rates
        
        Returns:
            DataFrame with funding rate history
        """
        
        payload = {
            "type": "fundingHistory",
            "coin": symbol,
            "startTime": int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
        }
        
        try:
            response = self.session.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Parse funding history
            funding_history = []
            
            for entry in data:
                entry_time = datetime.fromtimestamp(entry['time'] / 1000)
                funding_history.append({
                    'timestamp': entry_time,
                    'funding_rate': float(entry['fundingRate']),
                    'premium': float(entry.get('premium', 0))
                })
            
            return pd.DataFrame(funding_history)
            
        except Exception as e:
            print(f"Error fetching funding history: {e}")
            return pd.DataFrame()
    
    def get_open_interest(self, symbol="BTC"):
        """
        Get current open interest
        
        Returns:
            Open interest in USD
        """
        
        payload = {
            "type": "metaAndAssetCtxs"
        }
        
        try:
            response = self.session.post(self.base_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Find BTC open interest
            for asset in data[1]:  # assetCtxs
                if asset['name'] == symbol:
                    oi = float(asset.get('openInterest', 0))
                    return oi
            
            return 0.0
            
        except Exception as e:
            print(f"Error fetching open interest: {e}")
            return 0.0
    
    def analyze_funding_trend(self, funding_df):
        """
        Analyze funding rate trends
        
        Returns:
            Dict with trend metrics
        """
        
        if funding_df.empty or len(funding_df) < 2:
            return {
                'trend': 'NEUTRAL',
                'avg_funding': 0,
                'funding_momentum': 0,
                'extreme_count': 0
            }
        
        # Calculate metrics
        avg_funding = funding_df['funding_rate'].mean()
        latest_funding = funding_df['funding_rate'].iloc[-1]
        funding_momentum = latest_funding - funding_df['funding_rate'].iloc[0]
        
        # Count extreme funding events (>0.1% or <-0.05%)
        extreme_count = len(funding_df[
            (funding_df['funding_rate'] > 0.001) | 
            (funding_df['funding_rate'] < -0.0005)
        ])
        
        # Determine trend
        if avg_funding > 0.0005:
            trend = 'BULLISH_EXTREME'
        elif avg_funding > 0.0002:
            trend = 'BULLISH'
        elif avg_funding < -0.0003:
            trend = 'BEARISH_EXTREME'
        elif avg_funding < -0.0001:
            trend = 'BEARISH'
        else:
            trend = 'NEUTRAL'
        
        return {
            'trend': trend,
            'avg_funding': avg_funding,
            'funding_momentum': funding_momentum,
            'extreme_count': extreme_count
        }
    
    def get_funding_features(self):
        """
        Generate funding rate features for ML model
        
        Returns:
            Dictionary of features
        """
        
        # Get current funding
        current_funding = self.get_current_funding()
        
        # Get funding history
        funding_df = self.get_funding_history(hours=24)
        
        # Get open interest
        oi = self.get_open_interest()
        
        if funding_df.empty:
            return self._empty_features()
        
        # Analyze trend
        trend_analysis = self.analyze_funding_trend(funding_df)
        
        # Calculate features
        features = {
            # Current state
            'funding_current': current_funding,
            'funding_current_pct': current_funding * 100,
            
            # Historical metrics
            'funding_avg_24h': trend_analysis['avg_funding'],
            'funding_momentum': trend_analysis['funding_momentum'],
            'funding_extreme_count': trend_analysis['extreme_count'],
            
            # Trend classification
            'funding_is_extreme_high': 1 if current_funding > 0.001 else 0,
            'funding_is_extreme_low': 1 if current_funding < -0.0005 else 0,
            'funding_is_neutral': 1 if abs(current_funding) < 0.0001 else 0,
            
            # Open interest
            'oi_current': oi,
            'oi_millions': oi / 1_000_000,
            
            # Derived signals
            'funding_reversal_signal': 1 if abs(current_funding) > 0.0008 else 0,
            'funding_trend': self._encode_trend(trend_analysis['trend'])
        }
        
        return features
    
    def _encode_trend(self, trend):
        """Encode trend as numeric value"""
        encoding = {
            'BEARISH_EXTREME': -2,
            'BEARISH': -1,
            'NEUTRAL': 0,
            'BULLISH': 1,
            'BULLISH_EXTREME': 2
        }
        return encoding.get(trend, 0)
    
    def _empty_features(self):
        """Return empty features when no data available"""
        return {
            'funding_current': 0,
            'funding_current_pct': 0,
            'funding_avg_24h': 0,
            'funding_momentum': 0,
            'funding_extreme_count': 0,
            'funding_is_extreme_high': 0,
            'funding_is_extreme_low': 0,
            'funding_is_neutral': 1,
            'oi_current': 0,
            'oi_millions': 0,
            'funding_reversal_signal': 0,
            'funding_trend': 0
        }

# Example usage
if __name__ == "__main__":
    monitor = FundingRateMonitor()
    
    print("="*60)
    print("💰 Funding Rate Monitor Test")
    print("="*60)
    
    # Get current funding
    print("\n📊 Fetching current funding rate...")
    funding = monitor.get_current_funding()
    print(f"✅ Current funding: {funding*100:.4f}% (8h rate)")
    print(f"   Annualized: {funding*365*3:.2f}%")
    
    # Get funding history
    print("\n📈 Fetching funding history (24h)...")
    funding_df = monitor.get_funding_history(hours=24)
    
    if not funding_df.empty:
        print(f"✅ Found {len(funding_df)} funding rate updates")
        print(f"   Avg funding: {funding_df['funding_rate'].mean()*100:.4f}%")
        print(f"   Min funding: {funding_df['funding_rate'].min()*100:.4f}%")
        print(f"   Max funding: {funding_df['funding_rate'].max()*100:.4f}%")
        
        # Analyze trend
        print("\n🔍 Analyzing trend...")
        trend = monitor.analyze_funding_trend(funding_df)
        print(f"✅ Trend: {trend['trend']}")
        print(f"   Momentum: {trend['funding_momentum']*100:.4f}%")
        print(f"   Extreme events: {trend['extreme_count']}")
    
    # Get open interest
    print("\n📊 Fetching open interest...")
    oi = monitor.get_open_interest()
    print(f"✅ Open Interest: ${oi/1_000_000:.2f}M")
    
    # Get features
    print("\n📈 Generating features...")
    features = monitor.get_funding_features()
    print("✅ Features:")
    for key, value in features.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)
