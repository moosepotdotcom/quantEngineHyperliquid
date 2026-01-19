#!/usr/bin/env python3
"""
Liquidation Detector for Hyperliquid
Since there's no direct liquidation API, we'll infer liquidations from:
1. Large price wicks (liquidation cascades)
2. Volume spikes with price reversals
3. Funding rate extremes
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class LiquidationDetector:
    """
    Detects liquidation zones using price action and volume
    """
    
    def __init__(self):
        self.base_url = "https://api.hyperliquid.xyz/info"
        self.session = requests.Session()
    
    def get_recent_candles(self, symbol="BTC", interval="5m", num_candles=100):
        """Get recent candle data"""
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol,
                "interval": interval,
                "startTime": int((datetime.now() - timedelta(hours=24)).timestamp() * 1000),
                "endTime": int(datetime.now().timestamp() * 1000)
            }
        }
        
        try:
            response = self.session.post(self.base_url, json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    return df.tail(num_candles)
        except Exception as e:
            print(f"Error getting candles: {e}")
        
        return pd.DataFrame()
    
    def detect_liquidation_wicks(self, df, wick_threshold=0.005):
        """
        Detect liquidation wicks (long wicks that reverse quickly)
        
        Args:
            df: Candle DataFrame
            wick_threshold: Minimum wick size as % of price (0.5% default)
        """
        
        if df.empty or len(df) < 2:
            return []
        
        liquidation_events = []
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Calculate wick sizes
            upper_wick = (row['high'] - max(row['open'], row['close'])) / row['close']
            lower_wick = (min(row['open'], row['close']) - row['low']) / row['close']
            
            # Long upper wick = long liquidations
            if upper_wick > wick_threshold:
                # Check if price reversed (closed lower)
                if row['close'] < row['open']:
                    liquidation_events.append({
                        'time': row['time'],
                        'type': 'LONG_LIQ',
                        'price': row['high'],
                        'wick_size': upper_wick * 100,
                        'volume': row['volume']
                    })
            
            # Long lower wick = short liquidations
            if lower_wick > wick_threshold:
                # Check if price reversed (closed higher)
                if row['close'] > row['open']:
                    liquidation_events.append({
                        'time': row['time'],
                        'type': 'SHORT_LIQ',
                        'price': row['low'],
                        'wick_size': lower_wick * 100,
                        'volume': row['volume']
                    })
        
        return liquidation_events
    
    def calculate_liquidation_heatmap(self, current_price, leverage=50):
        """
        Calculate liquidation price levels based on leverage
        
        For BTC at $95k with 50x leverage:
        - Long liq at 2% down = $93,100
        - Short liq at 2% up = $96,900
        """
        
        # Liquidation happens at ~2% move with 50x leverage
        liq_threshold = 0.02
        
        # Calculate liquidation zones
        long_liq_zone = current_price * (1 - liq_threshold)
        short_liq_zone = current_price * (1 + liq_threshold)
        
        # Create heatmap levels
        heatmap = []
        
        # Long liquidation clusters (below current price)
        for i in range(1, 6):
            price_level = current_price * (1 - liq_threshold * i)
            heatmap.append({
                'price': price_level,
                'type': 'LONG_LIQ',
                'distance_pct': liq_threshold * i * 100,
                'risk_score': 1.0 / i  # Closer = higher risk
            })
        
        # Short liquidation clusters (above current price)
        for i in range(1, 6):
            price_level = current_price * (1 + liq_threshold * i)
            heatmap.append({
                'price': price_level,
                'type': 'SHORT_LIQ',
                'distance_pct': liq_threshold * i * 100,
                'risk_score': 1.0 / i
            })
        
        return pd.DataFrame(heatmap)
    
    def get_liquidation_features(self, current_price):
        """
        Generate liquidation-based features
        """
        
        # Get recent candles
        df = self.get_recent_candles(num_candles=50)
        
        if df.empty:
            return {
                'liq_wick_count_1h': 0,
                'liq_nearest_zone_dist': 999,
                'liq_pressure_score': 0
            }
        
        # Detect liquidation wicks
        liq_events = self.detect_liquidation_wicks(df)
        
        # Calculate heatmap
        heatmap = self.calculate_liquidation_heatmap(current_price)
        
        # Find nearest liquidation zone
        heatmap['distance'] = abs(heatmap['price'] - current_price)
        nearest = heatmap.loc[heatmap['distance'].idxmin()]
        
        # Calculate pressure score (0-1)
        recent_liq_count = len([e for e in liq_events if e['time'] > datetime.now() - timedelta(hours=1)])
        pressure_score = min(recent_liq_count / 5, 1.0)  # Normalize to 0-1
        
        return {
            'liq_wick_count_1h': recent_liq_count,
            'liq_nearest_zone_dist': nearest['distance_pct'],
            'liq_nearest_zone_type': 1 if nearest['type'] == 'LONG_LIQ' else -1,
            'liq_pressure_score': pressure_score,
            'liq_risk_score': nearest['risk_score']
        }

# Test
if __name__ == "__main__":
    print("="*60)
    print("🔥 Liquidation Detector Test")
    print("="*60)
    
    detector = LiquidationDetector()
    
    # Get current price
    from working_collectors import WorkingCollectors
    collector = WorkingCollectors()
    current_price = collector.get_current_price()
    
    print(f"\n💰 Current BTC Price: ${current_price:,.2f}")
    
    # Get candles
    print("\n📊 Fetching recent candles...")
    df = detector.get_recent_candles(num_candles=20)
    
    if not df.empty:
        print(f"✅ Got {len(df)} candles")
        print(f"\n   Latest candle:")
        latest = df.iloc[-1]
        print(f"   Time: {latest['time']}")
        print(f"   OHLC: ${latest['open']:.2f} / ${latest['high']:.2f} / ${latest['low']:.2f} / ${latest['close']:.2f}")
        print(f"   Volume: {latest['volume']:.2f}")
        
        # Detect liquidation wicks
        print("\n🔍 Detecting liquidation wicks...")
        liq_events = detector.detect_liquidation_wicks(df)
        
        if liq_events:
            print(f"✅ Found {len(liq_events)} liquidation events:")
            for event in liq_events[-5:]:  # Show last 5
                print(f"   {event['time']}: {event['type']} at ${event['price']:,.2f} (wick: {event['wick_size']:.2f}%)")
        else:
            print("   No liquidation wicks detected")
        
        # Calculate heatmap
        print("\n🗺️  Liquidation Heatmap:")
        heatmap = detector.calculate_liquidation_heatmap(current_price)
        print(f"   Nearest zones:")
        for idx, row in heatmap.head(6).iterrows():
            print(f"   {row['type']:10s} @ ${row['price']:,.2f} ({row['distance_pct']:+.2f}%) - Risk: {row['risk_score']:.2f}")
        
        # Get features
        print("\n📈 Liquidation Features:")
        features = detector.get_liquidation_features(current_price)
        for key, value in features.items():
            print(f"   {key}: {value}")
    else:
        print("❌ No candle data available")
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)
